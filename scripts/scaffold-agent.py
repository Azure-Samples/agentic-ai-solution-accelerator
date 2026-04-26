"""Scaffold a new worker agent into an existing scenario.

Usage::

    python scripts/scaffold-agent.py <agent_id> --scenario <scenario-id>
        --capability "<one-sentence capability>"
        [--depends-on other_agent_id,another_id]
        [--required | --optional]

Creates the three-layer agent module, wires it into the scenario's
``agents/__init__.py``, appends a ``_build_input_<agent_id>`` helper and a
``WorkerSpec`` entry to the scenario's ``workflow.py``, and drops a Foundry
agent spec stub under ``docs/agent-specs/``. Prints a YAML snippet for the
operator to paste into ``accelerator.yaml.scenario.agents[]`` (explicit
operator review - the scaffolder never edits the manifest itself).

Re-run safe: a second invocation with the same args exits non-zero without
changing anything (detected via conflict checks below).

Safety contract (fails fast if any assumption is violated - message tells
the partner the file is no longer scaffold-managed and must be edited by
hand):

1. ``agents/__init__.py`` must contain one ``from . import (...)`` statement
   naming every registered agent submodule.
2. ``workflow.py`` must contain:
   - one ``from .agents import (...)`` statement naming the same set, and
   - exactly one module-level ``WORKERS = { ... }`` assignment whose value
     is a Python dict literal (``ast.Dict`` node).
3. The target ``agent_id`` must NOT already appear as a ``WorkerSpec`` entry,
   module, or folder on disk.

All edits are applied transactionally. Before any write the scaffolder
snapshots the original bytes of every file it will mutate; on any failure
it restores originals and deletes files/directories it created.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys
from typing import Callable

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_SCENARIO_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class ScaffoldError(Exception):
    """Raised when the scaffolder refuses to proceed."""


# ---------------------------------------------------------------------------
# Manifest lookup
# ---------------------------------------------------------------------------
def _load_scenario(scenario_id: str) -> tuple[str, str]:
    """Return ``(package_dotted, package_leaf)`` for ``scenario_id``.

    Raises ``ScaffoldError`` if the manifest is missing or the scenario
    doesn't match; does NOT require all agents declared in the manifest to
    exist yet (lint handles that).
    """
    manifest = ROOT / "accelerator.yaml"
    if not manifest.exists():
        raise ScaffoldError("accelerator.yaml is missing at repo root")
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    scenario = data.get("scenario") or {}
    if scenario.get("id") != scenario_id:
        raise ScaffoldError(
            f"active scenario is {scenario.get('id')!r}, not {scenario_id!r}. "
            "Switch the manifest or pick the correct --scenario."
        )
    pkg = scenario.get("package")
    if not isinstance(pkg, str) or not pkg:
        raise ScaffoldError("scenario.package is missing or empty in accelerator.yaml")
    return pkg, pkg.split(".")[-1]


# ---------------------------------------------------------------------------
# File templates (new files)
# ---------------------------------------------------------------------------
def _agent_foundry_name(scenario_id: str, agent_id: str) -> str:
    return f"accel-{scenario_id}-{agent_id.replace('_', '-')}"


AGENT_TEMPLATES: dict[str, Callable[[str, str, str], str]] = {
    "__init__.py": lambda sid, aid, cap: (
        f'"""{aid} agent - {cap}."""\n'
        "from .prompt import build_prompt\n"
        "from .transform import transform_response\n"
        "from .validate import validate_response\n\n"
        f'AGENT_NAME = "{_agent_foundry_name(sid, aid)}"\n\n'
        '__all__ = ["AGENT_NAME", "build_prompt", "transform_response", '
        '"validate_response"]\n'
    ),
    "prompt.py": lambda sid, aid, cap: (
        f'"""{aid} prompt builder - pure function, no side effects.\n\n'
        f"Capability: {cap}\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n\n"
        "def build_prompt(request_data: dict[str, Any]) -> str:\n"
        "    return (\n"
        f'        "Task: {cap}.\\n"\n'
        '        f"Context: {request_data}.\\n"\n'
        '        "Output: JSON matching the documented schema; include "\n'
        '        "`sources: []` for any factual claim.\\n"\n'
        "    )\n"
    ),
    "transform.py": lambda sid, aid, cap: (
        f'"""Normalise {aid} output to a dict."""\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "from typing import Any\n\n\n"
        "def transform_response(response: str) -> dict[str, Any]:\n"
        "    if not response:\n"
        "        return {}\n"
        "    try:\n"
        "        return json.loads(response)\n"
        "    except json.JSONDecodeError:\n"
        '        start, end = response.find("{"), response.rfind("}")\n'
        "        if start >= 0 and end > start:\n"
        "            return json.loads(response[start:end + 1])\n"
        '        return {"text": response}\n'
    ),
    "validate.py": lambda sid, aid, cap: (
        f'"""Validate {aid} output shape."""\n'
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n\n"
        "REQUIRED_FIELDS: tuple[str, ...] = ()\n\n\n"
        "def validate_response(response: dict[str, Any]) -> tuple[bool, str]:\n"
        "    if not isinstance(response, dict):\n"
        '        return False, "response must be a JSON object"\n'
        "    missing = [f for f in REQUIRED_FIELDS if f not in response]\n"
        "    if missing:\n"
        '        return False, f"missing fields: {missing}"\n'
        '    if response.get("factual_claims") and not response.get("sources"):\n'
        '        return False, "factual claims without sources"\n'
        '    return True, ""\n'
    ),
}


