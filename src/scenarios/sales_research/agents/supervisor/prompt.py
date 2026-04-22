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
        "The briefing must include:\n"
        "- executive_summary (<=6 bullets)\n"
        "- account_profile: copy from account_planner output, preserving "
        "citations and all sub-fields.\n"
        "- icp_fit: copy from icp_fit_analyst output, preserving all "
        "sub-fields (fit_score, fit_reasons, fit_risks, "
        "recommended_segment, recommended_action, tier_recommendation, "
        "signal_evidence, nnr_indicators, data_gaps).\n"
        "- competitive_play: copy from competitive_context output, "
        "preserving all sub-fields (competitors with stance + evidence + "
        "evidence_urls, differentiators, likely_objections, "
        "talking_points, cloud_footprint_signals, battlecard_refs).\n"
        "- recommended_outreach: copy from outreach_personalizer output "
        "(subject, body_markdown, primary_cta, personalization_anchors).\n"
        "- next_steps: 3 concrete actions for the seller.\n"
        "- requires_approval: list of side-effect tools that need HITL "
        "sign-off (choose only from crm_write_contact, send_email).\n"
        "- tool_args: dict keyed by tool name with kwargs for each listed "
        "tool.\n\n"
        "Do NOT drop or rename fields from the worker outputs. Downstream "
        "consumers depend on the worker contracts."
    )
