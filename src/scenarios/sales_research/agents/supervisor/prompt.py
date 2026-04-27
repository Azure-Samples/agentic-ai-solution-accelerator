from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    # The four worker outputs (account_profile, icp_fit, competitive_play,
    # recommended_outreach) are merged deterministically in code by
    # ``SalesResearchWorkflow._aggregate``. This prompt only asks the
    # supervisor for the genuinely synthesized fields, which keeps the
    # aggregation call short (~10–15s instead of ~25–35s) and removes a
    # whole class of "supervisor dropped/renamed worker fields" failures.
    return (
        "You are the supervisor of a sales-research workflow. The four "
        "worker outputs (account_profile, icp_fit, competitive_play, "
        "recommended_outreach) will be carried into the final briefing "
        "verbatim by the orchestrator — do NOT echo them back. Your job "
        "is to produce ONLY the synthesis fields below.\n\n"
        f"Seller request: {request['seller_intent']}\n"
        f"Target company: {request['company_name']}\n"
        f"Persona to reach: {request.get('persona', 'unspecified')}\n\n"
        "Produce a JSON object with exactly these keys:\n"
        "- executive_summary: EXACTLY 3 concise bullets, each ONE "
        "sentence, grounded in the worker outputs. No preamble.\n"
        "- next_steps: EXACTLY 3 prioritized actions for the seller, "
        "each ONE sentence.\n"
        "- requires_approval: list of side-effect tools that need HITL "
        "sign-off (choose only from crm_write_contact, send_email; may "
        "be empty).\n"
        "- tool_args: dict keyed by tool name with kwargs for each tool "
        "listed in requires_approval (empty dict if none).\n\n"
        "IMPORTANT: Summarize from worker outputs only. Do NOT introduce "
        "new facts. Do NOT re-analyze the raw data. Be concise.\n\n"
        "Do NOT include account_profile, icp_fit, competitive_play, or "
        "recommended_outreach in your response — the orchestrator merges "
        "them in. Output ONLY the JSON object, no commentary."
    )
