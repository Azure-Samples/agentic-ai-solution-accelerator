"""Eval result schema.

Both quality and redteam evals produce results in this shape. CI reads
``evals/quality/results.jsonl`` + ``evals/redteam/results.jsonl`` after each
run and enforces acceptance thresholds from ``accelerator.yaml``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalResult:
    case_id: str
    suite: str              # "quality" | "redteam"
    passed: bool
    score: float | None = None       # 0..1 for continuous evals
    latency_ms: int | None = None
    cost_usd: float | None = None
    groundedness: float | None = None
    reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Acceptance:
    quality_threshold: float
    groundedness_threshold: float
    p95_latency_ms: int
    cost_per_call_usd: float
    redteam_must_pass: bool = True


def evaluate_acceptance(results: list[EvalResult], acc: Acceptance) -> tuple[bool, list[str]]:
    """Return (accepted, failures) given a set of results + the acceptance block."""
    failures: list[str] = []

    quality = [r for r in results if r.suite == "quality"]
    redteam = [r for r in results if r.suite == "redteam"]

    if quality:
        avg_score = sum(r.score or 0 for r in quality) / len(quality)
        if avg_score < acc.quality_threshold:
            failures.append(
                f"quality: avg score {avg_score:.3f} < threshold {acc.quality_threshold}"
            )
        grounded = [r.groundedness for r in quality if r.groundedness is not None]
        if grounded:
            avg_g = sum(grounded) / len(grounded)
            if avg_g < acc.groundedness_threshold:
                failures.append(
                    f"groundedness: avg {avg_g:.3f} < threshold {acc.groundedness_threshold}"
                )
        latencies = [r.latency_ms for r in quality if r.latency_ms]
        if latencies:
            latencies.sort()
            p95 = latencies[int(0.95 * (len(latencies) - 1))]
            if p95 > acc.p95_latency_ms:
                failures.append(f"latency P95 {p95}ms > {acc.p95_latency_ms}ms")
        costs = [r.cost_usd for r in quality if r.cost_usd is not None]
        if costs:
            avg_cost = sum(costs) / len(costs)
            if avg_cost > acc.cost_per_call_usd:
                failures.append(f"cost avg ${avg_cost:.4f} > ${acc.cost_per_call_usd}")

    if acc.redteam_must_pass and any(not r.passed for r in redteam):
        count = sum(1 for r in redteam if not r.passed)
        failures.append(f"redteam: {count} failing cases (must pass all)")

    return (not failures, failures)
