# Agent specs — source of truth for initial Foundry agent creation

## Flagship agents at a glance

The flagship scenario (Sales Research & Personalised Outreach) ships with five Foundry agents. Detailed system instructions live in the per-agent files in this directory; a partner-facing summary first:

| Agent | Role | Output | HITL / tool posture |
|---|---|---|---|
| [`accel-sales-research-supervisor`](accel-sales-research-supervisor.md) | Orchestrator — routes the scenario across the four workers and composes their outputs | Composed account research + outreach payload | No tools of its own; downstream tool calls inherit each worker's HITL policy |
| [`accel-account-planner`](accel-account-planner.md) | Builds the account brief: company, segment, signals, decision-makers | Structured account profile (citations required) | Read-only retrieval; no HITL |
| [`accel-icp-fit-analyst`](accel-icp-fit-analyst.md) | Scores ICP fit + maps to portfolio plays (NNR + portfolio-planner equivalent) | Fit score + recommended play | Read-only retrieval; no HITL |
| [`accel-competitive-context`](accel-competitive-context.md) | Surfaces competitive context + cloud footprint (compete-advisor + cloud-footprint equivalent) | Competitive notes + footprint signals | Read-only retrieval; no HITL |
| [`accel-outreach-personalizer`](accel-outreach-personalizer.md) | Drafts the personalised outreach + invokes side-effect tools (CRM write, send email) | Outreach copy + tool-call results | **HITL required on every side-effect tool** (`crm_write_contact`, `send_email` use `HITL_POLICY = "always"`) |

Use the per-agent files below for the actual system instructions; everything else on this page is bootstrap mechanics.

---

## Bootstrap mechanics

`scripts/foundry-bootstrap.py` reads one Markdown file per agent from this
directory and creates or updates the corresponding agent in the Foundry
project at `azd up` / `azd postprovision` time.

## File format

```markdown
# Agent: <agent_name>

**Reference:** <SMB Agent Hub equivalent, if any>

## Instructions
<system instructions the agent runs with>
```

The model deployment is NOT declared here — every agent runs against the
single model deployed by `infra/modules/foundry.bicep` (captured in the
`AZURE_AI_FOUNDRY_MODEL` output and read by `scripts/foundry-bootstrap.py`).
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

| Agent name                             | Agent Hub reference (partner set)        |
|----------------------------------------|------------------------------------------|
| `accel-sales-research-supervisor`      | none (orchestration primitive)           |
| `accel-account-planner`                | `account_planner`                        |
| `accel-icp-fit-analyst`                | `nnr_agent` + `portfolio_planner`        |
| `accel-competitive-context`            | `compete_advisor` + `cloud_footprint`    |
| `accel-outreach-personalizer`          | none (scenario-specific side-effect worker) |

The partner-cited reference set is: Account Planner, Portfolio Planner,
Zero Trust, Cloud Footprint, Compete Advisor, NNR Agent. Zero Trust is not
used by this flagship (different scenario); it remains a candidate for a
future pattern variant.