SPEC_TEMPLATE = """# {agent_name}

Foundry agent spec for the ``{sid}`` scenario's ``{aid}`` worker. Instructions
below are synced to the Foundry portal by ``src/bootstrap.py``;
the model comes from ``AZURE_AI_FOUNDRY_MODEL`` (emitted by Bicep) - do NOT
add a ``**Model:**`` field here (the lint blocks it).

## Capability

{capability}

## Instructions

You are the ``{aid}`` worker agent for the ``{sid}`` scenario. Your capability
is stated above. Produce a JSON object matching the scenario schema. Every
factual claim MUST include a citation in ``sources: []``. Never call
side-effect tools directly; the supervisor + HITL gate drive those.
"""


# ---------------------------------------------------------------------------
# In-place patching
# ---------------------------------------------------------------------------
_IMPORT_RE = re.compile(
    r"^from \.agents import \(\s*([^)]*?)\s*\)\s*$",
    re.MULTILINE | re.DOTALL,
)
_PKG_IMPORT_RE = re.compile(
    r"^from \. import \(\s*([^)]*?)\s*\)\s*$",
    re.MULTILINE | re.DOTALL,
)
_ALL_RE = re.compile(
    r"^__all__\s*=\s*\[\s*([^\]]*?)\s*\]\s*$",
    re.MULTILINE | re.DOTALL,
)


def _parse_name_tuple(block: str) -> list[str]:
    """Parse a comma-separated names block (whitespace / newlines tolerated)."""
    return [n.strip().strip('"').strip("'") for n in block.split(",") if n.strip()]


def _patch_agents_init(text: str, agent_id: str) -> str:
    """Insert ``agent_id`` into ``agents/__init__.py``'s import + __all__."""
    pkg_match = _PKG_IMPORT_RE.search(text)
    if not pkg_match:
        raise ScaffoldError(
            "agents/__init__.py: expected one `from . import ( ... )` block. "
            "File no longer scaffold-managed; edit manually."
        )
    names = _parse_name_tuple(pkg_match.group(1))
    if agent_id in names:
        raise ScaffoldError(
            f"agents/__init__.py already imports {agent_id!r}"
        )
    new_names = sorted(names + [agent_id])
    new_import = "from . import (\n    " + ",\n    ".join(new_names) + ",\n)"
    text = text[: pkg_match.start()] + new_import + text[pkg_match.end():]

    all_match = _ALL_RE.search(text)
    if not all_match:
        raise ScaffoldError(
            "agents/__init__.py: expected one `__all__ = [ ... ]` list. "
            "File no longer scaffold-managed; edit manually."
        )
    all_names = [
        n for n in _parse_name_tuple(all_match.group(1)) if n and not n.startswith("#")
    ]
    if agent_id in all_names:
        raise ScaffoldError(
            f"agents/__init__.py __all__ already lists {agent_id!r}"
        )
    new_all_names = sorted(all_names + [agent_id])
    new_all = (
        "__all__ = [\n    "
        + ",\n    ".join(f'"{n}"' for n in new_all_names)
        + ",\n]"
    )
    text = text[: all_match.start()] + new_all + text[all_match.end():]
    return text


