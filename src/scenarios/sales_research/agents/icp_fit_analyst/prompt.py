from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    profile = request["account_profile"]
    icp = request["icp_definition"]
    return (
        "Score the account against our Ideal Customer Profile and surface "
        "the grounded signals behind your judgment. Produce: fit + tier + "
        "grounded signal evidence + data gaps.\n\n"
        "Grounding rules:\n"
        "- Every fit_reason, fit_risk, and signal_evidence entry MUST be "
        "grounded in a specific fact from the account profile. Cite the "
        "profile field name or citation URL in signal_evidence[].source.\n"
        "- Never fabricate revenue, headcount, or wallet figures. If a "
        "signal needed to judge fit is missing, list it in data_gaps.\n"
        "- nnr_indicators are directional proxies, not numbers. Each is "
        "one of: strong | moderate | weak | unknown.\n"
        "- tier_recommendation: tier-1 (strategic pursue), tier-2 "
        "(active qualify), tier-3 (nurture cadence), watchlist "
        "(monitor only).\n\n"
        f"ICP definition:\n{icp}\n\n"
        f"Account profile:\n{profile}\n\n"
        "Return strict JSON with: fit_score (0..100), fit_reasons (<=3), "
        "fit_risks (<=3), recommended_segment "
        "(enterprise|mid-market|smb|unknown), recommended_action "
        "(pursue|nurture|disqualify), tier_recommendation "
        "(tier-1|tier-2|tier-3|watchlist), signal_evidence[] "
        "({signal, source}), nnr_indicators "
        "({size_signal, growth_signal, wallet_expansion_signal}), and "
        "data_gaps[]."
    )
