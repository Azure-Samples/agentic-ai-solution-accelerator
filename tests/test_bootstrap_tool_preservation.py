"""Tests for bootstrap's tool preservation + skip-create-version helpers.

The pure helpers exist so partners attaching catalog tools in the Foundry
portal don't get them silently nuked on every ``azd deploy``. These tests
guard the contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.bootstrap import (
    _agent_definition_unchanged,
    _kb_tool_present,
    _merge_preserved_tools,
    _tool_fingerprint,
)


# ---------------------------------------------------------------------------
# Tool stubs that quack like the Foundry SDK objects ``_tool_fingerprint``
# pattern-matches against.
# ---------------------------------------------------------------------------
@dataclass
class _McpTool:
    server_label: str
    project_connection_id: str
    type: str = "mcp"


@dataclass
class _DefStub:
    tools: list[Any]


def _kb(label: str = "accel-kb", conn: str = "conn-1") -> _McpTool:
    return _McpTool(server_label=label, project_connection_id=conn)


def _catalog(label: str, conn: str = "conn-cat") -> _McpTool:
    return _McpTool(server_label=label, project_connection_id=conn)


# ---------------------------------------------------------------------------
# _agent_definition_unchanged
# ---------------------------------------------------------------------------
def test_definition_unchanged_when_model_and_instr_match():
    assert _agent_definition_unchanged("gpt-5", "do x", "gpt-5", "do x") is True


def test_definition_changed_when_model_differs():
    assert _agent_definition_unchanged("gpt-4", "do x", "gpt-5", "do x") is False


def test_definition_changed_when_instructions_differ():
    assert _agent_definition_unchanged("gpt-5", "do x", "gpt-5", "do y") is False


def test_definition_changed_when_either_side_is_none():
    # New agent path: cur_model / cur_instr come back as None
    assert _agent_definition_unchanged(None, None, "gpt-5", "do x") is False


def test_definition_ignores_tool_changes():
    """Tools differing must NOT cause skip=False; that's the whole fix."""
    # Same model + instructions; helper has no opinion on tools (they're
    # merged separately in _merge_preserved_tools).
    assert _agent_definition_unchanged("gpt-5", "do x", "gpt-5", "do x") is True


# ---------------------------------------------------------------------------
# _merge_preserved_tools
# ---------------------------------------------------------------------------
def test_merge_with_no_existing_tools_appends_managed():
    kb = _kb()
    merged = _merge_preserved_tools([], kb)
    assert merged == [kb]


def test_merge_with_no_existing_and_no_managed_returns_none():
    assert _merge_preserved_tools([], None) is None
    assert _merge_preserved_tools(None, None) is None


def test_merge_preserves_partner_attached_catalog_tools():
    """The whole point: catalog tools survive the merge."""
    kb = _kb()
    catalog_a = _catalog("servicenow")
    catalog_b = _catalog("confluence")
    merged = _merge_preserved_tools([catalog_a, catalog_b], kb)
    assert merged is not None
    assert catalog_a in merged
    assert catalog_b in merged
    assert kb in merged
    # KB appended last, catalog tools come first in their original order
    assert merged.index(catalog_a) < merged.index(catalog_b) < merged.index(kb)


def test_merge_dedups_existing_managed_kb_tool():
    """A previous bootstrap version's KB tool gets refreshed, not duplicated."""
    old_kb = _kb()
    new_kb = _kb()
    catalog = _catalog("github")
    merged = _merge_preserved_tools([old_kb, catalog], new_kb)
    assert merged is not None
    # Only one KB tool in the result, and it must be the fresh instance
    # (identity check — the dataclasses compare equal by value).
    kb_fp = _tool_fingerprint(new_kb)
    kb_matches = [t for t in merged if _tool_fingerprint(t) == kb_fp]
    assert len(kb_matches) == 1
    assert kb_matches[0] is new_kb
    assert catalog in merged  # partner tool preserved


def test_merge_no_managed_passes_existing_through():
    """retrieval.mode=none: bootstrap doesn't manage a tool; preserve all."""
    catalog = _catalog("graph")
    merged = _merge_preserved_tools([catalog], None)
    assert merged == [catalog]


def test_merge_distinguishes_kb_from_catalog_with_same_label():
    """KB and a catalog tool with the same label but different connection
    must not be confused — fingerprint includes project_connection_id."""
    kb = _kb(label="search", conn="kb-conn")
    catalog = _catalog(label="search", conn="catalog-conn")
    merged = _merge_preserved_tools([catalog], kb)
    assert merged is not None
    assert kb in merged
    assert catalog in merged  # different conn id → different fingerprint → preserved


# ---------------------------------------------------------------------------
# _kb_tool_present
# ---------------------------------------------------------------------------
def test_kb_present_in_single_tool_definition():
    kb = _kb()
    fp = _tool_fingerprint(kb)
    assert _kb_tool_present(_DefStub(tools=[kb]), fp) is True


def test_kb_present_alongside_catalog_tools():
    kb = _kb()
    fp = _tool_fingerprint(kb)
    defn = _DefStub(tools=[_catalog("servicenow"), kb, _catalog("github")])
    assert _kb_tool_present(defn, fp) is True


def test_kb_not_present_when_only_catalog_tools():
    kb = _kb()
    fp = _tool_fingerprint(kb)
    defn = _DefStub(tools=[_catalog("servicenow")])
    assert _kb_tool_present(defn, fp) is False


def test_kb_not_present_with_empty_definition():
    kb = _kb()
    fp = _tool_fingerprint(kb)
    assert _kb_tool_present(None, fp) is False
    assert _kb_tool_present(_DefStub(tools=[]), fp) is False


def test_kb_not_present_with_empty_fingerprint():
    """Defensive: empty desired fingerprint shouldn't accidentally match."""
    defn = _DefStub(tools=[_kb()])
    assert _kb_tool_present(defn, ()) is False
