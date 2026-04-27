from __future__ import annotations

import json
from typing import Any


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    # Supervisor now produces only synthesis fields. Pass-through fields
    # (account_profile, icp_fit, competitive_play, recommended_outreach)
    # are merged in by ``SalesResearchWorkflow._aggregate`` from the
    # worker outputs directly — see the comment in supervisor/prompt.py.
    data = json.loads(raw) if isinstance(raw, str) else raw
    return {
        "executive_summary": list(data.get("executive_summary", []))[:6],
        "next_steps": list(data.get("next_steps", []))[:3],
        "requires_approval": list(data.get("requires_approval", [])),
        # Map of tool_name -> kwargs. The workflow reads this to call
        # side-effect tools; without it the run short-circuits gracefully.
        "tool_args": dict(data.get("tool_args", {})),
    }
