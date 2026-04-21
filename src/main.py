"""FastAPI entrypoint - loads the scenario declared in ``accelerator.yaml``.

Key properties (enforced by scripts/accelerator-lint.py):
- DefaultAzureCredential only; no secrets in env.
- OpenTelemetry configured at startup for App Insights correlation.
- SSE streaming for agent progress; no WebSockets / long polling.
- No agent instructions in code - Foundry portal holds them.
- No scenario-specific imports here - all scenario wiring comes from the
  manifest via :mod:`src.workflow.registry`.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from .accelerator_baseline.telemetry import Event, emit_event
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
            try:
                async for event in workflow.stream(payload.model_dump()):
                    if await request.is_disconnected():
                        break
                    yield f"data: {json.dumps(event)}\n\n".encode()
            except Exception as exc:
                emit_event(Event(name="response.returned", ok=False, error=str(exc)))
                err = {"type": "error", "message": str(exc)}
                yield f"data: {json.dumps(err)}\n\n".encode()

        return StreamingResponse(gen(), media_type="text/event-stream")

    stream_endpoint.__name__ = f"{bundle.id.replace('-', '_')}_stream"
    return stream_endpoint


app = FastAPI(title="Agentic AI Solution Accelerator", version="0.1.0")
_configure_otel()
_bundle = load_scenario()
logger.info("loaded scenario %r at %s", _bundle.id, _bundle.endpoint_path)
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

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
