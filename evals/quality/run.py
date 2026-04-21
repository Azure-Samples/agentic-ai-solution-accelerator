"""Run quality evals against the local API.

Usage:
    python evals/quality/run.py --api-url http://localhost:8000
    python evals/quality/run.py --api-url $API_URL --out results.jsonl

Each case is a JSON line with ``expected`` thresholds. Results land in
``results.jsonl`` for CI's ``accept`` gate. The endpoint path comes from
``scenario.endpoint.path`` in ``accelerator.yaml`` so renaming ``/research/stream``
to something scenario-specific doesn't break evals.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time

import httpx

HERE = pathlib.Path(__file__).parent
REPO_ROOT = HERE.parent.parent
CASES = HERE / "golden_cases.jsonl"
sys.path.insert(0, str(REPO_ROOT))


def _load_endpoint_path() -> str:
    from src.workflow.registry import read_scenario_raw

    scenario = read_scenario_raw(REPO_ROOT / "accelerator.yaml")
    path = (scenario.get("endpoint") or {}).get("path")
    if not path:
        raise RuntimeError(
            "accelerator.yaml: scenario.endpoint.path is required"
        )
    return path


async def run_case(
    client: httpx.AsyncClient, api_url: str, endpoint_path: str, case: dict,
) -> dict:
    started = time.time()
    payload = {k: case[k] for k in (
        "company_name", "domain", "persona",
        "seller_intent", "icp_definition", "our_solution",
    )}
    final_briefing = None
    try:
        async with client.stream(
            "POST", f"{api_url}{endpoint_path}", json=payload, timeout=120.0,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line.removeprefix("data:").strip())
                if event.get("type") == "final":
                    final_briefing = event["briefing"]
    except Exception as exc:
        return {"case_id": case["case_id"], "suite": "quality",
                "passed": False, "reason": f"transport: {exc}"}

    if final_briefing is None:
        return {"case_id": case["case_id"], "suite": "quality",
                "passed": False, "reason": "no final briefing"}

    expected = case["expected"]
    icp_score = (final_briefing.get("icp_fit", {}) or {}).get("fit_score", 0)
    profile_text = json.dumps(final_briefing.get("account_profile", {})).lower()
    citations_ok = bool((final_briefing.get("account_profile", {}) or {}).get("citations"))

    score = 1.0
    reasons = []
    if icp_score < expected.get("icp_fit_min", 0):
        score -= 0.4
        reasons.append(f"icp {icp_score} < {expected['icp_fit_min']}")
    for phrase in expected.get("must_mention", []):
        if phrase.lower() not in profile_text:
            score -= 0.2
            reasons.append(f"missing mention: {phrase}")
    groundedness = 1.0 if citations_ok else 0.0
    if expected.get("must_cite") and not citations_ok:
        reasons.append("no citations")

    latency_ms = int((time.time() - started) * 1000)
    passed = score >= 0.6 and (groundedness >= 0.8 or not expected.get("must_cite"))

    return {
        "case_id": case["case_id"], "suite": "quality",
        "passed": passed, "score": round(max(score, 0.0), 3),
        "groundedness": groundedness, "latency_ms": latency_ms,
        "reason": "; ".join(reasons) or None,
    }


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-url", default="http://localhost:8000")
    p.add_argument("--out", default=str(HERE / "results.jsonl"))
    args = p.parse_args()

    endpoint_path = _load_endpoint_path()
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    async with httpx.AsyncClient() as client:
        results = []
        for case in cases:
            r = await run_case(client, args.api_url, endpoint_path, case)
            results.append(r)
            print(json.dumps(r))

    pathlib.Path(args.out).write_text("\n".join(json.dumps(r) for r in results) + "\n")
    failed = [r for r in results if not r["passed"]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
