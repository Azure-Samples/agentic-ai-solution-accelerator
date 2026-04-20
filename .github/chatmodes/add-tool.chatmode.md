---
description: Add a side-effect tool (CRM write, ticket create, email send, etc.) with HITL scaffolding, telemetry, and a redteam case.
tools: ['codebase', 'editFiles', 'search']
---

# /add-tool — scaffold a side-effect tool with HITL baked in

Use this for any tool that writes, sends, mutates external state, or triggers destructive actions. If the tool is read-only, you probably don't need this — just add a retriever under `src/retrieval/`.

## Ask the partner
1. **Tool name** (snake_case, e.g., `crm_create_contact`)
2. **External system** (e.g., Salesforce, ServiceNow, Dynamics, SMTP)
3. **Operation** (verb + object, e.g., "create Contact in Salesforce")
4. **Reversibility** (reversible / irreversible — affects HITL default)
5. **HITL policy**: `always` / `threshold(<field> < X)` / `never` (only if reversible AND `accelerator.yaml.solution.hitl = none`)
6. **Which worker agent uses it** (must already exist)
7. **Auth approach** (Managed Identity / OAuth-via-KeyVault)

## Create `src/tools/<tool_name>.py`
```python
"""<Tool display name> — side-effect tool.

Operation: <verb + object>
External system: <system>
HITL: <policy>
Auth: <approach>
"""
from __future__ import annotations
from typing import Any
from azure.identity import DefaultAzureCredential
from ..accelerator_baseline.hitl import checkpoint, HITLDenied
from ..accelerator_baseline.telemetry import emit_event, Event


INPUT_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
}


async def run(args: dict[str, Any]) -> dict[str, Any]:
    await checkpoint(
        tool="<tool_name>",
        args=args,
        policy="<hitl policy>",
    )

    credential = DefaultAzureCredential()
    # call external system
    result: dict[str, Any] = {}

    emit_event(Event(
        name="tool.<tool_name>.executed",
        args_redacted={k: _redact(v) for k, v in args.items()},
        external_system="<system>",
        ok=True,
    ))
    return result


def _redact(v: Any) -> Any:
    return v
```

## Register on the worker
Expose the tool in the worker's tool registry so Foundry advertises it.

## Tests
`tests/tools/test_<tool_name>.py`:
- HITL approve → tool executes
- HITL deny → raises `HITLDenied`, no external call
- Redaction → no raw PII in events

## Redteam case
Add one case to `evals/redteam/` exercising prompt-injection and jailbreak attempts to misuse the tool.

## Guardrails
- NEVER skip `checkpoint(...)`.
- NEVER inline secrets; use `DefaultAzureCredential` or KeyVault references.
- NEVER use `requests` when an official SDK exists.
- Emit telemetry even on failure (`ok=False`).
- Run `scripts/accelerator-lint.py` after.
