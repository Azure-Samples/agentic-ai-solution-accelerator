"""Validate the Account Researcher response shape + groundedness constraint."""
from __future__ import annotations

from typing import Any

from src.accelerator_baseline.citations import require_citations

REQUIRED_FIELDS = (
    "company_overview", "industry", "recent_news",
    "strategic_initiatives", "technology_landscape",
    "buying_committee", "opportunity_signals", "citations",
)

FORBIDDEN_FIELDS = (
    "fit_score", "maturity_level", "aws_intensity",
    "nnr_opportunities", "outreach_subject",
)


def validate_response(response: dict[str, Any]) -> tuple[bool, str]:
    for f in REQUIRED_FIELDS:
        if f not in response:
            return False, f"missing field: {f}"
    for f in FORBIDDEN_FIELDS:
        if f in response:
            return False, f"cross-agent contamination: {f} belongs to another agent"
    ok, msg = require_citations(response, when_fields_present=("recent_news",))
    if not ok:
        return False, msg
    return True, ""
