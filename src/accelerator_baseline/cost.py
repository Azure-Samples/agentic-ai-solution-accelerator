"""Cost attribution helpers.

Estimates $ per agent invocation using token counts reported by Foundry. The
numbers are rough — the point is to emit *something* per call so cost
dashboards can show trends and the acceptance ``cost_per_call_usd`` gate
has data.

Partners are expected to refine ``MODEL_PRICE_USD_PER_1K_TOKENS`` from their
actual Foundry pricing or Azure consumption export.
"""
from __future__ import annotations

from dataclasses import dataclass

from .telemetry import Event, emit_event


# Rough defaults; override via env or partner's config.
MODEL_PRICE_USD_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "gpt-5.2":   {"input": 0.005, "output": 0.015},
    "gpt-5-mini": {"input": 0.0005, "output": 0.0015},
}


@dataclass
class UsageSample:
    model: str
    input_tokens: int
    output_tokens: int


def estimate_call_cost(u: UsageSample) -> float:
    prices = MODEL_PRICE_USD_PER_1K_TOKENS.get(u.model)
    if not prices:
        return 0.0
    return (
        (u.input_tokens / 1000.0) * prices["input"]
        + (u.output_tokens / 1000.0) * prices["output"]
    )


def record_call_cost(agent: str, u: UsageSample) -> float:
    cost = estimate_call_cost(u)
    emit_event(Event(
        name="cost.call",
        args_redacted={
            "agent": agent,
            "model": u.model,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
        },
        value=cost,
        unit="usd",
    ))
    return cost
