"""CRM write (side-effect). HITL-gated. Example: Salesforce/Dynamics contact upsert.

This is a STUB partners replace with their CRM. The important contract is:
- declare JSON schema in ``SCHEMA``
- call ``hitl.checkpoint`` BEFORE any network write
- emit ``tool.executed`` with success/failure
"""
from __future__ import annotations

from typing import Any

from ..accelerator_baseline.hitl import checkpoint
from ..accelerator_baseline.killswitch import assert_enabled
from ..accelerator_baseline.telemetry import Event, emit_event

TOOL_NAME = "crm_write_contact"
HITL_POLICY = "always"  # side-effect on customer system of record

SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": "Upsert a contact in the CRM. Requires human approval.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "email": {"type": "string"},
            "title": {"type": "string"},
            "source": {"type": "string",
                       "description": "How the contact was discovered"},
        },
        "required": ["account_id", "email", "last_name"],
    },
}


async def crm_write_contact(**args: Any) -> dict[str, Any]:
    assert_enabled("tools")
    await checkpoint(tool=TOOL_NAME, args=args, policy=HITL_POLICY)
    # Partner: replace with actual CRM SDK call (Salesforce, Dynamics, HubSpot).
    result = {"ok": True, "contact_id": f"stub-{args['email']}"}
    emit_event(Event(name="tool.executed", args_redacted=args,
                     external_system=TOOL_NAME, ok=True))
    return result
