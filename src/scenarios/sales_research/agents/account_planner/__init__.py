"""Account Planner agent — grounded account research + opportunity framing.

Reference: SMB Agent Hub ``account_planner`` agent. We anchor to that
functional contract (grounded company profile, strategic initiatives,
buying-committee) so partners see a credible reference, not a toy. The
agent's runtime instructions live in Azure AI Foundry portal; this module
only shapes I/O (prompt / transform / validate).
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-account-planner"

__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
