"""Create or verify Foundry agents for the flagship workflow.

Called from ``azure.yaml`` ``postprovision`` hook. Idempotent.

Behaviour:
1. Reads the 5 agent spec Markdown files in ``docs/agent-specs/``.
2. Connects to the Foundry project identified by ``AZURE_AI_FOUNDRY_ENDPOINT``
   using ``DefaultAzureCredential``.
3. For each spec, creates or updates the named agent with the spec's
   instructions + model. The bootstrap is the ONLY place instructions flow
   from the repo into Foundry — after this, the Foundry portal is the
   runtime source of truth.
4. Exits non-zero if any agent is missing and we cannot create it.

Required env:
    AZURE_AI_FOUNDRY_ENDPOINT   project endpoint from Bicep output
    AZURE_AI_FOUNDRY_MODEL      model deployment name (default: gpt-5.2)

Optional:
    --verify-only    fail if any agent is missing; don't create.
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


def _parse_spec(path: pathlib.Path, default_model: str) -> tuple[str, str]:
    txt = path.read_text(encoding="utf-8")
    model_match = _MODEL_RE.search(txt)
    model = model_match.group(1).strip() if model_match else default_model
    instr_match = _INSTRUCTIONS_RE.search(txt)
    if not instr_match:
        raise ValueError(f"{path.name}: missing '## Instructions' section")
    return model, instr_match.group(1).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true",
                    help="fail if any agent is missing; do not create.")
    args = ap.parse_args()

    endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")
    if not endpoint:
        print("::error::AZURE_AI_FOUNDRY_ENDPOINT is not set", file=sys.stderr)
        return 1

    default_model = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-5.2")

    client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

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
        model, instructions = _parse_spec(spec_path, default_model)

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
                    model=model,
                    instructions=instructions,
                )
                print(f"updated: {name} (model={model})")
            else:
                client.agents.create_agent(
                    name=name,
                    model=model,
                    instructions=instructions,
                )
                print(f"created: {name} (model={model})")
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
