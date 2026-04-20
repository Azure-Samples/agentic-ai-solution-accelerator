"""Kill-switch primitive.

Halts tool execution globally when the kill switch is engaged. Partners wire
this to an operational signal: feature flag, Azure App Configuration, or an
env var flipped by on-call.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("accelerator.killswitch")


class KillSwitchEngaged(Exception):
    """Raised when the global kill switch is on and a tool tries to execute."""


def assert_enabled(scope: str = "tools") -> None:
    """Assert that the scope is NOT killed. Raises KillSwitchEngaged otherwise.

    Partners can extend this with Azure App Configuration feature flags:
        FEATURE_CLIENT = AzureAppConfigurationClient(...)
        if FEATURE_CLIENT.is_enabled(f"killswitch.{scope}"): raise ...
    """
    env_key = f"KILLSWITCH_{scope.upper()}"
    if os.getenv(env_key, "").lower() in ("1", "true", "on"):
        logger.critical("Kill switch engaged: %s", env_key)
        raise KillSwitchEngaged(f"killswitch engaged: {scope}")