def _locate_workers_dict(tree: ast.Module) -> ast.AST:
    """Return the single module-level ``WORKERS = {...}`` assignment node.

    Accepts both plain ``Assign`` and annotated ``AnnAssign`` forms so a
    type annotation (``WORKERS: dict[str, WorkerSpec] = {...}``) stays
    scaffold-managed.
    """
    candidates: list[ast.AST] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "WORKERS"
            and isinstance(node.value, ast.Dict)
        ):
            candidates.append(node)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "WORKERS"
            and isinstance(node.value, ast.Dict)
        ):
            candidates.append(node)
    if len(candidates) != 1:
        raise ScaffoldError(
            "workflow.py: expected exactly one module-level "
            "`WORKERS = { ... }` dict literal; found "
            f"{len(candidates)}. File no longer scaffold-managed; edit "
            "manually."
        )
    return candidates[0]


def _patch_workflow(
    text: str,
    agent_id: str,
    depends_on: list[str],
    required: bool,
) -> str:
    """Insert ``_build_input_<agent_id>`` + ``WORKERS`` entry + import."""
    # 1. import
    imp_match = _IMPORT_RE.search(text)
    if not imp_match:
        raise ScaffoldError(
            "workflow.py: expected one `from .agents import ( ... )` block. "
            "File no longer scaffold-managed; edit manually."
        )
    imp_names = _parse_name_tuple(imp_match.group(1))
    if agent_id in imp_names:
        raise ScaffoldError(
            f"workflow.py already imports {agent_id!r} from .agents"
        )
    new_imp_names = sorted(imp_names + [agent_id])
    new_imp = (
        "from .agents import (\n    "
        + ",\n    ".join(new_imp_names)
        + ",\n)"
    )
    text = text[: imp_match.start()] + new_imp + text[imp_match.end():]

    # 2. reject if helper/entry exists
    if f"_build_input_{agent_id}" in text:
        raise ScaffoldError(
            f"workflow.py already defines _build_input_{agent_id}"
        )
    if re.search(rf'"{re.escape(agent_id)}"\s*:\s*WorkerSpec', text):
        raise ScaffoldError(
            f"workflow.py WORKERS already has entry {agent_id!r}"
        )

    # 3. AST-locate WORKERS dict assignment
    tree = ast.parse(text)
    workers_node = _locate_workers_dict(tree)
    # Insertion point for the helper: immediately BEFORE the WORKERS assignment.
    # end_lineno gives the dict's closing brace line (1-based).
    helper_insert_line = workers_node.lineno  # 1-based line OF the `WORKERS = ...`
    dict_close_line = workers_node.end_lineno or workers_node.lineno

    # Validate depends_on against already-imported worker modules.
    for dep in depends_on:
        if dep not in new_imp_names or dep == agent_id:
            raise ScaffoldError(
                f"--depends-on names unknown agent {dep!r}; known: "
                f"{', '.join(n for n in new_imp_names if n != agent_id)}"
            )

    # 4. Build the new snippets.
    deps_literal = (
        "frozenset()"
        if not depends_on
        else "frozenset({" + ", ".join(f'"{d}"' for d in depends_on) + "})"
    )
    required_literal = "" if required else ",\n        required=False"

    helper = (
        f"def _build_input_{agent_id}(state: WorkerState) -> dict[str, Any]:\n"
        "    # TODO(scaffold-agent): pass the upstream outputs or request "
        f"fields this worker needs.\n"
        "    return {\n"
        + "".join(
            f'        "{d}": state.outputs["{d}"],\n' for d in depends_on
        )
        + "        \"request\": dict(state.request),\n"
        "    }\n\n\n"
    )

    entry = (
        f'    "{agent_id}": WorkerSpec(\n'
        f'        id="{agent_id}",\n'
        f"        module={agent_id},\n"
        f"        build_input=_build_input_{agent_id},\n"
        f"        depends_on={deps_literal}{required_literal},\n"
        "    ),\n"
    )

    # 5. Text-edit: split into lines, insert helper before WORKERS line,
    # insert entry before dict close line (the line with the lone `}`).
    lines = text.splitlines(keepends=True)
    # Insert entry first (larger line number) so helper insertion indices
    # remain stable.
    close_idx = dict_close_line - 1  # 0-based
    # The close line is expected to be `}\n` (with any indentation). We insert
    # right BEFORE it.
    close_line = lines[close_idx]
    if close_line.strip() != "}":
        raise ScaffoldError(
            "workflow.py: WORKERS dict close line does not match the "
            "expected `}` on its own line. File no longer scaffold-managed."
        )
    lines.insert(close_idx, entry)

    # Helper insertion: before `WORKERS = {` line.
    helper_idx = helper_insert_line - 1  # 0-based
    lines.insert(helper_idx, helper)

    return "".join(lines)


