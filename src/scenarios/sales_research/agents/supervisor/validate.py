from __future__ import annotations

from typing import Any

REQUIRED = (
    "executive_summary", "account_profile", "icp_fit",
    "competitive_play", "recommended_outreach", "next_steps",
    "requires_approval", "tool_args",
)


def validate_response(response: dict[str, Any]) -> tuple[bool, str]:
    for f in REQUIRED:
        if f not in response:
            return False, f"missing field: {f}"
    if not response["executive_summary"]:
        return False, "executive_summary empty"
    if not isinstance(response["requires_approval"], list):
        return False, "requires_approval must be a list of tool names"
    if not isinstance(response["tool_args"], dict):
        return False, "tool_args must be a dict keyed by tool name"
    # Every approved tool must have args; otherwise the workflow will skip it.
    for t in response["requires_approval"]:
        if t not in response["tool_args"]:
            return False, f"requires_approval lists {t!r} but tool_args has no entry for it"
    return True, ""
