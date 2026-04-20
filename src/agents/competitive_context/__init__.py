"""Competitive Context — competitors, differentiators, objections, talking points.

Reference: SMB Agent Hub ``compete_advisor`` + ``cloud_footprint`` (the
latter supplies the evidence model for AWS/GCP/OCI footprint signals). The
accelerator flagship uses a slimmed contract so the pattern stays clear.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-competitive-context"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
