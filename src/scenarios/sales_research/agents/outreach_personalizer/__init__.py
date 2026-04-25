"""Outreach Personalizer — seller-ready email draft.

Scenario-specific side-effect worker, kept so the flagship demonstrates
a side-effect-capable output (email) gated by HITL. Partners can remove
it if their scenario doesn't need outreach.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-outreach-personalizer"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
