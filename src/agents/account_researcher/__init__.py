"""Account Researcher agent — 3-layer pattern.

prompt.py   → build_prompt(request)
transform.py → transform_response(raw)
validate.py → validate_response(response)

The agent's system instructions live in Azure AI Foundry portal. This module
only builds the *user* prompt + normalises/validates the response.
"""
from .prompt import build_prompt
from .transform import transform_response
from .validate import validate_response

AGENT_NAME = "accel-account-researcher"

__all__ = ["AGENT_NAME", "build_prompt", "transform_response", "validate_response"]
