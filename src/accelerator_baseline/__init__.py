"""Partner-owned accelerator primitives.

These modules ship inline with the template — NOT as an external pip package.
Partners own this code, extend it freely, and never suffer a dependency pin
drift. Consistency is maintained by CI lint (``scripts/accelerator-lint.py``)
verifying shape, not by a separate package release.
"""

from .cost import UsageSample, estimate_call_cost, record_call_cost
from .evals import Acceptance, EvalResult, evaluate_acceptance
from .hitl import HITLDenied, HITLMisconfigured, checkpoint
from .killswitch import KillSwitchEngaged, assert_enabled
from .telemetry import KPI_EVENTS, Event, emit_event

__all__ = [
    "Acceptance",
    "Event",
    "EvalResult",
    "HITLDenied",
    "HITLMisconfigured",
    "KPI_EVENTS",
    "KillSwitchEngaged",
    "UsageSample",
    "assert_enabled",
    "checkpoint",
    "emit_event",
    "estimate_call_cost",
    "evaluate_acceptance",
    "record_call_cost",
]
