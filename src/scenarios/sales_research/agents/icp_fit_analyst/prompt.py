from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    profile = request["account_profile"]
    icp = request["icp_definition"]
    return (
        "Score the account against our ICP and surface grounded signals.\n\n"
        "BREVITY: Concise, actionable output. <=3 items per array.\n\n"
        "Grounding rules:\n"
        "- Every fit_reason, fit_risk, and signal_evidence entry MUST be "
        "grounded in a specific fact from the account profile.\n"
        "- Never fabricate revenue, headcount, or wallet figures. Missing "
        "data goes in data_gaps.\n"
        "- nnr_indicators: strong | moderate | weak | unknown.\n"
        "- tier_recommendation: tier-1 (strategic) | tier-2 (qualify) | "
        "tier-3 (nurture) | watchlist.\n\n"
        f"ICP definition:\n{icp}\n\n"
        f"Account profile:\n{profile}\n\n"
        "Return strict JSON with: fit_score (0..100), fit_reasons (<=3, "
        "1 sentence each), fit_risks (<=3), recommended_segment, "
        "recommended_action, tier_recommendation, signal_evidence[] "
        "(<=3, {signal, source}), nnr_indicators, data_gaps[] (<=3)."
    )
