---
description: Switch the repo from the flagship supervisor-routing pattern to a simpler variant (single-agent or chat-with-actioning), or vice versa.
tools: ['codebase', 'editFiles', 'search', 'terminal']
---

# /switch-to-variant — change the solution shape

Use this when the brief or customer feedback indicates the current pattern is over- or under-powered.

## Choices
- **single-agent** — one agent + retrieval + 1–2 tools. Best for narrow Q&A-with-actioning.
- **chat-with-actioning** — conversational front-end with tools + HITL. Best when UX is a chat thread.
- **supervisor-routing** — flagship default; 2+ specialists + aggregation.

## Actions by target

### → single-agent
1. Copy `patterns/single-agent/src/` into `src/agents/main/` (adjust imports).
2. Move current workers' domain knowledge into `src/agents/main/prompt.py` as composition.
3. Keep one or two most-used tools; drop the rest.
4. Delete `src/agents/supervisor/` and `src/workflow/sales_research_workflow.py` (git history preserves).
5. Set `accelerator.yaml.solution.pattern: single-agent`.
6. Update `docs/architecture.md` diagram.

### → chat-with-actioning
1. Copy `patterns/chat-with-actioning/src/` into `src/`.
2. Preserve workers as tool-backing; move orchestration to a conversation loop.
3. Wire session/thread state (`agent_framework` thread management).
4. Set `accelerator.yaml.solution.pattern: chat-with-actioning`.
5. Confirm HITL still gates every side-effect in the chat loop.

### → supervisor-routing
1. If coming from `single-agent`, split the prompt into worker-aligned capabilities; each becomes a worker.
2. Re-introduce `src/agents/supervisor/` and `src/workflow/sales_research_workflow.py` from template history.
3. Identify ≥2 workers; update supervisor prompt with routing cues.
4. Set `accelerator.yaml.solution.pattern: supervisor-routing`.

## Post-switch
- Run `scripts/accelerator-lint.py`.
- Re-run `evals/quality/` locally; thresholds may need revisiting.
- Commit: `chore: switch pattern to <variant>`.

## Guardrails
- Do NOT silently delete customer-specific logic; move it into the new shape.
- HITL, telemetry, retrieval, content filters stay regardless of variant.
- "Turn off HITL to simplify chat" → refuse; HITL is pattern-agnostic.
