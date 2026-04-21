"""Workflow framework — scenario-agnostic plumbing.

Concrete scenario workflows live under ``src.scenarios.*.workflow`` and are
resolved at startup by :func:`src.workflow.registry.load_scenario`.
"""
from .base import BaseWorkflow
from .registry import (
    ScenarioAgent,
    ScenarioBundle,
    ScenarioContext,
    ScenarioIndex,
    load_scenario,
    read_scenario_raw,
)

__all__ = [
    "BaseWorkflow",
    "ScenarioAgent",
    "ScenarioBundle",
    "ScenarioContext",
    "ScenarioIndex",
    "load_scenario",
    "read_scenario_raw",
]
