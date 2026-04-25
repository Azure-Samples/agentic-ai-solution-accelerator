"""Agent registry — imports all flagship agents so the workflow can discover them.

Worker functional contracts are documented in
``docs/agent-specs/accel-*.md``:

    account_planner       — accel-account-planner
    icp_fit_analyst       — accel-icp-fit-analyst
    competitive_context   — accel-competitive-context
    outreach_personalizer — accel-outreach-personalizer
    supervisor            — accel-sales-research-supervisor

The supervisor is the orchestration primitive (plan → delegate →
aggregate). Outreach Personalizer is a scenario-specific side-effect
worker, kept so the flagship exercises the HITL + tool-invocation
path end-to-end.

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
