from __future__ import annotations

from typing import Any

REQUIRED = ("competitors", "differentiators", "likely_objections", "talking_points")
FORBIDDEN = ("fit_score", "outreach_subject", "company_overview")


def validate_response(response: dict[str, Any]) -> tuple[bool, str]:
    for f in REQUIRED:
        if f not in response:
            return False, f"missing field: {f}"
    for f in FORBIDDEN:
        if f in response:
            return False, f"cross-agent contamination: {f}"
    for c in response["competitors"]:
        if not isinstance(c, dict) or "name" not in c:
            return False, "each competitor must be {name, evidence}"
    return True, ""
