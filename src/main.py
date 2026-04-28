"""FastAPI entrypoint - loads the scenario declared in ``accelerator.yaml``.

Key properties (enforced by scripts/accelerator-lint.py):
- DefaultAzureCredential only; no secrets in env.
- OpenTelemetry configured at startup for App Insights correlation.
- SSE streaming for agent progress; no WebSockets / long polling.
- No agent instructions in code - Foundry portal holds them.
- No scenario-specific imports here - all scenario wiring comes from the
  manifest via :mod:`src.workflow.registry`.
- CORS allow-list driven by the ``ALLOWED_ORIGINS`` env var (comma-separated
  list of exact origins, or ``*`` for sandbox-only allow-all). Empty default
  is production-safe: no cross-origin browser calls until the deployer opts in.
- Foundry agents + AI Search index are bootstrapped synchronously inside the
  ``lifespan`` startup phase by :mod:`src.bootstrap`. The container does not
  accept requests until bootstrap completes; on persistent failure the
  exception aborts startup so ACA marks the revision unhealthy and ``azd up``
  exits non-zero. Replaces the previous postprovision azd hook.
"""
from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from .accelerator_baseline.telemetry import Event, emit_event
from .bootstrap import bootstrap as run_bootstrap
from .config.settings import load_settings
from .workflow.registry import ScenarioBundle, load_scenario

logger = logging.getLogger("accelerator")
logging.basicConfig(level=logging.INFO)


def _configure_otel() -> None:
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor  # type: ignore
    except Exception:
        logger.warning("azure-monitor-opentelemetry not installed; OTel disabled.")
        return
    s = load_settings()
    if s.appinsights_connection:
        configure_azure_monitor(
            connection_string=s.appinsights_connection,
            logger_name="accelerator",
        )
        logger.info("App Insights wired up.")


def _make_stream_endpoint(bundle: ScenarioBundle):
    schema_cls = bundle.request_schema
    workflow = bundle.workflow

    async def stream_endpoint(request: Request) -> StreamingResponse:
        try:
            payload = schema_cls.model_validate(await request.json())
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        async def gen() -> AsyncIterator[bytes]:
            # Stream protocol contract
            # ------------------------
            # Every data event carries a monotonic ``seq`` so the client can
            # detect truncation by ANY intermediate hop (Vite dev proxy,
            # ACA ingress, browser fetch). The stream ALWAYS ends with a
            # terminal ``{"type":"done", "seq":N}`` event — if the client
            # reads EOF without ``done`` it knows the connection was cut
            # mid-flight and must surface that to the user instead of
            # silently treating it as success.
            #
            # Heartbeats from the workflow are converted here to SSE
            # comment lines (``: ka\\n\\n``) which are protocol-level and
            # do NOT reach the EventSource/onmessage handler — keeping
            # the data event stream clean for UI consumers.
            seq = 0
            try:
                async for event in workflow.stream(payload.model_dump()):
                    if await request.is_disconnected():
                        break
                    if isinstance(event, dict) and event.get("type") == "heartbeat":
                        yield b": ka\n\n"
                        continue
                    seq += 1
                    yield f"data: {json.dumps({**event, 'seq': seq})}\n\n".encode()
            except Exception as exc:
                emit_event(Event(name="response.returned", ok=False, error=str(exc)))
                seq += 1
                err = {"type": "error", "message": str(exc), "seq": seq}
                yield f"data: {json.dumps(err)}\n\n".encode()
            # Terminal marker — emitted on BOTH the happy path and after a
            # fatal error. Clients use absence-of-``done`` to detect a
            # truncated stream.
            seq += 1
            yield f"data: {json.dumps({'type': 'done', 'seq': seq})}\n\n".encode()

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                # Tell ACA ingress / nginx-style proxies NOT to buffer the
                # response. Without this some intermediaries hold the body
                # until close, defeating SSE entirely.
                "X-Accel-Buffering": "no",
                # Prevent any cache / transform layer from coalescing or
                # mangling the chunked body.
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
            },
        )

    stream_endpoint.__name__ = f"{bundle.id.replace('-', '_')}_stream"
    return stream_endpoint


def _configure_cors(app: FastAPI) -> None:
    """Install CORS middleware from ``ALLOWED_ORIGINS``.

    The env var is a comma-separated list of exact origins
    (e.g. ``http://localhost:5173,https://contoso.example.com``). The literal
    value ``*`` enables allow-all without credentials — sandbox-only.
    Empty / unset means no cross-origin allowed: the API is server-to-server
    until the deployer explicitly opts in. This is the production-safe default.

    Read directly from ``os.environ`` (not via :func:`load_settings`) so this
    can run before Foundry / Search env vars are present — e.g. in unit-test
    smoke checks of the FastAPI app object.
    """
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if not raw:
        return
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        return
    if origins == ["*"]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info("CORS: allow-all (sandbox mode).")
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info("CORS: allow-listed %d origin(s).", len(origins))


app = FastAPI(
    title="Agentic AI Solution Accelerator",
    version="0.1.0",
    lifespan=None,  # set below once _bundle is loaded
)
_configure_otel()
_configure_cors(app)
_bundle = load_scenario()
logger.info("loaded scenario %r at %s", _bundle.id, _bundle.endpoint_path)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run deploy-time bootstrap before accepting traffic.

    See :mod:`src.bootstrap` for the contract. Failure here propagates and
    aborts uvicorn startup — that is the intended fail-closed signal for
    ``azd up`` (ACA marks the revision unhealthy).
    """
    await run_bootstrap(_bundle)
    # Pre-warm credential and agent version cache so the first user
    # request does not pay a cold-start penalty.
    if hasattr(_bundle.workflow, "warmup"):
        try:
            await _bundle.workflow.warmup()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001 — warmup is best-effort
            logger.debug("workflow.warmup skipped: %s", exc)
    yield


app.router.lifespan_context = _lifespan
app.add_api_route(
    _bundle.endpoint_path,
    _make_stream_endpoint(_bundle),
    methods=["POST"],
    name=f"scenario-{_bundle.id}",
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "scenario": _bundle.id}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)  # noqa: S104  # bind-all expected for containerized app
