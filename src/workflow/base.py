"""Structural contract every scenario workflow must satisfy.

Scenarios plug a concrete workflow into the accelerator by declaring a
``workflow_factory`` in ``accelerator.yaml`` that returns any object with an
async ``stream(request: dict) -> AsyncIterator[dict]`` method. Enforced as a
``Protocol`` so partners can implement with plain classes (no inheritance).
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class BaseWorkflow(Protocol):
    def stream(  # pragma: no cover - protocol
        self, request: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        ...
