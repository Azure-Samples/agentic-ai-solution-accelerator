"""Verify the catalog-tool-hitl warning lint rule."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINT_PATH = ROOT / "scripts" / "accelerator-lint.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("acc_lint_catalog", LINT_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    sys.modules["acc_lint_catalog"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_manifest(tmp_path: pathlib.Path, agents_yaml: str) -> None:
    """Write a minimal accelerator.yaml + empty src/tools/ + scenario stub."""
    manifest = textwrap.dedent(f"""
        schema_version: "1.0"
        scenario:
          id: x
          agents:
        {agents_yaml}
    """).lstrip("\n")
    (tmp_path / "accelerator.yaml").write_text(manifest, encoding="utf-8")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "tools").mkdir(exist_ok=True)


def _run_rule(tmp_path: pathlib.Path, monkeypatch):
    lint = _load_lint()
    monkeypatch.setattr(lint, "ROOT", tmp_path)
    return lint.catalog_tool_hitl(lint.Ctx())


def test_read_shaped_catalog_tool_emits_no_warning(tmp_path, monkeypatch):
    _make_manifest(tmp_path, """
            - id: searcher
              foundry_name: x
              catalog_tools:
                - servicenow_get_incident
                - confluence_search_pages
    """)
    findings = _run_rule(tmp_path, monkeypatch)
    assert findings == []


def test_side_effect_catalog_tool_without_in_process_wrapper_warns(tmp_path, monkeypatch):
    _make_manifest(tmp_path, """
            - id: ticketer
              foundry_name: x
              catalog_tools:
                - servicenow_create_incident
    """)
    findings = _run_rule(tmp_path, monkeypatch)
    assert len(findings) == 1
    assert findings[0].rule == "catalog-tool-hitl"
    assert findings[0].severity == "warn"
    assert "servicenow_create_incident" in findings[0].message


def test_side_effect_catalog_tool_with_matching_in_process_tool_does_not_warn(
    tmp_path, monkeypatch
):
    _make_manifest(tmp_path, """
            - id: ticketer
              foundry_name: x
              catalog_tools:
                - servicenow_create_incident
    """)
    (tmp_path / "src" / "tools" / "servicenow_create_incident.py").write_text(
        "HITL_POLICY = 'required'\n", encoding="utf-8"
    )
    findings = _run_rule(tmp_path, monkeypatch)
    assert findings == []


def test_missing_manifest_emits_no_findings(tmp_path, monkeypatch):
    findings = _run_rule(tmp_path, monkeypatch)
    assert findings == []


def test_multiple_side_effect_keywords_detected(tmp_path, monkeypatch):
    _make_manifest(tmp_path, """
            - id: writer
              foundry_name: x
              catalog_tools:
                - jira_update_issue
                - github_open_issue
                - mailgun_send_email
                - drive_delete_file
    """)
    findings = _run_rule(tmp_path, monkeypatch)
    assert len(findings) == 4


def test_non_list_catalog_tools_is_skipped(tmp_path, monkeypatch):
    _make_manifest(tmp_path, """
            - id: x
              foundry_name: x
              catalog_tools: "not_a_list"
    """)
    findings = _run_rule(tmp_path, monkeypatch)
    assert findings == []
