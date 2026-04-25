"""Materialize a new scenario skeleton under ``src/scenarios/<package>/``.

Usage::

    python scripts/scaffold-scenario.py <scenario-id> --display "Human Name"
    python scripts/scaffold-scenario.py order-triage --display "Order Triage"

Creates:
- ``src/scenarios/<package>/__init__.py``
- ``src/scenarios/<package>/schema.py``         (request BaseModel stub)
- ``src/scenarios/<package>/workflow.py``       (BaseWorkflow + build_workflow factory)
- ``src/scenarios/<package>/retrieval.py``      (index_definition stub)
- ``src/scenarios/<package>/agents/__init__.py``
- ``src/scenarios/<package>/agents/supervisor/{__init__,prompt,transform,validate}.py``
- ``docs/agent-specs/accel-<scenario-id>-supervisor.md`` (spec stub)
- ``data/samples/<package>.json``               (empty seed)

Behaviour:
- Fails fast if any target path already exists (no accidental overwrites).
- On failure mid-run, removes paths it created in this invocation (best-effort
  rollback; existing files are left untouched).
- Does NOT edit ``accelerator.yaml`` automatically; prints the ``scenario:``
  block to paste in manually so operator review is explicit.

Guardrails:
- Scenario IDs may contain hyphens (``order-triage``); package dirs are
  auto-converted to underscores (``order_triage``) because Python imports
  require it.
- Rejects IDs that aren't lowercase alphanumerics (with hyphens).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Callable

ROOT = pathlib.Path(__file__).resolve().parent.parent
_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def _package_leaf(scenario_id: str) -> str:
    return scenario_id.replace("-", "_")


def _supervisor_foundry_name(scenario_id: str) -> str:
    return f"accel-{scenario_id}-supervisor"


TEMPLATES: dict[str, Callable[[str, str], str]] = {
    "__init__.py": lambda sid, leaf: (
        f'"""Scenario: {sid}.\n\n'
        f"Exports are intentionally empty — the scenario is consumed via\n"
        f":mod:`src.workflow.registry` which resolves ``schema:`` and\n"
        f'``workflow_factory:`` by module path from ``accelerator.yaml``.\n"""\n'
    ),
    "schema.py": lambda sid, leaf: (
        '"""Request schema for the {sid} scenario."""\n'
        'from __future__ import annotations\n\n'
        'from pydantic import BaseModel\n\n\n'
        'class ScenarioRequest(BaseModel):\n'
        '    """Inputs the scenario accepts. Extend as needed."""\n'
        '    query: str\n'
    ).format(sid=sid),
    "retrieval.py": lambda sid, leaf: (
        '"""Index definitions for the {sid} scenario."""\n'
        'from __future__ import annotations\n\n'
        'from azure.search.documents.indexes.models import (\n'
        '    SearchableField,\n'
        '    SearchFieldDataType,\n'
        '    SearchIndex,\n'
        '    SimpleField,\n'
        ')\n\n\n'
        'def index_definition(name: str) -> SearchIndex:\n'
        '    """Return the default index for this scenario."""\n'
        '    return SearchIndex(\n'
        '        name=name,\n'
        '        fields=[\n'
        '            SimpleField(name="id", type=SearchFieldDataType.String, key=True),\n'
        '            SearchableField(name="content", type=SearchFieldDataType.String),\n'
        '        ],\n'
        '    )\n'
    ).format(sid=sid),
    "workflow.py": lambda sid, leaf: (
        '"""Workflow for the {sid} scenario."""\n'
        'from __future__ import annotations\n\n'
        'from typing import Any, AsyncIterator\n\n'
        'from src.accelerator_baseline.killswitch import assert_enabled\n'
        'from src.accelerator_baseline.telemetry import Event, emit_event\n'
        'from src.workflow.base import BaseWorkflow\n\n'
        'from .agents import supervisor\n\n\n'
        'class {class_name}Workflow:\n'
        '    """Minimal supervisor-only workflow. Extend with workers as needed."""\n\n'
        '    def __init__(self, *, primary_index_name: str = "") -> None:\n'
        '        self._primary_index_name = primary_index_name\n\n'
        '    async def stream(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:\n'
        '        assert_enabled("workflow")\n'
        '        emit_event(Event(name="request.received"))\n'
        '        yield {{"type": "status", "stage": "supervisor.planning"}}\n'
        '        # TODO: invoke supervisor + workers here\n'
        '        emit_event(Event(name="response.returned", ok=True))\n'
        '        yield {{"type": "final", "briefing": {{"echo": request}}}}\n\n\n'
        'def build_workflow(context: Any) -> BaseWorkflow:\n'
        '    indexes = getattr(context, "retrieval_indexes", ()) or ()\n'
        '    primary = indexes[0].name if indexes else ""\n'
        '    return {class_name}Workflow(primary_index_name=primary)\n'
    ).format(sid=sid, class_name="".join(p.title() for p in leaf.split("_"))),
    "agents/__init__.py": lambda sid, leaf: (
        f'"""Agent registry for {sid}. Add workers here as they scaffold in."""\n'
        f"from . import supervisor\n\n"
        f'__all__ = ["supervisor"]\n'
    ),
    "agents/supervisor/__init__.py": lambda sid, leaf: (
        f'"""Supervisor agent for {sid}."""\n'
        f"from .prompt import build_prompt\n"
        f"from .transform import transform_response\n"
        f"from .validate import validate_response\n\n"
        f'AGENT_NAME = "{_supervisor_foundry_name(sid)}"\n'
        f'__all__ = ["AGENT_NAME", "build_prompt", "transform_response", '
        f'"validate_response"]\n'
    ),
    "agents/supervisor/prompt.py": lambda sid, leaf: (
        '"""Supervisor prompt builder - pure function, no side effects."""\n'
        'from __future__ import annotations\n\n'
        'from typing import Any\n\n\n'
        'def build_prompt(request: dict[str, Any]) -> str:\n'
        '    return (\n'
        '        "You are the supervisor. Plan the workers and synthesise the final "\n'
        '        f"briefing.\\nREQUEST:\\n{request}\\n"\n'
        '    )\n'
    ),
    "agents/supervisor/transform.py": lambda sid, leaf: (
        '"""Normalise supervisor output to a dict."""\n'
        'from __future__ import annotations\n\n'
        'import json\n'
        'from typing import Any\n\n\n'
        'def transform_response(raw: str) -> dict[str, Any]:\n'
        '    if not raw:\n'
        '        return {}\n'
        '    try:\n'
        '        return json.loads(raw)\n'
        '    except Exception:\n'
        '        return {"text": raw}\n'
    ),
    "agents/supervisor/validate.py": lambda sid, leaf: (
        '"""Validate supervisor output shape."""\n'
        'from __future__ import annotations\n\n'
        'from typing import Any\n\n\n'
        'def validate_response(data: dict[str, Any]) -> tuple[bool, str]:\n'
        '    if not isinstance(data, dict):\n'
        '        return False, "supervisor output must be a JSON object"\n'
        '    return True, ""\n'
    ),
}


