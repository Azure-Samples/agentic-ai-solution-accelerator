"""Validate the Account Researcher response shape + groundedness constraint."""
from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = (
    "company_overview", "industry", "recent_news",
    "strategic_initiatives", "buying_committee", "citations",
)

FORBIDDEN_FIELDS = ("icp_fit_score", "competitors", "outreach_subject")


def validate_response(response: dict[str, Any]) -> tuple[bool, str]:
    for f in REQUIRED_FIELDS:
        if f not in response:
            return False, f"missing field: {f}"
    for f in FORBIDDEN_FIELDS:
        if f in response:
            return False, f"cross-agent contamination: {f} belongs to another agent"
    if not response["citations"] and response["recent_news"]:
        return False, "recent_news present without citations (groundedness violation)"
    return True, ""
