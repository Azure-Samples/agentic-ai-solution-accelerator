"""Web search tool (read-only). Partner wires Bing Web Search / Tavily / SerpAPI.

Constrained by allow-list in ``accelerator.yaml.solution.grounding_sources``.
Content-filtered by Foundry before reaching the agent.
"""
from __future__ import annotations

from typing import Any

from ..accelerator_baseline.telemetry import Event, emit_event

TOOL_NAME = "web_search"

SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": "Search the public web for recent news about an account.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "recency_days": {"type": "integer", "default": 90},
            "top": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
}


async def web_search(**args: Any) -> dict[str, Any]:
    emit_event(Event(name="tool.executed", args_redacted={"query_len": len(args["query"])},
                     external_system=TOOL_NAME, ok=True))
    # Partner: replace with Bing Web Search via grounded retrieval.
    return {"results": []}
