"""Create or verify Foundry agents for the flagship workflow.

Called from ``azure.yaml`` ``postprovision`` hook. Idempotent.

Behaviour:
1. Pre-flight: verifies the project endpoint is reachable, the expected model
   deployment exists on the parent Cognitive Services account, and a RAI
   (content filter) policy is bound to that deployment. If any check fails,
   exits non-zero with an actionable message so partners know to re-run
   ``azd up`` or fix quota rather than chasing a Foundry agent error.
2. Reads the 5 agent spec Markdown files in ``docs/agent-specs/``.
3. Connects to the Foundry project identified by ``AZURE_AI_FOUNDRY_ENDPOINT``
   using ``DefaultAzureCredential``.
4. For each spec, creates or updates the named agent with the spec's
   instructions + model. The bootstrap is the ONLY place instructions flow
   from the repo into Foundry — after this, the Foundry portal is the
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
    # azure-ai-projects is the current Foundry SDK; agents are accessed via
    # `project_client.agents` (wrapping azure-ai-agents).
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

AGENT_NAMES = [
    "accel-sales-research-supervisor",
    "accel-account-planner",
    "accel-icp-fit-analyst",
    "accel-competitive-context",
    "accel-outreach-personalizer",
]


_MODEL_RE = re.compile(r"^\*\*Model:\*\*\s*(\S+)", re.MULTILINE)
_INSTRUCTIONS_RE = re.compile(r"## Instructions\s*\n(.*)", re.DOTALL)


def _parse_spec(path: pathlib.Path) -> str:
    """Return the ``## Instructions`` body of the spec file.

    Model is deliberately NOT read from the spec — every agent uses the
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


def _preflight(credential: DefaultAzureCredential) -> list[str]:
    """Management-plane checks. Returns list of error strings (empty == ok)."""
    errors: list[str] = []
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    resource_group = os.environ.get("AZURE_RESOURCE_GROUP")
    account_name = os.environ.get("AZURE_AI_FOUNDRY_ACCOUNT_NAME")
    deployment_name = os.environ.get("AZURE_AI_FOUNDRY_MODEL")

    if not (subscription_id and resource_group and account_name and deployment_name):
        errors.append(
            "pre-flight requires AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, "
            "AZURE_AI_FOUNDRY_ACCOUNT_NAME, and AZURE_AI_FOUNDRY_MODEL "
            "(all emitted by Bicep). Run inside an `azd` env or pass "
            "--skip-preflight to bypass."
        )
        return errors

    if not _HAS_MGMT:
        errors.append(
            "azure-mgmt-cognitiveservices is not installed; "
            "pip install azure-mgmt-cognitiveservices or pass --skip-preflight"
        )
        return errors

    mgmt = CognitiveServicesManagementClient(credential, subscription_id)

    try:
        deployment = mgmt.deployments.get(resource_group, account_name, deployment_name)
    except Exception as exc:
        errors.append(
            f"model deployment '{deployment_name}' not found on account "
            f"'{account_name}' in '{resource_group}': {exc}. "
            "Re-run `azd up` or fix model capacity quota."
        )
        return errors

    rai_policy = getattr(deployment.properties, "rai_policy_name", None)
    if not rai_policy:
        errors.append(
            f"model deployment '{deployment_name}' has no RAI (content filter) "
            "policy bound. Re-run `azd up` so Bicep reapplies the default "
            "accelerator content filter policy."
        )
        return errors

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

    default_model = os.environ.get("AZURE_AI_FOUNDRY_MODEL")
    if not default_model:
        print("::error::AZURE_AI_FOUNDRY_MODEL is not set; it is emitted by "
              "Bicep and is the authoritative model deployment for all agents",
              file=sys.stderr)
        return 1

    credential = DefaultAzureCredential()

    if not args.skip_preflight:
        errors = _preflight(credential)
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
    for name in AGENT_NAMES:
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
                print(f"verify ok: {name}")
            continue

        try:
            if name in existing_by_name:
                agent = existing_by_name[name]
                client.agents.update_agent(
                    agent_id=agent.id,
                    model=default_model,
                    instructions=instructions,
                )
                print(f"updated: {name} (model={default_model})")
            else:
                client.agents.create_agent(
                    name=name,
                    model=default_model,
                    instructions=instructions,
                )
                print(f"created: {name} (model={default_model})")
        except Exception as exc:
            failures.append(f"{name}: {exc}")

    if failures:
        for f in failures:
            print(f"::error::{f}", file=sys.stderr)
        return 1

    print(f"bootstrap ok: {len(AGENT_NAMES)} agents verified in {endpoint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
