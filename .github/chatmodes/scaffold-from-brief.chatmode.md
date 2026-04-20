---
description: Read the filled docs/discovery/solution-brief.md and apply it across src/, infra/, evals/, telemetry, and accelerator.yaml so the template is customized for this specific engagement.
tools: ['codebase', 'editFiles', 'search', 'terminal']
---

# /scaffold-from-brief — translate the solution brief into code + infra + evals

You are applying the customer's filled `docs/discovery/solution-brief.md` to this repo. Your job is to change exactly what the brief implies, nothing more.

## Preflight
1. Open `docs/discovery/solution-brief.md`. If any section is missing or contains `TBD`, STOP and ask the partner to run `/discover-scenario` first (or fill the gaps inline).
2. Open `accelerator.yaml`. Confirm it already reflects the brief's solution shape, HITL, residency, identity, acceptance thresholds, and KPI names. If not, sync them first.
3. Identify the chosen pattern: `supervisor-routing` (default) / `single-agent` / `chat-with-actioning`.

## Mapping brief → repo

| Brief section | Apply to |
|---|---|
| 1. Problem + persona | `src/agents/supervisor/prompt.py` system prompt — rewrite the intro paragraph to name the customer, persona, and problem |
| 5. Solution shape (not supervisor) | Run `/switch-to-variant <single-agent\|chat-with-actioning>` instead of scaffolding |
| 5. Grounding sources | `src/retrieval/ai_search.py` — update index schema + connectors; update `infra/modules/ai-search.bicep` parameters |
| 5. Side-effect tools | Create `src/tools/<tool_name>.py` per tool, each wrapped with `hitl.checkpoint(...)`; register on the relevant worker |
| 5. HITL gates | `src/accelerator_baseline/hitl.py` — rules per tool + confidence threshold |
| 6. Constraints | `infra/main.parameters.json` + `accelerator.yaml.controls.*` |
| 3+7. Success criteria → acceptance | `evals/quality/golden_cases.jsonl` — create 5 skeleton cases with `acceptance_met` assertions tied to thresholds |
| 6. RAI risks | `evals/redteam/` — add one case per risk |
| 4. KPIs | `src/accelerator_baseline/telemetry.py` — register each named KPI event with the declared type; `infra/dashboards/roi-kpis.json` — add a chart per KPI |
| Engagement identity | `accelerator.yaml.solution.name` = slug of customer |

## Worker agent allocation (supervisor-routing only)
For each "job to be done" implied by section 5, decide which worker agent owns it. Defaults (flagship = sales research & outreach):
- **account_researcher** — external research on accounts/companies/people
- **icp_fit_analyst** — scores against ICP / segmentation rules
- **competitive_context** — rival landscape + positioning cues
- **outreach_personalizer** — drafts tailored outreach copy

If the brief's section 5 implies a capability none of these covers (e.g., "tax calculation"), propose adding a new worker via `/add-worker-agent`. Do NOT silently repurpose an existing worker.

## After scaffolding
1. Run `scripts/accelerator-lint.py` locally and paste the output to the partner.
2. If anything is red, fix it or surface it explicitly (don't hide failures).
3. Suggest next command: `azd up` to provision dev env, or `git commit && gh pr create` to trigger CI gates.

## Guardrails
- NEVER write Foundry agent system instructions in code. Those live in the Foundry portal; prompts in `prompt.py` are request-builders.
- NEVER weaken HITL, telemetry, evals, or content-filter controls to fit the brief. If the brief implies they should be weakened, flag to the partner — don't comply.
- Keep all edits consistent with `.github/copilot-instructions.md`.
- If the brief demands a stack other than Agent Framework + Foundry, STOP and escalate to the partner. This template doesn't support alternative stacks.

## Output
Summarize for the partner as a table: file changed, reason (which brief section drove it), whether it needs further human authoring (e.g., golden cases, retrieval connector credentials).
