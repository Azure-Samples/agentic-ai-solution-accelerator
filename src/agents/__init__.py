"""Agent registry — imports all flagship agents so the workflow can discover them.

Each agent's functional contract is anchored to an SMB Agent Hub reference so
partners see credible provenance (not fictional toy agents). The accelerator
keeps the flagship lean — 5 agents — so the *pattern* (supervisor + grounded
researcher + parallel workers + HITL + aggregator) stays obvious. Partners
extend from here by adding or swapping agents; the registry is the single
place to wire a new one in.
"""

from . import (
    account_planner,
    competitive_context,
    icp_fit_analyst,
    outreach_personalizer,
    supervisor,
)

__all__ = [
    "account_planner",
    "competitive_context",
    "icp_fit_analyst",
    "outreach_personalizer",
    "supervisor",
]