# ---------------------------------------------------------------------------
# Plan / apply
# ---------------------------------------------------------------------------
def _plan_new_files(
    scenario_id: str, pkg_leaf: str, agent_id: str, capability: str
) -> list[tuple[pathlib.Path, str]]:
    pkg_root = ROOT / "src" / "scenarios" / pkg_leaf / "agents" / agent_id
    agent_name = _agent_foundry_name(scenario_id, agent_id)
    files: list[tuple[pathlib.Path, str]] = []
    for rel, tmpl in AGENT_TEMPLATES.items():
        files.append((pkg_root / rel, tmpl(scenario_id, agent_id, capability)))
    files.append((
        ROOT / "docs" / "agent-specs" / f"{agent_name}.md",
        SPEC_TEMPLATE.format(agent_name=agent_name, sid=scenario_id,
                             aid=agent_id, capability=capability),
    ))
    return files


def _rollback(
    new_paths: list[pathlib.Path],
    snapshots: dict[pathlib.Path, str],
) -> None:
    for p in reversed(new_paths):
        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
        except Exception as exc:
            print(
                f"::warning::rollback could not remove {p}: {exc}",
                file=sys.stderr,
            )
    for path, original in snapshots.items():
        try:
            path.write_text(original, encoding="utf-8")
        except Exception as exc:
            print(
                f"::warning::rollback could not restore {path}: {exc}",
                file=sys.stderr,
            )


