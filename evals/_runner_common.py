"""Shared helpers for the eval runners (quality + redteam).

Currently exposes ``warmup_endpoint`` so both runners dodge the
Container Apps scale-to-zero cold start that otherwise flunks the
first eval case with a transport timeout.

Kept dependency-free beyond ``httpx`` (already a runner dep) so the
helper works in any partner clone without extra installs.
"""
from __future__ import annotations

import asyncio
import sys
import time

import httpx


async def warmup_endpoint(
    client: httpx.AsyncClient,
    api_url: str,
    *,
    max_wait_s: float = 120.0,
    interval_s: float = 5.0,
    attempt_timeout_s: float = 10.0,
) -> bool:
    """Poll ``GET {api_url}/healthz`` until it returns 200, or give up.

    Returns ``True`` if the endpoint became healthy within ``max_wait_s``,
    ``False`` otherwise. Never raises -- a failed warmup falls through and
    lets the actual eval cases surface the underlying problem so we don't
    introduce a NEW failure mode on top of the existing one.

    All log lines go to stderr so stdout stays clean for JSONL results.

    The FastAPI app's ``lifespan`` runs ``bootstrap`` + ``workflow.warmup``
    before serving routes, so a successful ``/healthz`` means the process
    is alive AND the in-process warmup completed. That covers the dominant
    cold-start cost (Container Apps scaling from zero); downstream Foundry /
    AI Search calls still happen on the first eval case but at warm-cluster
    latency.
    """
    base = api_url.rstrip("/")
    health_url = f"{base}/healthz"
    print(f"warming up endpoint via {health_url} (max {max_wait_s:.0f}s)...", file=sys.stderr)

    deadline = time.monotonic() + max_wait_s
    last_error: str | None = None
    while True:
        attempt_start = time.monotonic()
        try:
            resp = await client.get(health_url, timeout=attempt_timeout_s)
            if resp.status_code == 200:
                elapsed = time.monotonic() - (deadline - max_wait_s)
                print(f"endpoint warm after {elapsed:.1f}s", file=sys.stderr)
                return True
            last_error = f"HTTP {resp.status_code}"
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        if time.monotonic() >= deadline:
            print(
                f"warning: endpoint did not become healthy after {max_wait_s:.0f}s; "
                f"continuing with eval cases. last error: {last_error}",
                file=sys.stderr,
            )
            return False

        # Sleep the remainder of the interval (don't double-wait if the
        # attempt itself already burned most of it).
        slept = time.monotonic() - attempt_start
        remaining = max(0.0, interval_s - slept)
        if remaining:
            await asyncio.sleep(remaining)
