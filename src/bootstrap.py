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
from typing import Any, Awaitable, Callable

from .workflow.registry import ROOT, ScenarioBundle

logger = logging.getLogger("accelerator.bootstrap")

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


async def _bootstrap_foundry(bundle: ScenarioBundle) -> None:
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

    # Pre-resolve specs so we fail fast on missing/malformed files BEFORE
    # touching the control plane.
    work: list[tuple[str, str, str]] = []  # (foundry_name, deployment, instructions)
    for agent in bundle.agents:
        spec_path = SPECS_DIR / f"{agent.foundry_name}.md"
        if not spec_path.exists():
            raise RuntimeError(
                f"{agent.foundry_name}: missing spec file {spec_path}"
            )
        instructions = _parse_spec(spec_path)
        deployment = model_map.get("default", "")
        work.append((agent.foundry_name, deployment, instructions))

    from azure.identity.aio import DefaultAzureCredential
    from azure.ai.agents.aio import AgentsClient

    cred = DefaultAzureCredential()
    try:
        client = AgentsClient(endpoint=endpoint, credential=cred)
        try:
            existing: dict[str, Any] = {}

            async def _list() -> None:
                async for a in client.list_agents():
                    if a.name:
                        existing[a.name] = a

            await _retry(
                _list,
                name="foundry.list_agents",
                budget_seconds=_retry_budget_seconds(),
            )

            for name, deployment, instructions in work:
                if name in existing:
                    agent_obj = existing[name]

                    async def _update(_id=agent_obj.id, _dep=deployment, _ins=instructions) -> None:
                        await client.update_agent(
                            agent_id=_id, model=_dep, instructions=_ins,
                        )

                    await _retry(
                        _update,
                        name=f"foundry.update.{name}",
                        budget_seconds=_retry_budget_seconds(),
                    )
                    logger.info("bootstrap.foundry: updated %s (model=%s)", name, deployment)
                else:
                    async def _create(_name=name, _dep=deployment, _ins=instructions) -> None:
                        await client.create_agent(
                            name=_name, model=_dep, instructions=_ins,
                        )

                    await _retry(
                        _create,
                        name=f"foundry.create.{name}",
                        budget_seconds=_retry_budget_seconds(),
                    )
                    logger.info("bootstrap.foundry: created %s (model=%s)", name, deployment)
        finally:
            await client.close()
    finally:
        await cred.close()


async def _bootstrap_search(bundle: ScenarioBundle) -> None:
    if not bundle.retrieval_indexes:
        logger.info("bootstrap.search: no retrieval indexes declared; skipping")
        return

    endpoint = os.environ.get("AZURE_AI_SEARCH_ENDPOINT")
    if not endpoint:
        raise RuntimeError("AZURE_AI_SEARCH_ENDPOINT is not set")

    from azure.identity.aio import DefaultAzureCredential
    from azure.search.documents.aio import SearchClient
    from azure.search.documents.indexes.aio import SearchIndexClient

    cred = DefaultAzureCredential()
    try:
        ic = SearchIndexClient(endpoint=endpoint, credential=cred)
        try:
            for entry in bundle.retrieval_indexes:
                index = entry.schema_callable(entry.name)

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
    await _bootstrap_foundry(bundle)
    await _bootstrap_search(bundle)
    logger.info(
        "bootstrap: complete in %.1fs (%d agents, %d index(es))",
        time.monotonic() - started,
        len(bundle.agents),
        len(bundle.retrieval_indexes),
    )
