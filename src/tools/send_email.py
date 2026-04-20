"""Outbound email (side-effect). HITL-gated. Partner wires Graph / SendGrid / SES."""
from __future__ import annotations

from typing import Any

from ..accelerator_baseline.hitl import checkpoint
from ..accelerator_baseline.killswitch import assert_enabled
from ..accelerator_baseline.telemetry import Event, emit_event

TOOL_NAME = "send_email"
HITL_POLICY = "always"

SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": "Send an outbound email draft. Requires human approval.",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "array", "items": {"type": "string"}},
            "subject": {"type": "string"},
            "body_markdown": {"type": "string"},
            "reply_to": {"type": "string"},
        },
        "required": ["to", "subject", "body_markdown"],
    },
}


async def send_email(**args: Any) -> dict[str, Any]:
    assert_enabled("tools")
    await checkpoint(tool=TOOL_NAME, args=args, policy=HITL_POLICY)
    # Partner: swap for Microsoft Graph sendMail.
    result = {"ok": True, "message_id": f"stub-{abs(hash(args['subject']))}"}
    emit_event(Event(name="tool.executed", args_redacted={"to_count": len(args["to"])},
                     external_system=TOOL_NAME, ok=True))
    return result
