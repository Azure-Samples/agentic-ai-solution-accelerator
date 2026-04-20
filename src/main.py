"""FastAPI entrypoint for the flagship Sales Research & Outreach solution.

Key properties (enforced by scripts/accelerator-lint.py):
- DefaultAzureCredential only; no secrets in env.
- OpenTelemetry configured at startup for App Insights correlation.
- SSE streaming for agent progress; no WebSockets / long polling.
- No agent instructions in code — Foundry portal holds them.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .accelerator_baseline.telemetry import Event, emit_event
from .config.settings import load_settings
from .workflow.sales_research_workflow import SalesResearchWorkflow

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
        configure_azure_monitor(connection_string=s.appinsights_connection,
                                logger_name="accelerator")
        logger.info("App Insights wired up.")


app = FastAPI(title="Sales Research & Outreach Accelerator", version="0.1.0")
_configure_otel()
_workflow = SalesResearchWorkflow()


class ResearchRequest(BaseModel):
    company_name: str
    domain: str = ""
    seller_intent: str = Field(..., description="What the seller wants from this account")
    persona: str = "Decision maker"
    icp_definition: str
    our_solution: str
    context_hints: list[str] = []


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/research/stream")
async def research_stream(req: ResearchRequest, request: Request) -> StreamingResponse:
    async def gen() -> AsyncIterator[bytes]:
        try:
            async for event in _workflow.stream(req.model_dump()):
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(event)}\n\n".encode()
        except Exception as exc:  # surface to client as SSE error event
            emit_event(Event(name="response.returned", ok=False, error=str(exc)))
            payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(payload)}\n\n".encode()

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
