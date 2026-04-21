# Agent specs — source of truth for initial Foundry agent creation

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
