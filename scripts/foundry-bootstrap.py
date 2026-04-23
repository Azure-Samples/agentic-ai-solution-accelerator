"""Create or verify Foundry agents for the loaded scenario.

Called from ``azure.yaml`` ``postprovision`` hook. Idempotent.

Manifest-driven: reads ``scenario.agents[]`` from ``accelerator.yaml`` and
expects a spec file at ``docs/agent-specs/<foundry_name>.md`` for each. The
``accel-sales-research-supervisor``-shaped list is no longer hardcoded here
so partners who scaffold a new scenario don't have to edit this file.

Behaviour:
1. Pre-flight: verifies the project endpoint is reachable, the expected model
   deployment exists on the parent Cognitive Services account, and a RAI
   (content filter) policy is bound to that deployment. If any check fails,
   exits non-zero with an actionable message so partners know to re-run
   ``azd up`` or fix quota rather than chasing a Foundry agent error.
2. Reads the agent spec Markdown files in ``docs/agent-specs/``.
3. Connects to the Foundry project identified by ``AZURE_AI_FOUNDRY_ENDPOINT``
   using ``DefaultAzureCredential``.
4. For each spec, creates or updates the named agent with the spec's
   instructions + model. The bootstrap is the ONLY place instructions flow
   from the repo into Foundry - after this, the Foundry portal is the
   runtime source of truth.
5. Exits non-zero if any agent is missing and we cannot create it.

Required env:
    AZURE_AI_FOUNDRY_ENDPOINT           project endpoint from Bicep output
    AZURE_AI_FOUNDRY_ACCOUNT_NAME       parent Cognitive Services account
    AZURE_AI_FOUNDRY_MODEL              model deployment name (from Bicep)
    AZURE_SUBSCRIPTION_ID               subscription for management-plane checks
    AZURE_RESOURCE_GROUP                resource group of the account

Optional:
    --verify-only       fail if any agent is missing; don't create.
    --skip-preflight    skip the management-plane deployment/RAI checks
                        (useful in CI where the MI lacks Reader on the RG).
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

from azure.identity import DefaultAzureCredential

try:
    from azure.ai.projects import AIProjectClient
except ImportError:
    print("::error::azure-ai-projects is not installed; pip install -U azure-ai-projects",
          file=sys.stderr)
    sys.exit(1)

try:
    from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
    _HAS_MGMT = True
except ImportError:
    _HAS_MGMT = False

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "docs/agent-specs"
sys.path.insert(0, str(ROOT))


_MODEL_RE = re.compile(r"^\*\*Model:\*\*\s*(\S+)", re.MULTILINE)
_INSTRUCTIONS_RE = re.compile(r"## Instructions\s*\n(.*)", re.DOTALL)


def _load_agents_from_manifest() -> list[dict]:
    """Return the list of agents (name + optional model slug) from the manifest."""
    from src.workflow.registry import read_scenario_raw

    scenario = read_scenario_raw(ROOT / "accelerator.yaml")
    agents = scenario.get("agents") or []
    out: list[dict] = []
    for i, a in enumerate(agents):
        if not isinstance(a, dict):
            raise ValueError(
                f"accelerator.yaml: scenario.agents[{i}] must be a mapping"
            )
        name = a.get("foundry_name")
        if not name:
            raise ValueError(
                f"accelerator.yaml: scenario.agents[{i}] missing 'foundry_name'"
            )
        out.append({"foundry_name": name, "model_slug": a.get("model") or "default"})
    if not out:
        raise ValueError("accelerator.yaml: scenario.agents is empty")
    return out


def _load_model_map() -> dict[str, str]:
    """Resolve slug -> deployment_name from env (emitted by Bicep output).

    Falls back to ``{"default": AZURE_AI_FOUNDRY_MODEL}`` when the map
    env var is absent (i.e. partners on the pre-G10 flow with no
    `models:` block in their manifest).
    """
    import json as _json

    default_dep = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "")
    raw = os.environ.get("AZURE_AI_FOUNDRY_MODEL_MAP", "").strip()
    if not raw:
        return {"default": default_dep} if default_dep else {}
    try:
        mapping = _json.loads(raw)
    except ValueError as exc:
        raise ValueError(
            f"AZURE_AI_FOUNDRY_MODEL_MAP is not valid JSON: {exc}. "
            "It should be the Bicep `AZURE_AI_FOUNDRY_MODEL_MAP` output."
        ) from exc
    if not isinstance(mapping, dict):
        raise ValueError(
            "AZURE_AI_FOUNDRY_MODEL_MAP must be a JSON object "
            "(slug -> deployment_name)"
        )
    return {str(k): str(v) for k, v in mapping.items()}


def _parse_spec(path: pathlib.Path) -> str:
    """Return the ``## Instructions`` body of the spec file.

    Model is deliberately NOT read from the spec - every agent uses the
    single model deployed by Bicep, exposed as ``AZURE_AI_FOUNDRY_MODEL``.
    The accelerator lint rejects any spec that re-introduces ``**Model:**``.
    """
    txt = path.read_text(encoding="utf-8")
    if _MODEL_RE.search(txt):
        raise ValueError(
            f"{path.name}: spec contains a '**Model:**' field, which is no "
            "longer allowed. The accelerator's single deployed model "
            "(AZURE_AI_FOUNDRY_MODEL) is authoritative."
        )
    instr_match = _INSTRUCTIONS_RE.search(txt)
    if not instr_match:
        raise ValueError(f"{path.name}: missing '## Instructions' section")
    return instr_match.group(1).strip()


def _preflight(credential: DefaultAzureCredential,
               deployment_names: list[str]) -> list[str]:
    """Management-plane checks for every deployment in the model map.

    Returns a list of error strings (empty == ok).
    """
    errors: list[str] = []
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    resource_group = os.environ.get("AZURE_RESOURCE_GROUP")
    account_name = os.environ.get("AZURE_AI_FOUNDRY_ACCOUNT_NAME")

    if not (subscription_id and resource_group and account_name and deployment_names):
        errors.append(
            "pre-flight requires AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, "
            "AZURE_AI_FOUNDRY_ACCOUNT_NAME, and at least one resolved model "
            "deployment (from AZURE_AI_FOUNDRY_MODEL_MAP or AZURE_AI_FOUNDRY_MODEL). "
            "Run inside an `azd` env or pass --skip-preflight to bypass."
        )
        return errors

    if not _HAS_MGMT:
        errors.append(
            "azure-mgmt-cognitiveservices is not installed; "
            "pip install azure-mgmt-cognitiveservices or pass --skip-preflight"
        )
        return errors

    mgmt = CognitiveServicesManagementClient(credential, subscription_id)

    for deployment_name in deployment_names:
        try:
            deployment = mgmt.deployments.get(
                resource_group, account_name, deployment_name
            )
        except Exception as exc:
            errors.append(
                f"model deployment '{deployment_name}' not found on account "
                f"'{account_name}' in '{resource_group}': {exc}. "
                "Re-run `azd up` or fix model capacity quota."
            )
            continue

        rai_policy = getattr(deployment.properties, "rai_policy_name", None)
        if not rai_policy:
            errors.append(
                f"model deployment '{deployment_name}' has no RAI (content filter) "
                "policy bound. Re-run `azd up` so Bicep reapplies the default "
                "accelerator content filter policy."
            )
            continue

        print(
            f"preflight ok: model={deployment_name} "
            f"sku={getattr(deployment.sku, 'name', '?')} "
            f"capacity={getattr(deployment.sku, 'capacity', '?')} "
            f"rai_policy={rai_policy}"
        )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true",
                    help="fail if any agent is missing; do not create.")
    ap.add_argument("--skip-preflight", action="store_true",
                    help="skip management-plane deployment/RAI checks.")
    args = ap.parse_args()

    endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")
    if not endpoint:
        print("::error::AZURE_AI_FOUNDRY_ENDPOINT is not set", file=sys.stderr)
        return 1

    try:
        model_map = _load_model_map()
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    if "default" not in model_map or not model_map["default"]:
        print(
            "::error::no default model deployment resolved. Set "
            "AZURE_AI_FOUNDRY_MODEL (from Bicep) or add a `models:` block with "
            "a `default: true` entry to accelerator.yaml",
            file=sys.stderr,
        )
        return 1

    try:
        agents_manifest = _load_agents_from_manifest()
    except Exception as exc:
        print(f"::error::failed to load agents from accelerator.yaml: {exc}",
              file=sys.stderr)
        return 1

    # Validate every referenced slug resolves BEFORE hitting the control plane.
    unresolved = [
        a["foundry_name"] for a in agents_manifest
        if a["model_slug"] not in model_map
    ]
    if unresolved:
        slugs = sorted({
            a["model_slug"] for a in agents_manifest
            if a["model_slug"] not in model_map
        })
        print(
            f"::error::{len(unresolved)} agent(s) reference undeclared model "
            f"slug(s) {slugs}: {unresolved}. Declare the slug in "
            "accelerator.yaml `models:` or remove the `model:` field to use "
            "the default.",
            file=sys.stderr,
        )
        return 1

    credential = DefaultAzureCredential()

    if not args.skip_preflight:
        deployments_to_check = sorted(set(model_map.values()))
        errors = _preflight(credential, deployments_to_check)
        if errors:
            for err in errors:
                print(f"::error::{err}", file=sys.stderr)
            return 1

    client = AIProjectClient(endpoint=endpoint, credential=credential)

    existing_by_name: dict[str, object] = {}
    try:
        for agent in client.agents.list_agents():
            existing_by_name[agent.name] = agent
    except Exception as exc:
        print(f"::error::failed to list agents: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for entry in agents_manifest:
        name = entry["foundry_name"]
        slug = entry["model_slug"]
        deployment_name = model_map[slug]
        spec_path = SPECS_DIR / f"{name}.md"
        if not spec_path.exists():
            failures.append(f"{name}: missing spec file {spec_path}")
            continue
        try:
            instructions = _parse_spec(spec_path)
        except ValueError as exc:
            failures.append(str(exc))
            continue

        if args.verify_only:
            if name not in existing_by_name:
                failures.append(f"{name}: missing in Foundry project")
            else:
                print(f"verify ok: {name} (slug={slug}, model={deployment_name})")
            continue

        try:
            if name in existing_by_name:
                agent = existing_by_name[name]
                client.agents.update_agent(
                    agent_id=agent.id,
                    model=deployment_name,
                    instructions=instructions,
                )
                print(f"updated: {name} (slug={slug}, model={deployment_name})")
            else:
                client.agents.create_agent(
                    name=name,
                    model=deployment_name,
                    instructions=instructions,
                )
                print(f"created: {name} (slug={slug}, model={deployment_name})")
        except Exception as exc:
            failures.append(f"{name}: {exc}")

    if failures:
        for f in failures:
            print(f"::error::{f}", file=sys.stderr)
        return 1

    print(f"bootstrap ok: {len(agents_manifest)} agents verified in {endpoint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
