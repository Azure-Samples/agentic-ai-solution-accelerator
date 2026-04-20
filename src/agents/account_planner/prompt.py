"""Build the user prompt for the Account Planner."""
from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    company = request["company_name"]
    domain = request.get("domain", "")
    hints = request.get("context_hints", [])
    hints_block = "\n".join(f"- {h}" for h in hints) or "(none)"
    grounding = request.get("grounding_chunks", [])
    grounding_block = "\n".join(
        f"[{c.get('id','?')}] {c.get('content','')} (source: {c.get('source','')})"
        for c in grounding
    ) or "(none — you may search the web, but every factual claim still needs a citation)"
    return (
        f"Profile the account: {company} ({domain}).\n"
        f"Seller context hints:\n{hints_block}\n\n"
        f"GROUNDING CHUNKS (from AI Search, prefer these over web):\n{grounding_block}\n\n"
        "Return a grounded profile covering: company_overview (<=4 sentences), "
        "industry, recent_news (last 90 days), strategic_initiatives, "
        "technology_landscape, buying_committee, and opportunity_signals. Every "
        "factual claim MUST carry a citation (URL + quote). Uncited claims are "
        "rejected."
    )
