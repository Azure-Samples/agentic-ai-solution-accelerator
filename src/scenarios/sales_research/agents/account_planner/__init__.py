"""Account Planner agent — grounded account research + opportunity framing.

Produces a grounded company profile, strategic initiatives, and
buying-committee details with citations. The agent's runtime
instructions live in Microsoft Foundry portal; this module only shapes
I/O (prompt / transform / validate).
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-account-planner"

__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
