from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    profile = request["account_profile"]
    our_solution = request["our_solution"]
    return (
        "Given the account profile and our solution, identify the competitive "
        "landscape at this account. Mirror the IO shape of SMB Agent Hub "
        "compete_advisor + cloud_footprint: grounded competitor posture + "
        "cloud footprint signals + battlecard references.\n\n"
        "Grounding rules:\n"
        "- Only list a competitor if you can ground it in the account "
        "profile or a verified public source returned by your grounding "
        "tool. Empty arrays are preferred over fabricated entries.\n"
        "- evidence_urls must only contain URLs that appeared verbatim in "
        "your grounding results or the account profile's citations. Never "
        "construct or guess URLs.\n"
        "- cloud_footprint_signals are directional: only list a provider "
        "when the profile or a search result explicitly mentions a workload "
        "there. No inference by product category.\n"
        "- Never speculate about competitor pricing, internal roadmaps, or "
        "contract terms.\n"
        "- battlecard_refs are the *names* of relevant Compete Advisor "
        "battlecards; never invent battlecard URLs.\n\n"
        f"Our solution: {our_solution}\n\n"
        f"Account profile:\n{profile}\n\n"
        "Return strict JSON with: competitors[] "
        "({name, stance, evidence, evidence_urls}) where stance is one of "
        "incumbent|challenger|evaluator|absent|unknown; differentiators[] "
        "(<=3); likely_objections[] (<=3); talking_points[] anchored to "
        "profile details; cloud_footprint_signals[] "
        "({provider, workload_signal, evidence, evidence_url}) where "
        "provider is one of aws|gcp|azure|oci|other; and battlecard_refs[]."
    )
