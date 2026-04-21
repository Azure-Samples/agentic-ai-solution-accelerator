"""Agent registry — imports all flagship agents so the workflow can discover them.

Worker functional contracts are anchored to SMB Agent Hub agents from the
partner's reference set — only those actually used by this flagship:

    account_planner       ← Agent Hub account_planner
    icp_fit_analyst       ← Agent Hub nnr_agent + portfolio_planner
    competitive_context   ← Agent Hub compete_advisor + cloud_footprint

Supervisor is the orchestration primitive (pattern, not a specific Agent
Hub worker). Outreach Personalizer has no direct analog in the cited set
and is kept as a scenario-specific side-effect worker so the flagship can
exercise the HITL + tool-invocation path end-to-end.

The flagship stays lean (5 agents) so the *pattern* — supervisor +
grounded retrieval + parallel workers + HITL + aggregator — is obvious.
Partners extend from here by adding or swapping agents; this registry is
the single place to wire a new one in.
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
