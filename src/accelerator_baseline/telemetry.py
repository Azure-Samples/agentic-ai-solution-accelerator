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
    """Emit a typed event to App Insights via the OTel-wired logger.

    **Canonical query surface: the App Insights ``traces`` table.** Each event
    becomes a log record with ``message == event.name`` and flattened attributes
    available as ``customDimensions.<attr>``. Example KQL::

        traces
        | where message == "response.returned"
        | where tostring(customDimensions.ok) == "true"
        | summarize count() by bin(timestamp, 1d)

    A span event is *also* attached to the active span when one is recording, so
    distributed traces show event timeline points alongside the request span.
    The span event is **enrichment, not a separate counted item** — always
    count from ``traces``.

    Why the unconditional log: ``configure_azure_monitor(logger_name="accelerator")``
    pipes ``accelerator.*`` loggers through the Azure Monitor exporter. Relying
    on ``span.add_event`` alone silently dropped events because async streaming
    paths often had no recording parent span (no FastAPI auto-instrumentation
    or manual span scoping wrapped them).
    """
    payload = asdict(event)
    flat = _otel_flatten(payload)

    # `name` collides with stdlib ``logging.LogRecord.name``; reroute to
    # ``event_name`` so the log record fields don't blow up at emit time.
    flat.pop("name", None)
    flat["event_name"] = event.name

    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name=event.name, attributes=_otel_flatten(payload))

    # Always log — this is what makes the event visible in `traces`. The
    # ``extra`` dict becomes ``customDimensions`` in App Insights.
    logger.info(event.name, extra=flat)


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
