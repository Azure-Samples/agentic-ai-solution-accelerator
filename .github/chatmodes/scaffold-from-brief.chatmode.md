---
description: Thin wrapper over scripts/scaffold-scenario.py — materializes a new scenario package, then walks through pasting the manifest snippet and customising per the solution brief.
tools: ['codebase', 'editFiles', 'search', 'terminal']
---

# /scaffold-from-brief — generate a scenario from the discovery brief

You are applying the customer's filled `docs/discovery/solution-brief.md` to this repo. The structural work is delegated to `scripts/scaffold-scenario.py`; your job is to (a) drive the CLI, (b) update `accelerator.yaml`, and (c) customize per the brief.

## Preflight
1. Open `docs/discovery/solution-brief.md`. If any section is missing or contains `TBD`, STOP and reply: "Run `/discover-scenario` first to fill the brief." Then stop.
2. Open `accelerator.yaml`. Check whether the existing `scenario:` block is the flagship (`id: sales-research`) or a prior partner-scaffolded scenario.
3. Confirm a scenario id (lowercase-with-hyphens, e.g. `order-triage`, `claims-intake`).

## Step 1 — Run the scaffolder
```bash
# <scenario-id> is the scenario slug, lowercase-with-hyphens (e.g., sales-research, customer-service)
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
- `solution.name` → engagement slug (lowercase-with-hyphens)
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
If the brief implies more than a supervisor (typical for `supervisor-routing`), add worker packages under `src/scenarios/<package>/agents/<worker>/` following the same three-layer shape (`prompt.py`, `transform.py`, `validate.py`, `__init__.py` exporting `AGENT_NAME`). Add each to `scenario.agents[]` in the manifest and ship a matching `docs/agent-specs/<foundry_name>.md` spec file. The `src/bootstrap.py` startup bootstrap syncs them all to Foundry on the next `azd up` / `azd deploy`.

## Step 5 — Validate
```bash
python -c "from src.main import app"
flake8 src --select=E9,F63,F7,F82
python scripts/accelerator-lint.py
```
The lint's `scenario-manifest` check validates every import ref in the new `scenario:` block; `agents-three-layer` verifies the package's `agents/` directory contains complete three-layer agents.

## Step 6 — Surface the UX-shape next step

Read the `## UX shape` / `ux_shape` field from `docs/discovery/solution-brief.md` and print the matching next-step block. Do **not** scaffold any frontend code — frontend forking is a manual decision. Just signpost:

| `ux_shape` value | Print to chat |
|---|---|
| **Structured form + report** | "Next step (frontend starter): `cd patterns/sales-research-frontend && cp -r . ../../my-frontend && cd ../../my-frontend && npm install`. Then walk the **UX inputs** and **UX output sections** tables below to adapt the form and result panels." |
| **Chat** | "No chat UI pattern shipped yet. The `chat-with-actioning` backend pattern supports this shape — build the UI on top (or use any chat UI framework). Consume `/<scenario>/stream` from your client." |
| **Dashboard / viewer** | "No UI work in this repo. Have the customer's existing app consume the SSE endpoint at `/<scenario>/stream` — see `patterns/sales-research-frontend/src/services/researchClient.ts` for a reference SSE client to lift." |
| **API-only / embed** | "No UI. The hosted SSE endpoint at `/<scenario>/stream` IS the deliverable. Hand the URL + auth scheme to the integrating system (Power Automate, n8n, partner platform)." |
| TBD / missing | "The brief's `ux_shape` field is empty. Re-run `/discover-scenario` to fill it before deciding on a frontend." |

### Step 6a — Form + report deep-dive (only when `ux_shape` is `Structured form + report`)

Read the brief's `## UX inputs` and `## UX output sections` tables. If either is missing or still contains `TBD`, reply: "Re-run `/discover-scenario` to fill the UX inputs / UX output sections tables before continuing." Then stop.

1. **Print `## UX inputs` back verbatim**, then add:
   > *"Next: adapt `patterns/sales-research-frontend/src/components/ResearchForm.tsx` — replace the current form fields with the rows above. Your `src/scenarios/<pkg>/schema.py` `ScenarioRequest` should declare exactly these fields with matching types."*

2. **Print `## UX output sections` back verbatim**, then add:
   > *"Next: adapt `patterns/sales-research-frontend/src/components/ResultPanel.tsx` — render one subsection per row above. Your supervisor's `transform.py` should emit a dict with one top-level key per section (lowercase_with_underscores form of the section name); `validate.py` should enforce the schema."*

3. **Emit `docs/discovery/ux-blueprint.md`** — a generated reference doc that persists both tables for downstream work. Use this template, substituting the tables verbatim from the brief:

   ```markdown
   # UX blueprint — <scenario-id>

   > Generated by `/scaffold-from-brief` from `docs/discovery/solution-brief.md`.
   > This is a **reference snapshot** of the form+report contract — keep it
   > in sync with the brief if either changes. Wired to:
   > `patterns/sales-research-frontend/src/components/ResearchForm.tsx`,
   > `patterns/sales-research-frontend/src/components/ResultPanel.tsx`,
   > `src/scenarios/<pkg>/schema.py`,
   > `src/scenarios/<pkg>/agents/supervisor/transform.py`.

   ## Inputs (form fields)

   <copy `## UX inputs` table from the brief>

   ## Output sections (result panels)

   <copy `## UX output sections` table from the brief>
   ```

   Overwrite if the file already exists; the brief is the source of truth.

## Guardrails
- NEVER write Foundry agent system instructions in code. Those live in the Foundry portal; prompts in `prompt.py` are request-builders.
- NEVER weaken HITL, telemetry, evals, or content-filter controls to fit the brief. If the brief implies they should be weakened, flag the conflict — don't comply.
- Keep all edits consistent with `.github/copilot-instructions.md`.
- If the brief demands a stack other than Agent Framework + Foundry, STOP and escalate. This template doesn't support alternative stacks.

## Output
Summarize as a table: file changed, reason (which brief section drove it), whether it needs further human authoring (e.g., golden cases, retrieval connector credentials).
