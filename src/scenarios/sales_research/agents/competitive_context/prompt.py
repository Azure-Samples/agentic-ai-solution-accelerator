from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    profile = request["account_profile"]
    our_solution = request["our_solution"]
    return (
        "Given the account profile and our solution, identify the competitive "
        "landscape at this account.\n\n"
        "BREVITY: Output concise, actionable intel. <=3 items per array.\n\n"
        "Grounding rules:\n"
        "- Only list a competitor if grounded in the account profile or a "
        "verified public source. Empty arrays > fabricated entries.\n"
        "- evidence_urls: only URLs that appeared verbatim in grounding results. "
        "Never construct or guess URLs.\n"
        "- cloud_footprint_signals: only list a provider when explicitly "
        "mentioned. No inference by product category.\n"
        "- Never speculate about competitor pricing, roadmaps, or contracts.\n\n"
        f"Our solution: {our_solution}\n\n"
        f"Account profile:\n{profile}\n\n"
        "Return strict JSON with: competitors[] (<=3, "
        "{name, stance, evidence (1 sentence), evidence_urls}); "
        "differentiators[] (<=3, 1 sentence each); "
        "likely_objections[] (<=3); talking_points[] (<=3, anchored to profile); "
        "cloud_footprint_signals[] (<=3); competitor_refs[] (<=3)."
    )
