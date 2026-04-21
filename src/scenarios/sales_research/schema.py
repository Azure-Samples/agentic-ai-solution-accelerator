"""Request schema for the Sales Research & Outreach scenario.

Resolved at startup by :func:`src.workflow.registry.load_scenario` via the
``scenario.request_schema`` entry in ``accelerator.yaml``.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    company_name: str
    domain: str = ""
    seller_intent: str = Field(
        ..., description="What the seller wants from this account"
    )
    persona: str = "Decision maker"
    icp_definition: str
    our_solution: str
    context_hints: list[str] = []
