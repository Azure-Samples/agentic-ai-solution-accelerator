"""ICP Fit Analyst — scores account against seller's ICP.

Reference: SMB Agent Hub ``nnr_agent`` + ``portfolio_planner`` (opportunity
qualification + tiering logic). Kept lean here; the full Agent Hub NNR
sizing model is out of scope for the flagship.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-icp-fit-analyst"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
