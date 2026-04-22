---
description: Add a new specialist worker agent to the supervisor orchestration, following the three-layer prompt/transform/validate pattern, and wire it into the workflow.
tools: ['codebase', 'editFiles', 'search']
---

# /add-worker-agent — scaffold a new worker following the 3-layer pattern

Use this when the brief or a follow-on requirement introduces a capability no current worker covers (e.g., "pricing calc", "risk scoring", "invoice classification").

## Preconditions
- The solution is using the `supervisor-routing` pattern (check `accelerator.yaml.solution.pattern`).
- The new worker has a clear, one-sentence capability. If you can't write that sentence, push back on the partner to clarify — don't scaffold fuzziness.

## Ask the partner
1. **Agent name** (snake_case, e.g., `pricing_calculator`)
2. **One-sentence capability** (used in the supervisor's routing prompt)
3. **Input fields** (what the supervisor passes it)
4. **Output schema** (JSON shape `transform_response` will produce)
5. **Tools it uses** (call out any side-effect tools; HITL applies)
6. **Foundry agent name** (will be retrieved via `AzureAIClient(agent_name=..., use_latest_version=True)`)

## Files to create
```
src/scenarios/<scenario>/agents/<agent_name>/
├── __init__.py
├── prompt.py       build_prompt(request_data: dict) -> str
├── transform.py    transform_response(response: str) -> dict
└── validate.py     validate_response(response: dict) -> tuple[bool, str]
```

## prompt.py skeleton
```python
"""<Agent display name> prompt builder.

Capability: <one-sentence capability>
"""
from __future__ import annotations


def build_prompt(request_data: dict) -> str:
    return (
        "Task: <derived from capability>.\n"
        "Context: <fields from request_data>.\n"
        "Output: JSON matching the documented schema; include `sources: []` for any factual claim."
    )
```

## transform.py skeleton
```python
from __future__ import annotations
import json


def transform_response(response: str) -> dict:
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        start, end = response.find("{"), response.rfind("}")
        data = json.loads(response[start:end + 1]) if start >= 0 else {}
    return {**data}
```

## validate.py skeleton
```python
from __future__ import annotations


REQUIRED_FIELDS: tuple[str, ...] = ()


def validate_response(response: dict) -> tuple[bool, str]:
    missing = [f for f in REQUIRED_FIELDS if f not in response]
    if missing:
        return False, f"missing fields: {missing}"
    if response.get("factual_claims") and not response.get("sources"):
        return False, "factual claims without sources"
    return True, ""
```

## Wire into supervisor
1. In `src/scenarios/<scenario>/agents/supervisor/prompt.py`, add a routing cue for the new worker.
2. In `src/scenarios/<scenario>/workflow.py`, add the worker to the executor graph; register the Foundry agent name in `accelerator.yaml -> scenario.agents[]`.
3. In `src/accelerator_baseline/telemetry.py`, add `worker.<agent_name>.completed` if missing.

## Evals
Add at least 2 golden cases to `evals/quality/golden_cases.jsonl` that exercise this worker through the supervisor, with expected fields and acceptance thresholds.

## Guardrails
- If a side-effect tool is needed, also run `/add-tool` for each. Never mix tool creation with worker scaffolding.
- Do NOT write the Foundry system prompt in code. Ensure the Foundry agent already exists in the portal.
- Run `scripts/accelerator-lint.py` after to catch registration gaps.
