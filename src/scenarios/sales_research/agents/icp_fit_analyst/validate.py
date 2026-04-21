from __future__ import annotations

from typing import Any

REQUIRED = ("fit_score", "fit_reasons", "fit_risks",
            "recommended_segment", "recommended_action")
FORBIDDEN = ("company_overview", "competitors", "outreach_subject")
VALID_SEGMENTS = {"enterprise", "mid-market", "smb", "unknown"}
VALID_ACTIONS = {"pursue", "nurture", "disqualify"}


def validate_response(response: dict[str, Any]) -> tuple[bool, str]:
    for f in REQUIRED:
        if f not in response:
            return False, f"missing field: {f}"
    for f in FORBIDDEN:
        if f in response:
            return False, f"cross-agent contamination: {f}"
    if not (0 <= response["fit_score"] <= 100):
        return False, "fit_score must be in [0,100]"
    if response["recommended_segment"] not in VALID_SEGMENTS:
        return False, f"invalid segment: {response['recommended_segment']}"
    if response["recommended_action"] not in VALID_ACTIONS:
        return False, f"invalid action: {response['recommended_action']}"
    return True, ""
