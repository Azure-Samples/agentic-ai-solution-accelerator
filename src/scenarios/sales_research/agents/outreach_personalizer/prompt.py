from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    return (
        "Draft a concise, highly-personalised outreach email for this account. "
        "The email MUST reference: (a) one specific strategic initiative from the "
        "profile, (b) one differentiator, (c) one clear call-to-action. "
        "Tone: direct, respectful, zero marketing jargon. Length: <= 120 words.\n\n"
        f"Account profile: {request['account_profile']}\n"
        f"ICP fit summary: {request['fit_summary']}\n"
        f"Competitive context: {request['competitive_context']}\n"
        f"Persona: {request['persona']}\n\n"
        "Return: subject, body_markdown, primary_cta, personalization_anchors[]."
    )
