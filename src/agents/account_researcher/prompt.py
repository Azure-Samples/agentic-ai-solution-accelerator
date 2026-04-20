"""Build the user prompt for the Account Researcher."""
from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    company = request["company_name"]
    domain = request.get("domain", "")
    hints = request.get("context_hints", [])
    hints_block = "\n".join(f"- {h}" for h in hints) or "(none)"
    return (
        f"Profile the account: {company} ({domain}).\n"
        f"Context hints from the seller:\n{hints_block}\n\n"
        "Return a structured profile covering: company overview, industry, "
        "recent news (last 90 days), strategic initiatives, and likely buying "
        "committee roles. Cite every factual claim with a source URL from your "
        "grounded retrieval — no ungrounded assertions."
    )
