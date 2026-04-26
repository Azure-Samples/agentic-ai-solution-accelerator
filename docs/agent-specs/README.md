# Agent specs — source of truth for initial Foundry agent creation

## Flagship agents at a glance

The flagship scenario (Sales Research & Personalised Outreach) ships with five Foundry agents. Detailed system instructions live in the per-agent files in this directory; a partner-facing summary first:

| Agent | Role | Output | HITL / tool posture |
|---|---|---|---|
| [`accel-sales-research-supervisor`](accel-sales-research-supervisor.md) | Orchestrator — routes the scenario across the four workers and composes their outputs | Composed account research + outreach payload | No tools of its own; downstream tool calls inherit each worker's HITL policy |
| [`accel-account-planner`](accel-account-planner.md) | Builds the account brief: company, segment, signals, decision-makers | Structured account profile (citations required) | Read-only retrieval; no HITL |
| [`accel-icp-fit-analyst`](accel-icp-fit-analyst.md) | Scores ICP fit + maps to a tier recommendation | Fit score + recommended play | Read-only retrieval; no HITL |
| [`accel-competitive-context`](accel-competitive-context.md) | Surfaces competitive context + cloud footprint signals | Competitive notes + footprint signals | Read-only retrieval; no HITL |
| [`accel-outreach-personalizer`](accel-outreach-personalizer.md) | Drafts the personalised outreach + invokes side-effect tools (CRM write, send email) | Outreach copy + tool-call results | **HITL required on every side-effect tool** (`crm_write_contact`, `send_email` use `HITL_POLICY = "always"`) |

Use the per-agent files below for the actual system instructions; everything else on this page is bootstrap mechanics.

---

## Bootstrap mechanics

`src/bootstrap.py` reads one Markdown file per agent from this
directory and creates or updates the corresponding agent in the Foundry
project at `azd up` / `azd postprovision` time.

## File format

```markdown
# Agent: <agent_name>

**Pattern:** <one-line description of what shape this agent fills>

## Instructions
<system instructions the agent runs with>
```

The model deployment is NOT declared here — every agent runs against the
single model deployed by `infra/modules/foundry.bicep` (captured in the
`AZURE_AI_FOUNDRY_MODEL` output and read by `src/bootstrap.py` at FastAPI startup).
This keeps infra as the source of truth and prevents specs drifting away
from what `azd up` actually provisions. The accelerator lint fails if any
spec file contains a `**Model:**` field.

## Important

These files are ONLY used at bootstrap time. After `azd up` completes, agent
instructions live in the **Foundry portal** — that is the runtime source of
truth. The `.md` files here remain as a reproducible starting point so a
partner who clones the template gets a working system immediately.

Do NOT reference these `.md` files at runtime. Do NOT import from them.

## Flagship agents (5)

The flagship ships one supervisor plus four workers. Each agent's
`.md` file in this directory is the source of truth for its
instructions; the table at the top of this page is the partner-facing
summary. Add new agents to a scaffolded scenario with
`python scripts/scaffold-agent.py` (writes a matching spec stub).
