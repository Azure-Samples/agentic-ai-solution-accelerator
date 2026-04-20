from __future__ import annotations

from typing import Any

REQUIRED = (
    "executive_summary", "account_profile", "icp_fit",
    "competitive_play", "recommended_outreach", "next_steps",
    "requires_approval",
)


def validate_response(response: dict[str, Any]) -> tuple[bool, str]:
    for f in REQUIRED:
        if f not in response:
            return False, f"missing field: {f}"
    if not response["executive_summary"]:
        return False, "executive_summary empty"
    if not isinstance(response["requires_approval"], list):
        return False, "requires_approval must be a list of tool names"
    return True, ""