SPEC_TEMPLATE = """# {agent_name}

> **This file IS your agent's system instructions.** The `## Instructions`
> section below is synced **verbatim** to the Foundry portal by
> `scripts/foundry-bootstrap.py` on every `azd up`. **Edit this file to
> change agent behaviour.** Never put agent system instructions in Python
> code — `prompt.py` builds *per-request* input, not system instructions.

Foundry agent spec for the {sid} scenario's supervisor. The model comes
from ``AZURE_AI_FOUNDRY_MODEL`` (emitted by Bicep) - do NOT add a
``**Model:**`` field here (the lint blocks it).

## Instructions

You are the supervisor agent for the {sid} scenario. **Replace this
paragraph with the real system instructions for your scenario** — describe
the agent's role, the exact JSON output contract, grounding rules, and any
HITL-related obligations. Your job is to plan which worker agents to invoke
for each request, and to synthesise their outputs into a single final
briefing. Follow the accelerator's HITL + grounding policies; never call
side-effect tools directly.
"""


MANIFEST_SNIPPET = """# Paste this under the existing `scenario:` block, or replace the current one.
scenario:
  id: {sid}
  package: src.scenarios.{leaf}
  request_schema: schema:ScenarioRequest
  workflow_factory: workflow:build_workflow
  endpoint:
    path: /{leaf}/stream
  agents:
    - {{ id: supervisor, foundry_name: {agent_name} }}
  retrieval:
    indexes:
      - name: {leaf}
        seed: data/samples/{leaf}.json
        schema: retrieval:index_definition
  evals:
    quality_dataset: evals/quality/golden_cases.jsonl
    redteam_dataset: evals/redteam/cases.jsonl
"""


def _plan(scenario_id: str) -> list[tuple[pathlib.Path, str]]:
    leaf = _package_leaf(scenario_id)
    pkg_root = ROOT / "src" / "scenarios" / leaf
    agent_name = _supervisor_foundry_name(scenario_id)
    files: list[tuple[pathlib.Path, str]] = []
    for rel, tmpl in TEMPLATES.items():
        files.append((pkg_root / rel, tmpl(scenario_id, leaf)))
    files.append((
        ROOT / "docs" / "agent-specs" / f"{agent_name}.md",
        SPEC_TEMPLATE.format(agent_name=agent_name, sid=scenario_id),
    ))
    files.append((
        ROOT / "data" / "samples" / f"{leaf}.json",
        "[]\n",
    ))
    return files


def _rollback(created: list[pathlib.Path]) -> None:
    for p in reversed(created):
        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                # only remove if empty
                try:
                    p.rmdir()
                except OSError:
                    pass
        except Exception as exc:
            print(f"::warning::rollback could not remove {p}: {exc}",
                  file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario_id",
                    help="slug (lowercase; hyphens ok). E.g. 'order-triage'.")
    ap.add_argument("--display", default="",
                    help="(reserved) human-readable display name")
    args = ap.parse_args()

    sid = args.scenario_id.strip()
    if not _ID_RE.match(sid):
        print(f"::error::invalid scenario id {sid!r}; must match "
              f"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", file=sys.stderr)
        return 2

    plan = _plan(sid)
    conflicts = [p for p, _ in plan if p.exists()]
    if conflicts:
        print("::error::targets already exist; refusing to overwrite:",
              file=sys.stderr)
        for p in conflicts:
            print(f"  {p}", file=sys.stderr)
        return 2

    created: list[pathlib.Path] = []
    try:
        for path, content in plan:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Track the directory chain so rollback is complete.
            for anc in reversed(path.parents):
                if anc == ROOT or anc in created:
                    continue
                if anc.exists() and anc.is_dir() and not any(anc.iterdir()):
                    created.append(anc)
            path.write_text(content, encoding="utf-8")
            created.append(path)
        leaf = _package_leaf(sid)
        agent_name = _supervisor_foundry_name(sid)
        print(f"scaffolded scenario: src/scenarios/{leaf}/")
        print("")
        print("Next step — paste this into accelerator.yaml:")
        print("")
        print(MANIFEST_SNIPPET.format(
            sid=sid, leaf=leaf, agent_name=agent_name,
        ))
        return 0
    except Exception as exc:
        print(f"::error::scaffold failed: {exc}", file=sys.stderr)
        _rollback(created)
        print("::error::rolled back partially-created paths.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
