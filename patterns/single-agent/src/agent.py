"""Single-agent variant — grounded QA with one Foundry agent.

Drop-in replacement for ``src/main.py`` when the solution does not need a
supervisor + workers. Reuses the accelerator_baseline primitives.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

try:
    from agent_framework.azure import AzureAIClient  # type: ignore
except Exception:  # pragma: no cover
    AzureAIClient = None  # type: ignore

from src.accelerator_baseline.killswitch import assert_enabled
from src.accelerator_baseline.telemetry import Event, emit_event

logger = logging.getLogger("accelerator.single_agent")

AGENT_NAME = "accel-single-agent"

app = FastAPI(title="Single-Agent Accelerator", version="0.1.0")


class AskRequest(BaseModel):
    question: str


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask/stream")
async def ask_stream(req: AskRequest, request: Request) -> StreamingResponse:
    async def gen() -> AsyncIterator[bytes]:
        assert_enabled("workflow")
        emit_event(Event(name="request.received",
                         args_redacted={"q_len": len(req.question)}))
        if AzureAIClient is None:
            yield b"data: {\"type\":\"error\",\"message\":\"SDK not installed\"}\n\n"
            return
        client = AzureAIClient(agent_name=AGENT_NAME, use_latest_version=True)
        agent = client.as_agent()
        async for chunk in agent.run_stream(req.question):
            if await request.is_disconnected():
                break
            payload = {"type": "chunk", "content": getattr(chunk, "text", str(chunk))}
            yield f"data: {json.dumps(payload)}\n\n".encode()
        emit_event(Event(name="response.returned", ok=True))
        yield b"data: {\"type\":\"final\"}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
