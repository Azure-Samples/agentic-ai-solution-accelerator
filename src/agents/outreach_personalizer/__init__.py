"""Outreach Personalizer — seller-ready email draft.

Reference: loose equivalent of SMB Agent Hub ``content_curator`` personalization
output, scoped down to a single email per briefing.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-outreach-personalizer"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
