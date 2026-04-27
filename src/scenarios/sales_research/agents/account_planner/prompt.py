"""Build the user prompt for the Account Planner."""
from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    company = request["company_name"]
    domain = request.get("domain", "")
    hints = request.get("context_hints", [])
    hints_block = "\n".join(f"- {h}" for h in hints) or "(none)"
    return (
        f"Profile the account: {company} ({domain}).\n"
        f"Seller context hints:\n{hints_block}\n\n"
        "RETRIEVAL: You have an Azure AI Search knowledge tool attached to "
        "this agent (FoundryIQ over the `accounts` index). Call it for any "
        "facts about this account — company overview, news, technology, "
        "leadership, financials. Prefer tool-grounded facts over open web; "
        "every factual claim MUST carry a citation (URL or document id from "
        "the tool result + a short quote). Uncited claims are rejected.\n\n"
        "Return a grounded profile covering: company_overview (<=4 "
        "sentences), industry, recent_news (last 90 days), "
        "strategic_initiatives, technology_landscape, buying_committee, and "
        "opportunity_signals."
    )
