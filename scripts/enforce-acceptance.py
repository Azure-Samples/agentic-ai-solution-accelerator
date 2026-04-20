"""Enforce every threshold in accelerator.yaml.acceptance.

Called from .github/workflows/evals.yml after quality + redteam runs.

Inputs:
  accelerator.yaml           -> acceptance block
  evals/quality/results.jsonl
  evals/redteam/results.jsonl

Exit non-zero if any threshold is violated. Prints a failure table.
"""
from __future__ import annotations

import json
import pathlib
import sys

import yaml

from src.accelerator_baseline.evals import Acceptance, EvalResult, evaluate_acceptance

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_results(path: pathlib.Path, suite: str) -> list[EvalResult]:
    out: list[EvalResult] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        out.append(EvalResult(
            case_id=d["case_id"],
            suite=suite,
            passed=bool(d.get("passed", False)),
            score=d.get("score"),
            groundedness=d.get("groundedness"),
            latency_ms=d.get("latency_ms"),
            cost_usd=d.get("cost_usd"),
            reason=d.get("reason"),
        ))
    return out


def main() -> int:
    manifest = yaml.safe_load((ROOT / "accelerator.yaml").read_text(encoding="utf-8"))
    acc_block = manifest.get("acceptance", {}) or {}
    acc = Acceptance(
        quality_threshold=float(acc_block.get("quality_threshold", 0.0)),
        groundedness_threshold=float(acc_block.get("groundedness_threshold", 0.0)),
        p95_latency_ms=int(acc_block.get("p95_latency_ms", 0)),
        cost_per_call_usd=float(acc_block.get("cost_per_call_usd", 0.0)),
        redteam_must_pass=bool(acc_block.get("redteam_must_pass", True)),
    )

    quality = _load_results(ROOT / "evals/quality/results.jsonl", "quality")
    redteam = _load_results(ROOT / "evals/redteam/results.jsonl", "redteam")

    if not quality:
        print("::error::no quality results (evals/quality/results.jsonl is empty)")
        return 1
    if not redteam:
        print("::error::no redteam results (evals/redteam/results.jsonl is empty)")
        return 1

    accepted, failures = evaluate_acceptance(quality + redteam, acc)
    if accepted:
        print("ACCEPT: all acceptance gates passed.")
        return 0
    for f in failures:
        print(f"::error::{f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
