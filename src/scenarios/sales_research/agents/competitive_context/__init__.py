"""Competitive Context — competitors, differentiators, objections, talking points.

Produces grounded competitor posture plus directional cloud-footprint
signals (AWS / GCP / OCI / Azure / other). The accelerator flagship
uses a slimmed contract so the pattern stays clear.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-competitive-context"
__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
