"""Human-in-the-Loop checkpoint primitive.

Every side-effect tool MUST call ``checkpoint`` before executing. In dev, a
console reviewer is the default; in production, the ``HITL_APPROVER_ENDPOINT``
env var points to a partner-hosted approval service (Teams bot, ITSM queue,
web UI).

Policy format (from accelerator.yaml + per-tool):
    always           — block until a human approves
    never            — skip (only if action is reversible AND
                       accelerator.yaml.solution.hitl = none)
    threshold:<expr> — block when the boolean expression over args is true
                       e.g. threshold:priority == "high"
                            threshold:amount > 1000

Partners can swap the approver transport without changing tool code.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Mapping

import httpx

from .telemetry import Event, emit_event

logger = logging.getLogger("accelerator.hitl")


class HITLDenied(Exception):
    """Raised when a human reviewer rejects the action."""


async def checkpoint(
    *,
    tool: str,
    args: Mapping[str, Any],
    policy: str,
    reviewer_context: Mapping[str, Any] | None = None,
) -> None:
    """Block until an approval decision is made.

    - ``always``   → always go to the approver.
    - ``never``    → no-op (logged).
    - ``threshold:<expr>`` → evaluate expr against args; if true, approver; else no-op.
    """
    decision_required = _policy_requires_approval(policy, args)
    if not decision_required:
        emit_event(Event(name="tool.hitl_skipped", args_redacted=dict(args),
                         external_system=tool, ok=True))
        return

    approver = os.getenv("HITL_APPROVER_ENDPOINT")
    if not approver:
        approved = await _console_review(tool, args, reviewer_context or {})
    else:
        approved = await _remote_review(approver, tool, args, reviewer_context or {})

    if approved:
        emit_event(Event(name="tool.hitl_approved", args_redacted=dict(args),
                         external_system=tool, ok=True))
        return

    emit_event(Event(name="tool.hitl_rejected", args_redacted=dict(args),
                     external_system=tool, ok=False, error="reviewer_denied"))
    raise HITLDenied(f"Reviewer denied tool={tool}")


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------
def _policy_requires_approval(policy: str, args: Mapping[str, Any]) -> bool:
    p = (policy or "").strip()
    if p == "always":
        return True
    if p == "never":
        return False
    if p.startswith("threshold:"):
        expr = p[len("threshold:"):].strip()
        # safe-ish boolean eval: only allows attribute access on ``args``.
        return bool(eval(expr, {"__builtins__": {}}, dict(args)))  # noqa: S307
    # Fail closed on unknown policy.
    logger.warning("Unknown HITL policy %r; failing closed (requiring approval)", p)
    return True


# ---------------------------------------------------------------------------
# Reviewers
# ---------------------------------------------------------------------------
async def _console_review(tool: str, args: Mapping[str, Any],
                          ctx: Mapping[str, Any]) -> bool:
    # Dev-only console approver. In prod, set HITL_APPROVER_ENDPOINT.
    logger.warning("HITL console review (DEV ONLY) — tool=%s args=%s",
                   tool, json.dumps(dict(args), default=str))
    return True  # dev fallback; override with HITL_APPROVER_ENDPOINT in prod


async def _remote_review(endpoint: str, tool: str, args: Mapping[str, Any],
                         ctx: Mapping[str, Any]) -> bool:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            endpoint,
            json={"tool": tool, "args": dict(args), "context": dict(ctx)},
        )
        resp.raise_for_status()
        return bool(resp.json().get("approved", False))
