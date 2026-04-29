"""Validate the Account Researcher response shape + groundedness constraint."""
from __future__ import annotations

from typing import Any

from src.accelerator_baseline.citations import (
    assert_no_hallucinated_urls,
    require_citations,
)

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
    # Foundry tool-trace groundedness: when the supervisor stamps
    # ``_retrieved_uris`` onto the response (populated by
    # ``_invoke_agent`` from the Foundry citation annotations), reject
    # any cited URL whose host wasn't actually retrieved. Fails open on
    # empty trace -- unit-test stubs and ungrounded scenarios don't
    # break.
    retrieved = response.get("_retrieved_uris", []) or []
    citations = response.get("citations") or []
    if isinstance(citations, list):
        ok, msg = assert_no_hallucinated_urls(citations, retrieved)
        if not ok:
            return False, msg
    return True, ""
