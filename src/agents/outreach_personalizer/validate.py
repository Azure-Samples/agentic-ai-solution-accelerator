from __future__ import annotations

from typing import Any

REQUIRED = ("subject", "body_markdown", "primary_cta", "personalization_anchors")
FORBIDDEN = ("fit_score", "competitors", "company_overview")
MAX_WORDS = 150


def validate_response(response: dict[str, Any]) -> tuple[bool, str]:
    for f in REQUIRED:
        if f not in response:
            return False, f"missing field: {f}"
    for f in FORBIDDEN:
        if f in response:
            return False, f"cross-agent contamination: {f}"
    if not response["subject"]:
        return False, "empty subject"
    words = len(response["body_markdown"].split())
    if words > MAX_WORDS:
        return False, f"body too long: {words} words > {MAX_WORDS}"
    if len(response["personalization_anchors"]) < 2:
        return False, "need >= 2 personalization anchors"
    return True, ""
