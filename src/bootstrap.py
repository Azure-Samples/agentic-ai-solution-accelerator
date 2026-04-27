"""In-app deploy-time bootstrap — replaces the postprovision azd hook.

Runs synchronously inside the FastAPI ``lifespan`` startup phase. The container
does not accept requests until this completes, so:

- A healthy ``/healthz`` from the container app proves bootstrap finished.
- ACA's ``startupProbe`` (configured in infra/modules/container-app.bicep) is
  the deployment readiness gate; if bootstrap exhausts its retry budget the
  exception propagates → uvicorn exits → ACA marks the revision unhealthy →
  ``azd up`` exits non-zero. This is the loud failure semantic the previous
  postprovision hook had, just centralized inside the workload image.

What it does (idempotent — safe to re-run on container restart):

1. **Foundry agents** — for every ``scenario.agents[]`` entry in
   ``accelerator.yaml``, read ``docs/agent-specs/<foundry_name>.md``, parse
   the ``## Instructions`` body, and create-or-update the Foundry agent
   bound to the slug-resolved model deployment.

2. **AI Search indexes** — for every ``scenario.retrieval.indexes[]`` entry,
   call the resolved schema callable to get a ``SearchIndex`` and
   create-or-update it. If a ``seed`` JSON file exists, upload the documents.

Inputs (env, set by Bicep outputs / Container App env block):
- ``AZURE_AI_FOUNDRY_ENDPOINT``         required
- ``AZURE_AI_FOUNDRY_MODEL``            required (default deployment name)
- ``AZURE_AI_FOUNDRY_MODEL_MAP``        optional JSON object (slug -> deployment)
- ``AZURE_AI_SEARCH_ENDPOINT``          required
- ``BOOTSTRAP_SKIP=1``                  optional; bypass entirely (local dev / tests)
- ``BOOTSTRAP_RETRY_BUDGET_SECONDS``    optional; default 600 (10 minutes)

Auth: ``DefaultAzureCredential`` only. The Bicep modules grant the workload MI:
- ``Azure AI Developer`` on the Foundry project (agent CRUD)
- ``Cognitive Services OpenAI User`` on the account (model invoke)
- ``Search Service Contributor`` + ``Search Index Data Contributor`` on Search
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import re
import time
import uuid
from typing import Any, Awaitable, Callable

from .workflow.registry import ROOT, ScenarioAgent, ScenarioBundle

logger = logging.getLogger("accelerator.bootstrap")

# Search RBAC roles granted to each Foundry agent's instance MI so its
# AzureAISearchTool calls can resolve the AI Search index at query time.
# Must match the ABAC condition allow-list in infra/main.bicep
# (workloadAssignsSearchRoles role assignment).
_AGENT_SEARCH_ROLES: dict[str, str] = {
    "Search Index Data Reader": "1407120a-92aa-4202-b7e9-c0e197c71c8f",
    "Search Index Data Contributor": "8ebe5a00-799e-43f5-93ac-243d3dce84a7",
    "Search Service Contributor": "7ca78c08-252a-4471-8644-bb5ff32d4ba0",
}

SPECS_DIR = ROOT / "docs" / "agent-specs"

_INSTRUCTIONS_RE = re.compile(
    r"^##\s+Instructions\s*\n(.*?)(?=^##\s|\Z)", re.DOTALL | re.MULTILINE
)
_MODEL_RE = re.compile(r"^\s*\*\*Model:\*\*", re.MULTILINE)


def _retry_budget_seconds() -> float:
    raw = os.environ.get("BOOTSTRAP_RETRY_BUDGET_SECONDS", "600")
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 600.0


def _parse_model_map() -> dict[str, str]:
    """Resolve slug -> deployment_name from env (Bicep output AZURE_AI_FOUNDRY_MODEL_MAP).

    Falls back to ``{"default": AZURE_AI_FOUNDRY_MODEL}`` when the map env is
    absent (i.e. a manifest with no ``models:`` block — only the default
    deployment exists).
    """
    default_dep = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "")
    raw = os.environ.get("AZURE_AI_FOUNDRY_MODEL_MAP", "").strip()
    if not raw:
        return {"default": default_dep} if default_dep else {}
    try:
        mapping = json.loads(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"AZURE_AI_FOUNDRY_MODEL_MAP is not valid JSON: {exc}. It should "
            "be the Bicep output AZURE_AI_FOUNDRY_MODEL_MAP."
        ) from exc
    if not isinstance(mapping, dict):
        raise RuntimeError(
            "AZURE_AI_FOUNDRY_MODEL_MAP must be a JSON object (slug -> "
            "deployment_name)"
        )
    return {str(k): str(v) for k, v in mapping.items()}


def _parse_spec(path: pathlib.Path) -> str:
    """Return the ``## Instructions`` body of the spec file.

    The Foundry agent's model is set from the resolved model map (Bicep
    output) — the spec must NOT carry a ``**Model:**`` field.
    """
    txt = path.read_text(encoding="utf-8")
    if _MODEL_RE.search(txt):
        raise RuntimeError(
            f"{path.name}: spec contains a '**Model:**' field, which is no "
            "longer allowed. The deployed model is authoritative."
        )
    m = _INSTRUCTIONS_RE.search(txt)
    if not m:
        raise RuntimeError(f"{path.name}: missing '## Instructions' section")
    return m.group(1).strip()


async def _retry(
    fn: Callable[[], Awaitable[Any]],
    *,
    name: str,
    budget_seconds: float,
    base: float = 2.0,
) -> Any:
    """Exponential-backoff retry around an awaitable factory.

    Retries on every exception except hard configuration errors (which are
    re-raised unwrapped). The intent is to absorb RBAC role-assignment
    propagation lag — Bicep finishes the role assignment but the Foundry /
    Search data planes can take several minutes to reflect it. After the
    budget is exhausted, the last exception propagates so the FastAPI
    lifespan fails and ACA marks the revision unhealthy.
    """
    deadline = time.monotonic() + budget_seconds
    attempt = 0
    while True:
        attempt += 1
        try:
            return await fn()
        except (RuntimeError, ValueError, FileNotFoundError):
            # Configuration / contract errors — never retry.
            raise
        except Exception as exc:  # noqa: BLE001  # broad on purpose: retry transient infra errors
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.error(
                    "bootstrap.%s: retry budget exhausted after %d attempts (%s)",
                    name, attempt, exc,
                )
                raise
            sleep = min(remaining, base ** min(attempt, 6))
            logger.warning(
                "bootstrap.%s: attempt %d failed (%s); retrying in %.1fs (%.1fs left)",
                name, attempt, exc, sleep, remaining,
            )
            await asyncio.sleep(sleep)


def _foundry_iq_asset_name(index_name: str) -> str:
    """Deterministic FoundryIQ asset name derived from the AI Search index name."""
    return f"{index_name}-knowledge"


_FOUNDRY_IQ_ASSET_VERSION = "1"


async def _bootstrap_indexes(bundle: ScenarioBundle) -> dict[str, str]:
    """Register a FoundryIQ Index asset on the project for each retrieval-using agent.

    Returns a map ``{search_index_name: asset_id}`` so ``_bootstrap_foundry``
    can wire the right ``index_asset_id`` into each agent's
    ``AzureAISearchTool``.

    Idempotent — ``indexes.create_or_update`` overwrites the same
    ``(name, version)`` pair across runs and the asset id is stable.
    """
    foundry_tool_agents = [
        a for a in bundle.agents
        if a.retrieval is not None and a.retrieval.mode == "foundry_tool"
    ]
    if not foundry_tool_agents:
        return {}

    endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")
    if not endpoint:
        raise RuntimeError("AZURE_AI_FOUNDRY_ENDPOINT is not set")
    connection_name = os.environ.get("AZURE_AI_FOUNDRY_SEARCH_CONNECTION_NAME")
    if not connection_name:
        raise RuntimeError(
            "AZURE_AI_FOUNDRY_SEARCH_CONNECTION_NAME is not set — Bicep "
            "should export it from the project AzureAISearch connection."
        )

    from azure.ai.projects.aio import AIProjectClient
    from azure.ai.projects.models import AzureAISearchIndex
    from azure.identity.aio import DefaultAzureCredential

    asset_ids: dict[str, str] = {}
    cred = DefaultAzureCredential()
    try:
        proj = AIProjectClient(endpoint=endpoint, credential=cred)
        try:
            seen_indexes: set[str] = set()
            for agent in foundry_tool_agents:
                assert agent.retrieval is not None  # type narrowing
                idx_name = agent.retrieval.index
                if not idx_name:
                    raise RuntimeError(
                        f"{agent.id}: retrieval.mode=foundry_tool requires "
                        "retrieval.index"
                    )
                if idx_name in seen_indexes:
                    continue
                seen_indexes.add(idx_name)

                asset_name = _foundry_iq_asset_name(idx_name)

                async def _create(_idx=idx_name, _asset=asset_name) -> Any:
                    return await proj.indexes.create_or_update(
                        _asset,
                        _FOUNDRY_IQ_ASSET_VERSION,
                        AzureAISearchIndex(
                            connection_name=connection_name,
                            index_name=_idx,
                            description=(
                                f"FoundryIQ knowledge over AI Search index "
                                f"'{_idx}'."
                            ),
                        ),
                    )

                created = await _retry(
                    _create,
                    name=f"foundry.indexes.{asset_name}",
                    budget_seconds=_retry_budget_seconds(),
                )
                asset_id = getattr(created, "id", None)
                if not asset_id:
                    # The Foundry Indexes API (AzureML-backed) does not
                    # populate the ``id`` field on the response. The runtime
                    # Responses API resolves indexes via the canonical
                    # ``<name>/versions/<version>`` form. The agents
                    # control-plane API also accepts this form.
                    asset_id = (
                        f"{asset_name}/versions/{_FOUNDRY_IQ_ASSET_VERSION}"
                    )
                    logger.info(
                        "bootstrap.indexes: %s server returned no asset id; "
                        "synthesized %s",
                        asset_name,
                        asset_id,
                    )
                asset_ids[idx_name] = asset_id
                logger.info(
                    "bootstrap.indexes: %s -> %s", asset_name, asset_id,
                )
        finally:
            await proj.close()
    finally:
        await cred.close()
    return asset_ids


def _build_search_tool(
    agent: ScenarioAgent, asset_ids: dict[str, str]
) -> Any | None:
    """Construct an ``AzureAISearchTool`` for an agent, or ``None``.

    Returns ``None`` if the agent has no foundry_tool retrieval. Raises if
    retrieval is configured but the asset isn't available — bootstrap should
    fail loudly rather than silently produce a tool-less agent.
    """
    if agent.retrieval is None or agent.retrieval.mode != "foundry_tool":
        return None
    asset_id = asset_ids.get(agent.retrieval.index)
    if not asset_id:
        raise RuntimeError(
            f"{agent.id}: retrieval requested index "
            f"{agent.retrieval.index!r} but no FoundryIQ asset registered"
        )
    from azure.ai.projects.models import (
        AISearchIndexResource,
        AzureAISearchQueryType,
        AzureAISearchTool,
        AzureAISearchToolResource,
    )
    qt_raw = (agent.retrieval.query_type or "vector_semantic_hybrid").lower()
    qt_enum = {
        "simple": AzureAISearchQueryType.SIMPLE,
        "semantic": AzureAISearchQueryType.SEMANTIC,
        "vector": AzureAISearchQueryType.VECTOR,
        "vector_simple_hybrid": AzureAISearchQueryType.VECTOR_SIMPLE_HYBRID,
        "vector_semantic_hybrid": AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID,
    }.get(qt_raw, AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID)
    return AzureAISearchTool(
        azure_ai_search=AzureAISearchToolResource(
            indexes=[AISearchIndexResource(
                index_asset_id=asset_id,
                query_type=qt_enum,
                top_k=agent.retrieval.top_k,
            )]
        )
    )


def _tool_fingerprint(tool: Any | None) -> tuple:
    """Order-stable fingerprint of an AzureAISearchTool for idempotency diff."""
    if tool is None:
        return ()
    res = getattr(tool, "azure_ai_search", None)
    if res is None:
        return ("azure_ai_search",)
    indexes = getattr(res, "indexes", None) or []
    parts: list[tuple] = []
    for ix in indexes:
        parts.append((
            getattr(ix, "index_asset_id", None) or "",
            str(getattr(ix, "query_type", "") or ""),
            int(getattr(ix, "top_k", 0) or 0),
        ))
    return ("azure_ai_search", tuple(parts))


def _existing_tools_fingerprint(definition: Any) -> tuple:
    """Fingerprint the ``tools`` field on a returned PromptAgentDefinition."""
    if definition is None:
        return ()
    tools = getattr(definition, "tools", None) or []
    if not tools:
        return ()
    # We only know how to compare azure_ai_search tools — anything else means
    # external state we don't manage; treat as unmatched so we rewrite.
    if len(tools) != 1:
        return ("__unknown_count__", len(tools))
    return _tool_fingerprint(tools[0])


async def _grant_agent_search_access(
    principal_id: str, agent_name: str, cred: Any,
) -> None:
    """Idempotently grant Search RBAC to a Foundry agent's instance MI.

    Each Foundry agent (PromptAgent) is created with its own
    ``instance_identity.principal_id`` — a fresh service principal not known
    at Bicep time. Without explicit RBAC, the agent's AzureAISearchTool
    call fails at query time with ``tool_user_error: Access denied``.

    Bootstrap closes the loop: after ``create_version`` returns, we read the
    instance principalId off the version envelope and assign the three
    Search roles below on the search service. The role-assignment GUIDs are
    derived deterministically (uuid5 over scope|principal|role) so re-runs
    are idempotent — 409 RoleAssignmentExists is treated as success.

    Authorization for THIS write comes from a workload-MI role assignment
    in ``infra/main.bicep`` (``workloadAssignsSearchRoles``): Role Based
    Access Control Administrator at the search-service scope, ABAC-conditioned
    so only the three Search role IDs can be granted. Minimum-privilege.

    Skips silently when ``AZURE_AI_SEARCH_RESOURCE_ID`` is unset (local dev,
    tests, or non-Bicep installs).
    """
    if not principal_id:
        logger.warning(
            "bootstrap.foundry: %s has no instance_identity.principal_id; "
            "skipping per-agent Search RBAC", agent_name,
        )
        return
    search_resource_id = os.environ.get("AZURE_AI_SEARCH_RESOURCE_ID", "")
    if not search_resource_id:
        logger.info(
            "bootstrap.foundry: AZURE_AI_SEARCH_RESOURCE_ID not set; "
            "skipping per-agent Search RBAC for %s", agent_name,
        )
        return

    from azure.core.exceptions import HttpResponseError, ResourceExistsError
    from azure.mgmt.authorization.aio import AuthorizationManagementClient

    parts = [p for p in search_resource_id.split("/") if p]
    try:
        sub_id = parts[parts.index("subscriptions") + 1]
    except (ValueError, IndexError):
        logger.warning(
            "bootstrap.foundry: AZURE_AI_SEARCH_RESOURCE_ID=%r is malformed; "
            "skipping per-agent Search RBAC for %s",
            search_resource_id, agent_name,
        )
        return

    auth = AuthorizationManagementClient(
        credential=cred, subscription_id=sub_id,
    )
    try:
        for role_name, role_id in _AGENT_SEARCH_ROLES.items():
            ra_name = str(uuid.uuid5(
                uuid.NAMESPACE_OID,
                f"{search_resource_id}|{principal_id}|{role_id}",
            ))
            params: dict[str, Any] = {
                "properties": {
                    "roleDefinitionId": (
                        f"/subscriptions/{sub_id}/providers/"
                        f"Microsoft.Authorization/roleDefinitions/{role_id}"
                    ),
                    "principalId": principal_id,
                    "principalType": "ServicePrincipal",
                    "description": (
                        f"Bootstrap-managed: Foundry agent {agent_name} "
                        f"-> {role_name} on AI Search."
                    ),
                },
            }
            try:
                await auth.role_assignments.create(
                    scope=search_resource_id,
                    role_assignment_name=ra_name,
                    parameters=params,
                )
                logger.info(
                    "bootstrap.foundry: granted '%s' to %s "
                    "(agent=%s, principal=%s)",
                    role_name, search_resource_id.rsplit("/", 1)[-1],
                    agent_name, principal_id,
                )
            except ResourceExistsError:
                # Already granted — idempotent success.
                continue
            except HttpResponseError as exc:
                if getattr(exc, "status_code", None) == 409:
                    continue
                # 403 here means the workload MI is missing the
                # workloadAssignsSearchRoles assignment from main.bicep —
                # log loudly and continue (other roles may still apply).
                logger.error(
                    "bootstrap.foundry: failed to grant '%s' to %s "
                    "(agent=%s): %s",
                    role_name, principal_id, agent_name, exc,
                )
    finally:
        await auth.close()


async def _bootstrap_foundry(
    bundle: ScenarioBundle, asset_ids: dict[str, str] | None = None,
) -> None:
    asset_ids = asset_ids or {}
    endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")
    if not endpoint:
        raise RuntimeError("AZURE_AI_FOUNDRY_ENDPOINT is not set")

    model_map = _parse_model_map()
    if "default" not in model_map or not model_map["default"]:
        raise RuntimeError(
            "no default Foundry model deployment resolved. Set "
            "AZURE_AI_FOUNDRY_MODEL (Bicep output) or include a `models:` "
            "block with `default: true` in accelerator.yaml."
        )

    # Pre-resolve specs and tools so we fail fast on missing files / asset
    # mismatches BEFORE touching the control plane.
    work: list[tuple[ScenarioAgent, str, str, Any | None]] = []
    for agent in bundle.agents:
        spec_path = SPECS_DIR / f"{agent.foundry_name}.md"
        if not spec_path.exists():
            raise RuntimeError(
                f"{agent.foundry_name}: missing spec file {spec_path}"
            )
        instructions = _parse_spec(spec_path)
        deployment = model_map.get("default", "")
        tool = _build_search_tool(agent, asset_ids)
        work.append((agent, deployment, instructions, tool))

    # SDK contract (GA-only — enforced by scripts/accelerator-lint.py
    # `sdks_pinned_to_ga` against ga-versions.yaml):
    #
    #   azure-ai-projects >=2.0.0,<3.0.0 -> AIProjectClient.agents
    #     The *new* Foundry "Agents (versions)" surface. Each instructions
    #     edit is a new version; "latest" is the active one. Methods used:
    #       agents.list()                 — enumerate agents in the project
    #       agents.get_version(name, ver) — fetch latest definition
    #       agents.create_version(name, definition=PromptAgentDefinition(
    #           model=..., instructions=...))
    #     The first create_version() implicitly creates the agent envelope.
    #
    #   azure-ai-agents >=1.0.0,<2.0.0  -> AgentsClient
    #     The *legacy* Foundry Assistants surface. Kept as a transitive dep
    #     of agent-framework, and used here only to delete any orphaned
    #     Assistants left over from earlier accelerator versions so the
    #     portal stops showing the "Update your agents" migration banner.
    #
    # If a future SDK bump moves these methods, update both this comment and
    # ga-versions.yaml in the same change so the lint stays honest.
    from azure.ai.projects.aio import AIProjectClient
    from azure.ai.projects.models import PromptAgentDefinition
    from azure.core.exceptions import (
        HttpResponseError,
        ResourceNotFoundError,
    )
    from azure.identity.aio import DefaultAzureCredential

    desired_names = {agent.foundry_name for agent, _, _, _ in work}

    cred = DefaultAzureCredential()
    try:
        proj = AIProjectClient(endpoint=endpoint, credential=cred)
        try:
            existing_names: set[str] = set()

            async def _list() -> None:
                async for a in proj.agents.list():
                    if a.name:
                        existing_names.add(a.name)

            await _retry(
                _list,
                name="foundry.agents.list",
                budget_seconds=_retry_budget_seconds(),
            )

            for agent, deployment, instructions, tool in work:
                name = agent.foundry_name
                desired_tools = [tool] if tool is not None else None
                desired_tool_fp = _tool_fingerprint(tool)
                # Force tool use for retrieval-mode agents so gpt-5-mini
                # cannot skip the AI Search call. Server may reject the
                # string form on some preview surfaces — wrapper handles
                # the fallback below.
                desired_tool_choice = (
                    "required" if tool is not None else None
                )

                # Decide whether a fresh version is needed: skip the write
                # when the latest version already matches our desired
                # (model, instructions, tools) tuple so partners don't
                # churn version history on every cold start.
                needs_new_version = True
                if name in existing_names:
                    try:
                        latest = await proj.agents.get_version(name, "latest")
                        defn = getattr(latest, "definition", None)
                        cur_model = getattr(defn, "model", None)
                        cur_instr = getattr(defn, "instructions", None)
                        cur_tool_fp = _existing_tools_fingerprint(defn)
                        if (
                            cur_model == deployment
                            and cur_instr == instructions
                            and cur_tool_fp == desired_tool_fp
                        ):
                            needs_new_version = False
                    except ResourceNotFoundError:
                        # Envelope exists but no version yet — still need
                        # to create one.
                        needs_new_version = True
                    except HttpResponseError as exc:
                        # Some Foundry preview surfaces reject the "latest"
                        # alias with invalid_parameters / 404 instead of a
                        # ResourceNotFoundError. In that case fall back to
                        # creating a fresh version — the server treats
                        # create_version as upsert by name+monotonic version.
                        logger.info(
                            "bootstrap.foundry: %s get_version(latest) "
                            "failed (%s); will create new version",
                            name, getattr(exc, "status_code", "?"),
                        )
                        needs_new_version = True

                if not needs_new_version:
                    logger.info(
                        "bootstrap.foundry: %s up-to-date (model=%s, tool=%s)",
                        name, deployment,
                        "yes" if tool is not None else "no",
                    )
                    # Even when the agent definition is up-to-date we re-run
                    # the per-agent Search RBAC grant for retrieval-mode
                    # agents — the helper is idempotent (409 = success) and
                    # this self-heals if a partner manually deletes a role
                    # assignment, or if a previous bootstrap landed before
                    # the workload MI got the RBAC-admin grant.
                    if tool is not None:
                        try:
                            principal_id = getattr(
                                getattr(latest, "instance_identity", None),
                                "principal_id", None,
                            )
                            await _grant_agent_search_access(
                                principal_id or "", name, cred,
                            )
                        except Exception as exc:  # pragma: no cover
                            logger.warning(
                                "bootstrap.foundry: %s Search RBAC refresh "
                                "skipped: %s", name, exc,
                            )
                    continue

                async def _create_version(
                    _name=name,
                    _dep=deployment,
                    _ins=instructions,
                    _tools=desired_tools,
                    _tc=desired_tool_choice,
                ) -> Any:
                    kwargs: dict[str, Any] = {
                        "model": _dep,
                        "instructions": _ins,
                    }
                    if _tools is not None:
                        kwargs["tools"] = _tools
                    if _tc is not None:
                        kwargs["tool_choice"] = _tc
                    try:
                        return await proj.agents.create_version(
                            agent_name=_name,
                            definition=PromptAgentDefinition(**kwargs),
                        )
                    except Exception as exc:  # noqa: BLE001  # see fallback below
                        # tool_choice="required" can be rejected on some
                        # preview server builds; retry once without it so
                        # the agent still gets the tool wired (model
                        # decides per-turn whether to call it).
                        if _tc is None or "tool_choice" not in str(exc):
                            raise
                        logger.warning(
                            "bootstrap.foundry: %s rejected tool_choice=%r "
                            "(%s); retrying without tool_choice",
                            _name, _tc, exc,
                        )
                        kwargs.pop("tool_choice", None)
                        return await proj.agents.create_version(
                            agent_name=_name,
                            definition=PromptAgentDefinition(**kwargs),
                        )

                verb = "updated" if name in existing_names else "created"
                created_version = await _retry(
                    _create_version,
                    name=f"foundry.{verb}.{name}",
                    budget_seconds=_retry_budget_seconds(),
                )
                created_version_id = getattr(
                    created_version, "version", None,
                )
                logger.info(
                    "bootstrap.foundry: %s %s "
                    "(model=%s, tool=%s, version=%s)",
                    verb, name, deployment,
                    "yes" if tool is not None else "no",
                    created_version_id or "?",
                )

                # Readback canary — for retrieval-mode agents, fetch the
                # version we just wrote and confirm the tool fingerprint
                # round-trips. Catches silent server-side strip of fields
                # we don't have visibility into yet. Cheap (~1 GET).
                if tool is not None and created_version_id:
                    try:
                        verified = await proj.agents.get_version(
                            name, created_version_id,
                        )
                        v_defn = getattr(verified, "definition", None)
                        v_fp = _existing_tools_fingerprint(v_defn)
                        if v_fp != desired_tool_fp:
                            raise RuntimeError(
                                f"foundry.foundry: {name} readback "
                                f"fingerprint {v_fp!r} != desired "
                                f"{desired_tool_fp!r} — tool not attached"
                            )
                        # Grant Search RBAC to the agent's instance MI now
                        # that the version exists. The principal id is
                        # stable across versions of the same agent name, so
                        # this is a one-time setup cost per agent — but the
                        # helper is idempotent so re-runs are 409 → noop.
                        principal_id = getattr(
                            getattr(verified, "instance_identity", None),
                            "principal_id", None,
                        )
                        await _grant_agent_search_access(
                            principal_id or "", name, cred,
                        )
                    except ResourceNotFoundError as exc:
                        raise RuntimeError(
                            f"foundry.foundry: {name} disappeared right "
                            f"after create_version: {exc}"
                        ) from exc
                    except HttpResponseError as exc:
                        # Some preview surfaces 400 on get_version while
                        # the create above succeeded — log and continue
                        # rather than blocking bootstrap on a verifier.
                        logger.warning(
                            "bootstrap.foundry: %s readback "
                            "get_version(%s) returned %s; "
                            "skipping fingerprint check",
                            name, created_version_id,
                            getattr(exc, "status_code", "?"),
                        )
        finally:
            await proj.close()

        # ---- legacy cleanup pass ----------------------------------------
        # Delete any orphaned legacy Assistants (created by earlier
        # accelerator versions via azure-ai-agents.AgentsClient) whose
        # name collides with one of our desired agents. On a fresh
        # subscription this is a no-op. Failures are logged but not fatal
        # — provisioning succeeded above and the runtime targets the new
        # versioned surface, so an orphaned Assistant is at worst a
        # cosmetic portal nag.
        try:
            from azure.ai.agents.aio import AgentsClient

            legacy = AgentsClient(endpoint=endpoint, credential=cred)
            try:
                async for a in legacy.list_agents():
                    if a.name in desired_names and a.id:
                        try:
                            await legacy.delete_agent(agent_id=a.id)
                            logger.info(
                                "bootstrap.foundry: deleted legacy Assistant %s",
                                a.name,
                            )
                        except Exception as exc:  # pragma: no cover - best effort
                            logger.warning(
                                "bootstrap.foundry: could not delete legacy "
                                "Assistant %s: %s", a.name, exc,
                            )
            finally:
                await legacy.close()
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("bootstrap.foundry: legacy cleanup skipped: %s", exc)
    finally:
        await cred.close()


async def _embed_seed_docs(
    docs: list[dict],
    aoai_endpoint: str,
    deployment: str,
    cred: Any,
) -> list[dict]:
    """Add a `contentVector` field to each seed doc by calling AOAI.

    Bootstrap-time embedding for the initial corpus. At query time the
    AzureOpenAIVectorizer attached to the index handles vectorization
    automatically — partners adding new docs via SearchClient.upload_documents
    on an existing deployment must do the same (call AOAI, set contentVector).
    """
    if not aoai_endpoint or not deployment:
        raise RuntimeError(
            "AZURE_AI_FOUNDRY_OPENAI_ENDPOINT and "
            "AZURE_AI_FOUNDRY_EMBEDDING_DEPLOYMENT must be set to embed seeds"
        )

    from azure.identity.aio import get_bearer_token_provider
    from openai import AsyncAzureOpenAI

    token_provider = get_bearer_token_provider(
        cred, "https://cognitiveservices.azure.com/.default"
    )
    client = AsyncAzureOpenAI(
        azure_endpoint=aoai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
    )
    try:
        out: list[dict] = []
        # Embed in small batches to stay well under per-request token caps.
        batch_size = 16
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            inputs = [d.get("content", "") for d in batch]
            resp = await client.embeddings.create(
                model=deployment, input=inputs
            )
            for d, item in zip(batch, resp.data, strict=True):
                merged = dict(d)
                merged["contentVector"] = item.embedding
                out.append(merged)
        return out
    finally:
        await client.close()


async def _bootstrap_search(bundle: ScenarioBundle) -> None:
    if not bundle.retrieval_indexes:
        logger.info("bootstrap.search: no retrieval indexes declared; skipping")
        return

    endpoint = os.environ.get("AZURE_AI_SEARCH_ENDPOINT")
    if not endpoint:
        raise RuntimeError("AZURE_AI_SEARCH_ENDPOINT is not set")

    aoai_endpoint = os.environ.get("AZURE_AI_FOUNDRY_OPENAI_ENDPOINT", "")
    embedding_deployment = os.environ.get(
        "AZURE_AI_FOUNDRY_EMBEDDING_DEPLOYMENT", ""
    )

    from azure.core.exceptions import ResourceNotFoundError
    from azure.identity.aio import DefaultAzureCredential
    from azure.search.documents.aio import SearchClient
    from azure.search.documents.indexes.aio import SearchIndexClient

    cred = DefaultAzureCredential()
    try:
        ic = SearchIndexClient(endpoint=endpoint, credential=cred)
        try:
            for entry in bundle.retrieval_indexes:
                index = entry.schema_callable(entry.name)
                wants_vector = any(
                    getattr(f, "vector_search_dimensions", None)
                    for f in (index.fields or [])
                )

                # Schema-mismatch detection. If an existing `accounts` index
                # is missing the contentVector field that the new schema
                # requires, delete it so create_or_update_index lays down
                # the new vector schema cleanly. Pre-share testing context;
                # no partner data preservation concern.
                if wants_vector:
                    try:
                        existing = await ic.get_index(entry.name)
                    except ResourceNotFoundError:
                        existing = None
                    if existing is not None:
                        existing_field_names = {
                            f.name for f in (existing.fields or [])
                        }
                        if "contentVector" not in existing_field_names:
                            logger.info(
                                "bootstrap.search: index %s lacks contentVector; "
                                "deleting and recreating with vector schema",
                                entry.name,
                            )
                            await ic.delete_index(entry.name)

                async def _create_index(_ix=index) -> None:
                    await ic.create_or_update_index(_ix)

                await _retry(
                    _create_index,
                    name=f"search.index.{entry.name}",
                    budget_seconds=_retry_budget_seconds(),
                )
                logger.info("bootstrap.search: index ok: %s", entry.name)

                seed_path = ROOT / entry.seed
                if not seed_path.exists():
                    logger.warning(
                        "bootstrap.search: seed file %s missing; skipping seeding",
                        seed_path,
                    )
                    continue

                docs = json.loads(seed_path.read_text(encoding="utf-8"))
                if not docs:
                    continue

                # Embed seeds for vector indexes so the initial corpus
                # has populated contentVector. Query-time vectorization
                # for new docs flows through the index's AzureOpenAIVectorizer.
                if wants_vector:
                    docs = await _embed_seed_docs(
                        docs, aoai_endpoint, embedding_deployment, cred
                    )

                sc = SearchClient(
                    endpoint=endpoint, index_name=entry.name, credential=cred,
                )
                try:
                    async def _upload(_sc=sc, _docs=docs) -> list[Any]:
                        return await _sc.upload_documents(documents=_docs)

                    result = await _retry(
                        _upload,
                        name=f"search.upload.{entry.name}",
                        budget_seconds=_retry_budget_seconds(),
                    )
                    failed = [r for r in result if not r.succeeded]
                    if failed:
                        raise RuntimeError(
                            f"{len(failed)} seed docs failed to upload into "
                            f"{entry.name}"
                        )
                    logger.info(
                        "bootstrap.search: seeded %d docs into %s",
                        len(docs), entry.name,
                    )
                finally:
                    await sc.close()
        finally:
            await ic.close()
    finally:
        await cred.close()


async def _canary_query(bundle: ScenarioBundle) -> None:
    """Synthetic prompt against each retrieval-using agent.

    Drives one ``agent.run()`` per foundry_tool agent through the
    ``agent_framework.azure.AzureAIClient`` SDK and asserts the response
    references at least one citation (URL or doc id) — the cheapest signal
    that the model actually invoked its attached AzureAISearchTool.

    Only runs when ``BOOTSTRAP_CANARY=1`` because each call costs a model
    + Search round-trip. Failure raises so ACA marks the revision unhealthy
    if the gpt-5-mini + AzureAISearchTool combo regresses.
    """
    if os.environ.get("BOOTSTRAP_CANARY") != "1":
        return
    foundry_tool_agents = [
        a for a in bundle.agents
        if a.retrieval is not None and a.retrieval.mode == "foundry_tool"
    ]
    if not foundry_tool_agents:
        return

    try:
        # GA SDK rename: agent_framework.azure.AzureAIClient → agent_framework.foundry.FoundryAgent.
        from agent_framework.foundry import FoundryAgent  # type: ignore
    except Exception as exc:
        logger.warning(
            "bootstrap.canary: agent-framework-foundry not importable (%s); "
            "skipping canary", exc,
        )
        return

    endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")
    if not endpoint:
        logger.warning(
            "bootstrap.canary: AZURE_AI_FOUNDRY_ENDPOINT not set; skipping",
        )
        return

    canary_prompt = (
        "Profile the account: Microsoft (microsoft.com). Use your attached "
        "AI Search knowledge tool to retrieve facts and include at least "
        "one citation. Output JSON only."
    )
    from azure.identity.aio import DefaultAzureCredential
    cred = DefaultAzureCredential()
    try:
        for agent in foundry_tool_agents:
            runner = FoundryAgent(
                project_endpoint=endpoint,
                credential=cred,
                agent_name=agent.foundry_name,
                allow_preview=True,
            )
            try:
                result = await runner.run(canary_prompt)
            except Exception as exc:
                raise RuntimeError(
                    f"bootstrap.canary: {agent.foundry_name} run failed: {exc}"
                ) from exc
            text = (getattr(result, "text", "") or "").lower()
            if "http" not in text and "url" not in text and "citations" not in text:
                raise RuntimeError(
                    f"bootstrap.canary: {agent.foundry_name} returned no "
                    f"citation marker — tool likely not invoked. "
                    f"First 400 chars: {text[:400]!r}"
                )
            logger.info(
                "bootstrap.canary: %s ok (%d chars)",
                agent.foundry_name, len(text),
            )
    finally:
        try:
            await cred.close()
        except Exception:  # noqa: S110
            pass


async def bootstrap(bundle: ScenarioBundle) -> None:
    """Run the full deploy-time bootstrap. Idempotent.

    Skipped entirely when ``BOOTSTRAP_SKIP=1`` (local dev / unit tests).
    Any unrecoverable error propagates — callers (the FastAPI lifespan) should
    let it abort process startup so ACA marks the revision unhealthy.
    """
    if os.environ.get("BOOTSTRAP_SKIP") == "1":
        logger.info("bootstrap: BOOTSTRAP_SKIP=1; skipping")
        return

    logger.info("bootstrap: starting (budget=%.0fs)", _retry_budget_seconds())
    started = time.monotonic()
    # Order is load-bearing: the AI Search vector index must exist before
    # FoundryIQ can wrap it as a project Index asset, and the asset must
    # exist before the Foundry agent's AzureAISearchTool can reference its
    # ``index_asset_id``.
    await _bootstrap_search(bundle)
    asset_ids = await _bootstrap_indexes(bundle)
    await _bootstrap_foundry(bundle, asset_ids)
    await _canary_query(bundle)
    logger.info(
        "bootstrap: complete in %.1fs (%d agents, %d index(es), %d FoundryIQ asset(s))",
        time.monotonic() - started,
        len(bundle.agents),
        len(bundle.retrieval_indexes),
        len(asset_ids),
    )
