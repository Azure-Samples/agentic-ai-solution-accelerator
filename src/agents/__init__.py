"""Agent registry — import all agents so the workflow can discover them."""

from . import (
    account_researcher,
    competitive_context,
    icp_fit_analyst,
    outreach_personalizer,
    supervisor,
)

__all__ = [
    "account_researcher",
    "competitive_context",
    "icp_fit_analyst",
    "outreach_personalizer",
    "supervisor",
]
