"""Telemetry primitives.

Typed events emitted by every part of the accelerator. Partners add KPI-
specific events declared in ``accelerator.yaml.kpis``. Do NOT use ``print``
or ad-hoc logging for observability — route through this module so that:

1. Event schemas stay consistent and greppable across partners.
2. PII redaction happens in one place.
3. OpenTelemetry spans wrap Foundry + tool calls for App Insights correlation.
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from opentelemetry import trace

logger = logging.getLogger("accelerator.telemetry")
tracer = trace.get_tracer("accelerator")


# ---------------------------------------------------------------------------
# Event schema — extend per engagement (keep types; don't repurpose names)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Event:
    name: str
    args_redacted: Mapping[str, Any] = field(default_factory=dict)
    external_system: str | None = None
    ok: bool = True
    error: str | None = None
    # numeric payload (for duration/cost/ratio kpis)
    value: float | None = None
    unit: str | None = None


# KPI registry — supervisor/scaffold-from-brief appends entries here from
# accelerator.yaml.kpis[]. Each engagement pins its KPI events here so lint
# can verify parity between YAML and code.
KPI_EVENTS: set[str] = {
    "request.received",
    "supervisor.routed",
    "worker.completed",
    "worker.skipped",
    "tool.executed",
    "tool.hitl_approved",
    "tool.hitl_rejected",
    "aggregator.composed",
    "response.returned",
}


def emit_event(event: Event) -> None:
    """Emit a typed event to App Insights via OTel.

    Span attributes follow ``event.*`` convention for Kusto queries. In local
    development where no AppInsights exporter is configured, falls back to
    structured ``logger.info`` output.
    """
    payload = asdict(event)
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name=event.name, attributes=_otel_flatten(payload))
    if not _appinsights_configured():
        logger.info("telemetry.event", extra={"event": payload})


def _otel_flatten(payload: Mapping[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for k, v in payload.items():
        if isinstance(v, Mapping):
            for kk, vv in v.items():
                flat[f"{k}.{kk}"] = _stringify(vv)
        else:
            flat[k] = _stringify(v)
    return flat


def _stringify(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def _appinsights_configured() -> bool:
    # azure-monitor-opentelemetry honors this env var
    return bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"))
