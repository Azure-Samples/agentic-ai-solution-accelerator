"""Supervisor — plans workers, then synthesises final briefing.

Implements the supervisor-routing pattern (plan → delegate → aggregate)
that drives the four workers below. Side-effect tools are gated by
HITL; the supervisor never calls them directly.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-sales-research-supervisor"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