MANIFEST_SNIPPET = """# Append under `scenario.agents` in accelerator.yaml:
    - {{ id: {aid}, foundry_name: {agent_name} }}

# Then add at least one golden case that exercises this worker in
# evals/quality/golden_cases.jsonl (or extend an existing case). The
# `agent_has_golden_case` lint rule blocks until this is done:
#   "exercises": [... , "{aid}"]
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "agent_id",
        help="snake_case id; appears in code and as a worker key",
    )
    ap.add_argument(
        "--scenario", required=True,
        help="scenario slug from accelerator.yaml (e.g. 'sales-research')",
    )
    ap.add_argument(
        "--capability", required=True,
        help="one-sentence capability; used in the prompt + spec stubs",
    )
    ap.add_argument(
        "--depends-on", default="",
        help="comma-separated worker ids this agent depends on",
    )
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--required", dest="required", action="store_true",
                       default=True,
                       help="(default) required=True; a failure fails the request")
    group.add_argument("--optional", dest="required", action="store_false",
                       help="required=False; a failure skips downstream dependents")
    args = ap.parse_args()

    agent_id = args.agent_id.strip()
    scenario_id = args.scenario.strip()
    capability = args.capability.strip()

    if not _ID_RE.match(agent_id):
        print(
            f"::error::invalid agent id {agent_id!r}; must match ^[a-z][a-z0-9_]*$",
            file=sys.stderr,
        )
        return 2
    if not _SCENARIO_ID_RE.match(scenario_id):
        print(
            f"::error::invalid scenario id {scenario_id!r}",
            file=sys.stderr,
        )
        return 2
    if not capability:
        print("::error::--capability is required", file=sys.stderr)
        return 2

    depends_on = [d.strip() for d in args.depends_on.split(",") if d.strip()]
    if agent_id in depends_on:
        print("::error::--depends-on cannot include the agent's own id",
              file=sys.stderr)
        return 2

    try:
        pkg_dotted, pkg_leaf = _load_scenario(scenario_id)
    except ScaffoldError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    # Conflict: folder must not exist.
    agent_dir = ROOT / "src" / "scenarios" / pkg_leaf / "agents" / agent_id
    if agent_dir.exists():
        print(f"::error::agent directory already exists: {agent_dir}",
              file=sys.stderr)
        return 2

    new_files_plan = _plan_new_files(scenario_id, pkg_leaf, agent_id, capability)
    conflicts = [p for p, _ in new_files_plan if p.exists()]
    if conflicts:
        print("::error::targets already exist; refusing to overwrite:",
              file=sys.stderr)
        for p in conflicts:
            print(f"  {p}", file=sys.stderr)
        return 2

    # Files to patch.
    agents_init = ROOT / "src" / "scenarios" / pkg_leaf / "agents" / "__init__.py"
    workflow_py = ROOT / "src" / "scenarios" / pkg_leaf / "workflow.py"
    if not agents_init.exists() or not workflow_py.exists():
        print(
            f"::error::scenario files missing: {agents_init} or {workflow_py}",
            file=sys.stderr,
        )
        return 2

    # Snapshot originals before any write (transactional).
    snapshots: dict[pathlib.Path, str] = {
        agents_init: agents_init.read_text(encoding="utf-8"),
        workflow_py: workflow_py.read_text(encoding="utf-8"),
    }

    created: list[pathlib.Path] = []
    try:
        # Patch existing files (may raise ScaffoldError BEFORE any new file is
        # created, leaving the repo untouched).
        new_agents_init = _patch_agents_init(snapshots[agents_init], agent_id)
        new_workflow = _patch_workflow(
            snapshots[workflow_py], agent_id, depends_on, args.required
        )

        # Write new files.
        for path, content in new_files_plan:
            path.parent.mkdir(parents=True, exist_ok=True)
            for anc in reversed(path.parents):
                if anc == ROOT or anc in created:
                    continue
                if anc.exists() and anc.is_dir() and not any(anc.iterdir()):
                    created.append(anc)
            path.write_text(content, encoding="utf-8")
            created.append(path)

        # Write patched files.
        agents_init.write_text(new_agents_init, encoding="utf-8")
        workflow_py.write_text(new_workflow, encoding="utf-8")

        # Syntax-validate the mutated workflow so a broken patch can't sneak
        # into CI. A syntax error here triggers rollback.
        try:
            ast.parse(new_workflow)
        except SyntaxError as exc:
            raise ScaffoldError(
                f"patched workflow.py failed to parse: {exc}"
            ) from exc

        agent_name = _agent_foundry_name(scenario_id, agent_id)
        print(f"scaffolded agent: {agent_dir.relative_to(ROOT)}")
        print("")
        print(MANIFEST_SNIPPET.format(aid=agent_id, agent_name=agent_name))
        print("Run `python scripts/accelerator-lint.py` to confirm 0 findings.")
        return 0

    except ScaffoldError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        _rollback(created, snapshots)
        print("::error::rolled back.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"::error::scaffold failed: {exc}", file=sys.stderr)
        _rollback(created, snapshots)
        print("::error::rolled back.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
