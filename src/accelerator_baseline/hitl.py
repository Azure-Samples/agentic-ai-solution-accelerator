"""Human-in-the-Loop checkpoint primitive.

Every side-effect tool MUST call ``checkpoint`` before executing.

- In **production** an approver endpoint is required. Set
  ``HITL_APPROVER_ENDPOINT`` to a partner-hosted approval service (Teams bot,
  ITSM queue, web UI). The checkpoint blocks until a decision arrives.
- In **development** (smoke tests, local runs), set ``HITL_DEV_MODE=1`` to
  enable the console reviewer which auto-approves with a loud warning.
- With neither set, ``checkpoint`` **fails closed** — it will NOT silently
  approve actions. This is deliberate to prevent a misconfigured production
  environment from side-effecting without a human in the loop.

Policy format (per-tool / per-call; `accelerator.yaml.solution.hitl` is
engagement-level documentation read by the lint, not by ``checkpoint`` at
runtime):
    always           — block until a human approves
    never            — skip the checkpoint unconditionally. Only safe
                       when the action is reversible AND the engagement
                       has documented `accelerator.yaml.solution.hitl =
                       none` in the handover packet.
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


class HITLMisconfigured(Exception):
    """Raised when side-effect tools run without any configured approver.

    Fail-closed: a production deployment that forgot to set
    ``HITL_APPROVER_ENDPOINT`` must not silently approve side-effect calls.
    """


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
    dev_mode = os.getenv("HITL_DEV_MODE", "").lower() in ("1", "true", "on")

    if approver:
        approved = await _remote_review(approver, tool, args, reviewer_context or {})
    elif dev_mode:
        approved = await _console_review(tool, args, reviewer_context or {})
    else:
        # Fail closed — never silently approve a side-effect in prod.
        emit_event(Event(name="tool.hitl_misconfigured",
                         args_redacted=dict(args), external_system=tool,
                         ok=False, error="no approver and not dev mode"))
        raise HITLMisconfigured(
            f"HITL required for tool={tool} but neither HITL_APPROVER_ENDPOINT "
            f"is set nor HITL_DEV_MODE=1. Refusing to execute side-effect."
        )

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
    # DEV-ONLY. Reachable only when HITL_DEV_MODE=1 is explicitly set AND
    # no HITL_APPROVER_ENDPOINT is configured.
    logger.warning("HITL_DEV_MODE console review — tool=%s args=%s",
                   tool, json.dumps(dict(args), default=str))
    return True


async def _remote_review(endpoint: str, tool: str, args: Mapping[str, Any],
                         ctx: Mapping[str, Any]) -> bool:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            endpoint,
            json={"tool": tool, "args": dict(args), "context": dict(ctx)},
        )
        resp.raise_for_status()
        return bool(resp.json().get("approved", False))
