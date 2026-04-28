"""Unit tests for :mod:`src.accelerator_baseline.telemetry`.

These tests pin the contract that ``emit_event`` ALWAYS emits a log record
through the ``accelerator`` logger, regardless of whether App Insights is
configured or whether a recording OTel parent span exists. That contract is
what makes Lab 3 (App Insights ``traces`` query) work — earlier behaviour
silently dropped events when both ``APPLICATIONINSIGHTS_CONNECTION_STRING``
was set AND no FastAPI auto-instrumented span was active.
"""
from __future__ import annotations

import logging

import pytest

from src.accelerator_baseline.telemetry import Event, emit_event


def test_emit_event_always_logs_when_appinsights_configured(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Even with the AppInsights env var set, ``emit_event`` must still log.

    Regression for the silent-drop bug — before the fix, the logger fallback
    was gated behind ``if not _appinsights_configured()`` and events
    disappeared in production.
    """
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000",
    )
    caplog.set_level(logging.INFO, logger="accelerator.telemetry")

    emit_event(Event(name="response.returned", ok=True))

    matching = [r for r in caplog.records if r.message == "response.returned"]
    assert matching, "emit_event must log even when AppInsights is configured"


def test_emit_event_does_not_collide_with_logrecord_reserved_keys(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``Event.name`` cannot land in ``LogRecord.extra`` as ``name=`` — it's
    reserved by stdlib ``logging``. Must be remapped to ``event_name`` so
    ``logger.info(..., extra=...)`` doesn't raise ``KeyError``.
    """
    caplog.set_level(logging.INFO, logger="accelerator.telemetry")

    # If the rename ever regresses, this call raises before we get to the
    # assertion — that's the test failure signal.
    emit_event(Event(name="supervisor.routed", external_system="planner"))

    record = next(r for r in caplog.records if r.message == "supervisor.routed")
    # The record's `name` is the LOGGER name, not the event name.
    assert record.name == "accelerator.telemetry"
    # The event name is preserved under the renamed attribute.
    assert getattr(record, "event_name", None) == "supervisor.routed"


def test_emit_event_flattens_attributes_for_querying(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Event payload fields must appear as flat attributes on the LogRecord
    so they show up as top-level keys in App Insights ``customDimensions``
    (queryable as e.g. ``tostring(customDimensions.ok) == 'false'``).
    """
    caplog.set_level(logging.INFO, logger="accelerator.telemetry")

    emit_event(
        Event(
            name="tool.hitl_rejected",
            external_system="crm_write_contact",
            ok=False,
            error="reviewer_denied",
            args_redacted={"to_count": 1},
        )
    )

    record = next(
        r for r in caplog.records if r.message == "tool.hitl_rejected"
    )
    assert record.ok is False
    assert record.error == "reviewer_denied"
    assert record.external_system == "crm_write_contact"
    # Nested mapping is flattened into dotted keys.
    assert getattr(record, "args_redacted.to_count") == 1
