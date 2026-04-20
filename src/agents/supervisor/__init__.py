"""Supervisor — plans workers, then synthesises final briefing.

Reference: SMB Agent Hub ``supervisor`` agent (supervisor-routing pattern).
Same contract: plan → delegate → aggregate. Side-effect tools are gated
by HITL, not called directly by the supervisor.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-sales-research-supervisor"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
