from __future__ import annotations

import json
from typing import Any


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    return {
        "executive_summary": list(data.get("executive_summary", []))[:6],
        "account_profile": data.get("account_profile", {}),
        "icp_fit": data.get("icp_fit", {}),
        "competitive_play": data.get("competitive_play", {}),
        "recommended_outreach": data.get("recommended_outreach", {}),
        "next_steps": list(data.get("next_steps", []))[:3],
        "requires_approval": list(data.get("requires_approval", [])),
        # Map of tool_name -> kwargs. The workflow reads this to call
        # side-effect tools; without it the run short-circuits gracefully.
        "tool_args": dict(data.get("tool_args", {})),
    }
