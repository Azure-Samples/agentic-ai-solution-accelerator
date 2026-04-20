from __future__ import annotations

from typing import Any


def build_prompt(request: dict[str, Any]) -> str:
    profile = request["account_profile"]
    our_solution = request["our_solution"]
    return (
        "Given the account profile and our solution, identify the most likely "
        "competitors already in-play at this account, our differentiators, and "
        "objections we should prepare for.\n\n"
        f"Our solution: {our_solution}\n\n"
        f"Account profile:\n{profile}\n\n"
        "Return: competitors[] (name, evidence), differentiators[] (3 max), "
        "likely_objections[] (3 max), and talking_points[] grounded in the profile."
    )
