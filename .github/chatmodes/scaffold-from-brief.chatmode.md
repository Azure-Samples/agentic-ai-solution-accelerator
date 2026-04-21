---
description: Thin wrapper over scripts/scaffold-scenario.py — materializes a new scenario package, then guides the partner through pasting the manifest snippet and customizing per the solution brief.
tools: ['codebase', 'editFiles', 'search', 'terminal']
---

# /scaffold-from-brief — generate a scenario from the discovery brief

You are applying the customer's filled `docs/discovery/solution-brief.md` to this repo. The structural work is delegated to `scripts/scaffold-scenario.py`; your job is to (a) drive the CLI, (b) update `accelerator.yaml`, and (c) customize per the brief.

## Preflight
1. Open `docs/discovery/solution-brief.md`. If any section is missing or contains `TBD`, STOP and ask the partner to run `/discover-scenario` first.
2. Open `accelerator.yaml`. Check whether the existing `scenario:` block is the flagship (`id: sales-research`) or a prior partner-scaffolded scenario.
3. Confirm a scenario id with the partner (kebab-case slug, e.g. `order-triage`, `claims-intake`).

## Step 1 — Run the scaffolder
```bash
python scripts/scaffold-scenario.py <scenario-id>
```
This materializes:
- `src/scenarios/<package>/{__init__,schema,workflow,retrieval}.py`
- `src/scenarios/<package>/agents/supervisor/{__init__,prompt,transform,validate}.py`
- `docs/agent-specs/accel-<scenario-id>-supervisor.md`
- `data/samples/<package>.json`

Package leaf is auto-derived (hyphens → underscores). The CLI fails fast if any target exists, and rolls back on partial failure.

## Step 2 — Update `accelerator.yaml`
Copy the `scenario:` snippet the CLI printed and paste it into `accelerator.yaml`, **replacing** the existing `scenario:` block. Then re-sync the rest of the manifest with the brief:
- `solution.name` → kebab slug of the engagement
- `solution.pattern` / `hitl` / `data_residency` / `identity`
- `solution.side_effect_tools` → tools your scenario will call (each must exist under `src/tools/` and pass HITL)
- `acceptance.*` → thresholds drawn from the brief's success criteria
- `kpis[]` → instrumentation events the scenario will emit

## Step 3 — Customize per the brief

| Brief section | Apply to |
|---|---|
| 1. Problem + persona | `src/scenarios/<package>/agents/supervisor/prompt.py` — rewrite intro paragraph |
| 5. Solution shape (not supervisor-routing) | Drop the supervisor stub and re-shape `workflow.py` for `single-agent` or `chat-with-actioning` |
| 5. Grounding sources | Edit `src/scenarios/<package>/retrieval.py` — add fields/connectors; declare additional indexes under `scenario.retrieval.indexes` and re-run scaffolder for new agents if needed |
| 5. Side-effect tools | Create `src/tools/<tool_name>.py`, each wrapped with `hitl.checkpoint(...)`; reference the tool name from the supervisor's `requires_approval` output |
| 5. HITL gates | `src/accelerator_baseline/hitl.py` — rules per tool + confidence threshold |
| 6. Constraints | `infra/main.parameters.json` + `accelerator.yaml.controls.*` |
| 3+7. Success criteria → acceptance | `evals/quality/golden_cases.jsonl` — replace flagship cases with 5+ for this scenario |
| 6. RAI risks | `evals/redteam/cases.jsonl` — one case per risk |
| 4. KPIs | `src/accelerator_baseline/telemetry.py` — register each named KPI event; `infra/dashboards/roi-kpis.json` — add a chart per KPI |

## Step 4 — Add additional worker agents (optional)
If the brief implies more than a supervisor (typical for `supervisor-routing`), add worker packages under `src/scenarios/<package>/agents/<worker>/` following the same three-layer shape (`prompt.py`, `transform.py`, `validate.py`, `__init__.py` exporting `AGENT_NAME`). Add each to `scenario.agents[]` in the manifest and ship a matching `docs/agent-specs/<foundry_name>.md` spec file. The `foundry-bootstrap.py` script syncs them all to Foundry on the next `azd up`.

## Step 5 — Validate
```bash
python -c "from src.main import app"
flake8 src --select=E9,F63,F7,F82
python scripts/accelerator-lint.py
```
The lint's `scenario-manifest` check AST-validates every import ref in the new `scenario:` block; `agents-three-layer` verifies the package's `agents/` directory contains complete three-layer agents.

## Guardrails
- NEVER write Foundry agent system instructions in code. Those live in the Foundry portal; prompts in `prompt.py` are request-builders.
- NEVER weaken HITL, telemetry, evals, or content-filter controls to fit the brief. If the brief implies they should be weakened, flag to the partner — don't comply.
- Keep all edits consistent with `.github/copilot-instructions.md`.
- If the brief demands a stack other than Agent Framework + Foundry, STOP and escalate. This template doesn't support alternative stacks.

## Output
Summarize for the partner as a table: file changed, reason (which brief section drove it), whether it needs further human authoring (e.g., golden cases, retrieval connector credentials).
