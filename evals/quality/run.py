"""Run quality evals against the local API.

Usage:
    python evals/quality/run.py --api-url http://localhost:8000
    python evals/quality/run.py --api-url $API_URL --out results.jsonl

Each case is a JSON line. The runner is scenario-agnostic:

* Payload: every case field except the reserved eval-control keys
  (``case_id``, ``expected``, ``technique``, ``notes``) is passed through
  verbatim to ``POST {scenario.endpoint.path}``. The active scenario's
  pydantic ``request_schema`` is therefore the source of truth; the dataset
  must match it.
* Checks: declared per-case under ``expected``:
    - ``must_mention``: list of substrings that MUST appear in the
      lowercased JSON dump of the final briefing.
    - ``must_cite``: if true, the briefing must contain a non-empty
      ``"citations"`` list somewhere in its tree.
    - ``thresholds``: ``{"<dotted.path>": {"min": N, "max": M}}`` comparing
      numeric values in the briefing.
    - Flagship back-compat: ``icp_fit_min`` (int, 0-100) is treated as
      ``thresholds: {"icp_fit.fit_score": {"min": N}}``.

Results land in ``results.jsonl`` for CI's ``accept`` gate. The endpoint
path comes from ``scenario.endpoint.path`` in ``accelerator.yaml``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import sys
import time

import httpx

HERE = pathlib.Path(__file__).parent
REPO_ROOT = HERE.parent.parent
CASES = HERE / "golden_cases.jsonl"
sys.path.insert(0, str(REPO_ROOT))

RESERVED_CASE_KEYS = {"case_id", "expected", "technique", "notes"}
_CITATIONS_RE = re.compile(r'"citations"\s*:\s*\[\s*[^\]\s]')


def _load_endpoint_path() -> str:
    from src.workflow.registry import read_scenario_raw

    scenario = read_scenario_raw(REPO_ROOT / "accelerator.yaml")
    path = (scenario.get("endpoint") or {}).get("path")
    if not path:
        raise RuntimeError(
            "accelerator.yaml: scenario.endpoint.path is required"
        )
    return path


def _get_dotted(obj: dict, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def _normalize_expected(expected: dict) -> dict:
    """Back-compat: fold `icp_fit_min` into `thresholds`."""
    exp = dict(expected or {})
    thresholds = dict(exp.get("thresholds") or {})
    if "icp_fit_min" in exp and "icp_fit.fit_score" not in thresholds:
        thresholds["icp_fit.fit_score"] = {"min": exp["icp_fit_min"]}
    exp["thresholds"] = thresholds
    return exp


async def run_case(
    client: httpx.AsyncClient, api_url: str, endpoint_path: str, case: dict,
) -> dict:
    started = time.time()
    payload = {k: v for k, v in case.items() if k not in RESERVED_CASE_KEYS}
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

    expected = _normalize_expected(case.get("expected", {}))
    blob_raw = json.dumps(final_briefing)
    blob = blob_raw.lower()
    citations_ok = bool(_CITATIONS_RE.search(blob_raw))

    score = 1.0
    reasons: list[str] = []

    for dotted, bound in (expected.get("thresholds") or {}).items():
        val = _get_dotted(final_briefing, dotted)
        if not isinstance(val, (int, float)):
            score -= 0.4
            reasons.append(f"{dotted}: not numeric ({val!r})")
            continue
        if "min" in bound and val < bound["min"]:
            score -= 0.4
            reasons.append(f"{dotted} {val} < {bound['min']}")
        if "max" in bound and val > bound["max"]:
            score -= 0.4
            reasons.append(f"{dotted} {val} > {bound['max']}")

    for phrase in expected.get("must_mention", []):
        if phrase.lower() not in blob:
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
