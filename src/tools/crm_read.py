"""Read-only CRM lookup. No HITL required (idempotent, read-only)."""
from __future__ import annotations

from typing import Any

from ..accelerator_baseline.telemetry import Event, emit_event

TOOL_NAME = "crm_read_account"

SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": "Look up an account + its open opportunities in the CRM.",
    "parameters": {
        "type": "object",
        "properties": {"account_id": {"type": "string"}},
        "required": ["account_id"],
    },
}


async def crm_read_account(**args: Any) -> dict[str, Any]:
    # Partner: replace with real SDK query.
    emit_event(Event(name="tool.executed", args_redacted=args,
                     external_system=TOOL_NAME, ok=True))
    return {
        "account_id": args["account_id"],
        "industry": "unknown",
        "revenue_band": "unknown",
        "open_opportunities": [],
    }
