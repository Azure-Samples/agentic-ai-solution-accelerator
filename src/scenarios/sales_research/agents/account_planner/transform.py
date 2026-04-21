"""Normalise Foundry response into the account_profile schema."""
from __future__ import annotations

import json
from typing import Any


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    return {
        "company_overview": data.get("company_overview", ""),
        "industry": data.get("industry", ""),
        "recent_news": list(data.get("recent_news", [])),
        "strategic_initiatives": list(data.get("strategic_initiatives", [])),
        "technology_landscape": dict(data.get("technology_landscape", {})),
        "buying_committee": list(data.get("buying_committee", [])),
        "opportunity_signals": list(data.get("opportunity_signals", [])),
        "citations": list(data.get("citations", [])),
    }
