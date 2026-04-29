"""Verify scaffold-scenario seeds and scaffold-agent extends golden_cases.jsonl."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCAFFOLD_SCENARIO = ROOT / "scripts" / "scaffold-scenario.py"
SCAFFOLD_AGENT = ROOT / "scripts" / "scaffold-agent.py"


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_scenario_stub_has_supervisor_in_exercises():
    sc = _load("scaffold_scenario_evals", SCAFFOLD_SCENARIO)
    line = sc._golden_cases_stub("contoso-x")
    case = json.loads(line)
    assert case["case_id"] == "q-001"
    assert case["scenario"] == "contoso-x"
    assert case["exercises"] == ["supervisor"]
    assert case["expected"]["must_cite"] is False


def test_extend_appends_agent_id_to_each_case():
    sa = _load("scaffold_agent_evals", SCAFFOLD_AGENT)
    text = (
        '{"case_id":"q-001","exercises":["supervisor"]}\n'
        '{"case_id":"q-002","exercises":["supervisor","planner"]}\n'
    )
    out = sa._extend_golden_cases(text, "scorer")
    cases = [json.loads(line) for line in out.strip().splitlines()]
    assert cases[0]["exercises"] == ["supervisor", "scorer"]
    assert cases[1]["exercises"] == ["supervisor", "planner", "scorer"]


def test_extend_is_idempotent():
    sa = _load("scaffold_agent_evals", SCAFFOLD_AGENT)
    text = '{"case_id":"q-001","exercises":["supervisor","scorer"]}\n'
    out = sa._extend_golden_cases(text, "scorer")
    case = json.loads(out.strip())
    assert case["exercises"] == ["supervisor", "scorer"]


def test_extend_creates_exercises_when_missing():
    sa = _load("scaffold_agent_evals", SCAFFOLD_AGENT)
    text = '{"case_id":"q-001"}\n'
    out = sa._extend_golden_cases(text, "scorer")
    case = json.loads(out.strip())
    assert case["exercises"] == ["supervisor", "scorer"]


def test_extend_passes_through_unparseable_lines():
    sa = _load("scaffold_agent_evals", SCAFFOLD_AGENT)
    text = (
        '# comment\n'
        '{"case_id":"q-001","exercises":["supervisor"]}\n'
        '\n'
    )
    out = sa._extend_golden_cases(text, "scorer")
    lines = out.splitlines()
    assert lines[0] == "# comment"
    assert json.loads(lines[1])["exercises"] == ["supervisor", "scorer"]


def test_extend_preserves_trailing_newline():
    sa = _load("scaffold_agent_evals", SCAFFOLD_AGENT)
    with_nl = '{"case_id":"q-001","exercises":["supervisor"]}\n'
    without_nl = '{"case_id":"q-001","exercises":["supervisor"]}'
    assert _load("scaffold_agent_evals", SCAFFOLD_AGENT)._extend_golden_cases(
        with_nl, "x"
    ).endswith("\n")
    assert not sa._extend_golden_cases(without_nl, "x").endswith("\n")
