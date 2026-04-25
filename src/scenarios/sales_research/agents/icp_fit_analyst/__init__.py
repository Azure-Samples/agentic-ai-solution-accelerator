"""ICP Fit Analyst — scores account against seller's ICP.

Produces opportunity qualification plus a tier recommendation. Kept
lean here; partners who need richer scoring (dollar sizing, territory
logic) extend or replace this worker.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-icp-fit-analyst"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
