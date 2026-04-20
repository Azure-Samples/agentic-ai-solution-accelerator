"""Supervisor prompt — plan which workers to run and synthesise final briefing.

The supervisor never calls side-effect tools directly; it calls workers.
Side-effect tools (crm_write_contact, send_email) are called from the
aggregator node, after the HITL gate.
"""
from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    return (
        "You are the supervisor of a sales-research workflow. For the given "
        "request, produce a final Account Briefing that combines the outputs "
        "of: account_researcher, icp_fit_analyst, competitive_context, "
        "outreach_personalizer.\n\n"
        f"Seller request: {request['seller_intent']}\n"
        f"Target company: {request['company_name']}\n"
        f"Persona to reach: {request.get('persona', 'unspecified')}\n\n"
        "The briefing must include: executive_summary (<=6 bullets), "
        "account_profile (cited), icp_fit (score + reasoning), "
        "competitive_play (competitors + differentiators + objections), "
        "recommended_outreach (subject, body, cta), next_steps (3 concrete "
        "actions for the seller), and a final ``requires_approval`` block "
        "listing any side-effect tools that need HITL sign-off."
    )
