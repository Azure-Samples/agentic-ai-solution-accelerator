from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    profile = request["account_profile"]
    icp = request["icp_definition"]
    return (
        "Score the account against our Ideal Customer Profile.\n\n"
        f"ICP definition:\n{icp}\n\n"
        f"Account profile:\n{profile}\n\n"
        "Return: fit_score (0..100), top 3 fit_reasons, top 3 fit_risks, "
        "recommended_segment (enterprise|mid-market|smb), and a "
        "recommended_action (pursue|nurture|disqualify)."
    )
