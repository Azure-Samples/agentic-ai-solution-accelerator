"""Tests for tool-trace groundedness wiring (Phase 2c.2).

Covers:
1. ``account_planner.validate_response`` rejects citations whose host
   isn't in ``_retrieved_uris`` (and accepts when it is).
2. The supervisor stamps ``_retrieved_uris`` from
   ``state.retrieved_uris`` onto the parsed dict, calls
   ``validate_response``, then pops the key so downstream consumers
   never see it.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from src.scenarios.sales_research.agents.account_planner.validate import (
    validate_response as account_planner_validate,
)
from src.workflow.supervisor import (
    SupervisorDAG,
    WorkerSpec,
    WorkerState,
)

# ---------------------------------------------------------------------------
# account_planner validator: hallucinated-URL rejection
# ---------------------------------------------------------------------------
_VALID_BASE = {
    "company_overview": "Contoso Ltd makes widgets.",
    "industry": "Manufacturing",
    "recent_news": [{"title": "Q3 earnings", "url": "https://news.example/a"}],
    "strategic_initiatives": ["AI transformation"],
    "technology_landscape": {"cloud": "Azure"},
    "buying_committee": [{"name": "J. Doe", "title": "CTO"}],
    "opportunity_signals": ["expanding cloud spend"],
}


def _resp(citations: list[dict[str, str]], retrieved: list[str] | None = None):
    """Build a parsed-response dict shaped like account_planner output."""
    out: dict[str, Any] = dict(_VALID_BASE)
    out["citations"] = citations
    if retrieved is not None:
        out["_retrieved_uris"] = retrieved
    return out


def test_account_planner_accepts_citation_in_retrieved_set():
    resp = _resp(
        citations=[{"url": "https://news.example/a", "quote": "x"}],
        retrieved=["https://news.example/a"],
    )
    ok, msg = account_planner_validate(resp)
    assert ok, msg


def test_account_planner_rejects_citation_not_in_retrieved_set():
    resp = _resp(
        citations=[{"url": "https://hallucinated.example/x", "quote": "y"}],
        retrieved=["https://news.example/a"],
    )
    ok, msg = account_planner_validate(resp)
    assert not ok
    assert "hallucinated.example" in msg


def test_account_planner_fails_open_when_retrieved_empty():
    """Empty trace must not block valid responses (unit-test stub path)."""
    resp = _resp(
        citations=[{"url": "https://anything.example/x"}],
        retrieved=[],
    )
    ok, msg = account_planner_validate(resp)
    assert ok, msg


def test_account_planner_fails_open_when_no_retrieved_key():
    """Missing key (legacy callers) must not block."""
    resp = _resp(citations=[{"url": "https://x.example"}])
    resp.pop("_retrieved_uris", None)
    ok, _ = account_planner_validate(resp)
    assert ok


def test_account_planner_accepts_citation_without_url():
    """ID-only or quote-only citations stay valid."""
    resp = _resp(
        citations=[{"id": "internal-1", "quote": "verbatim"}],
        retrieved=["https://news.example/a"],
    )
    ok, msg = account_planner_validate(resp)
    assert ok, msg


# ---------------------------------------------------------------------------
# Supervisor: stamp _retrieved_uris before validate, pop after
# ---------------------------------------------------------------------------
def _stub_module(name: str, *, captured: list[dict]) -> Any:
    """Build a stub agent module that records what validate_response saw."""
    def build_prompt(req: dict) -> str:
        return "p"

    def transform_response(raw: str) -> dict:
        return {"agent": name, "raw": raw}

    def validate_response(data: dict) -> tuple[bool, str]:
        # Snapshot what validators see -- including the private key.
        captured.append(dict(data))
        return True, ""

    return SimpleNamespace(
        AGENT_NAME=name,
        build_prompt=build_prompt,
        transform_response=transform_response,
        validate_response=validate_response,
    )


def test_supervisor_stamps_and_pops_retrieved_uris():
    captured: list[dict] = []
    mod = _stub_module("agent-a", captured=captured)

    async def invoke(agent_name: str, prompt: str, state: WorkerState) -> str:
        # Simulate _invoke_agent populating state.retrieved_uris
        state.retrieved_uris[agent_name] = [
            "https://news.example/a",
            "https://news.example/b",
        ]
        return "{}"

    spec = WorkerSpec(id="a", module=mod, build_input=lambda s: {})
    dag = SupervisorDAG({"a": spec}, invoke_agent=invoke)
    state = WorkerState(request={"q": "hi"})

    async def go():
        async for _ in dag.run(state):
            pass

    asyncio.run(go())
    # Validator saw _retrieved_uris stamped onto the dict
    assert len(captured) == 1
    assert captured[0].get("_retrieved_uris") == [
        "https://news.example/a",
        "https://news.example/b",
    ]
    # Final output (in state.outputs) must NOT carry the private key --
    # supervisor pops it after validate.
    out = state.outputs.get("a") or {}
    assert "_retrieved_uris" not in out


def test_supervisor_stamps_empty_list_when_no_uris_captured():
    """Workers that didn't call any tool still get an empty-list stamp."""
    captured: list[dict] = []
    mod = _stub_module("agent-b", captured=captured)

    async def invoke(agent_name: str, prompt: str, state: WorkerState) -> str:
        # No mutation -- simulates a worker whose tool trace was empty
        return "{}"

    spec = WorkerSpec(id="b", module=mod, build_input=lambda s: {})
    dag = SupervisorDAG({"b": spec}, invoke_agent=invoke)
    state = WorkerState(request={"q": "hi"})

    async def go():
        async for _ in dag.run(state):
            pass

    asyncio.run(go())
    assert captured[0].get("_retrieved_uris") == []


def test_supervisor_pops_retrieved_uris_even_when_validation_fails():
    """Even when validate rejects, the private key must not leak."""
    captured: list[dict] = []

    def build_prompt(req: dict) -> str:
        return "p"

    def transform_response(raw: str) -> dict:
        return {"agent": "c"}

    def validate_response(data: dict) -> tuple[bool, str]:
        captured.append(dict(data))
        return False, "nope"

    mod = SimpleNamespace(
        AGENT_NAME="agent-c",
        build_prompt=build_prompt,
        transform_response=transform_response,
        validate_response=validate_response,
    )

    async def invoke(agent_name: str, prompt: str, state: WorkerState) -> str:
        state.retrieved_uris[agent_name] = ["https://x.example"]
        return "{}"

    spec = WorkerSpec(
        id="c", module=mod, build_input=lambda s: {},
        validation_max_attempts=2,
    )
    dag = SupervisorDAG({"c": spec}, invoke_agent=invoke)
    state = WorkerState(request={"q": "hi"})

    async def go():
        with pytest.raises(Exception):  # noqa: B017,PT011
            async for _ in dag.run(state):
                pass

    asyncio.run(go())
    # Each retry must see the stamped key (proves stamping happens
    # inside the attempt loop, not just once).
    assert len(captured) == 2
    for snap in captured:
        assert snap.get("_retrieved_uris") == ["https://x.example"]
