# Agent specs — source of truth for initial Foundry agent creation

`scripts/foundry-bootstrap.py` reads one Markdown file per agent from this
directory and creates or updates the corresponding agent in the Foundry
project at `azd up` / `azd postprovision` time.

## File format

```markdown
# Agent: <agent_name>

**Model:** <deployment_name>    (e.g. gpt-5.2)
**Reference:** <SMB Agent Hub equivalent, if any>

## Instructions
<system instructions the agent runs with>
```

## Important

These files are ONLY used at bootstrap time. After `azd up` completes, agent
instructions live in the **Foundry portal** — that is the runtime source of
truth. The `.md` files here remain as a reproducible starting point so a
partner who clones the template gets a working system immediately.

Do NOT reference these `.md` files at runtime. Do NOT import from them.

## Flagship agents (5)

| Agent name                             | Reference (SMB Agent Hub)                |
|----------------------------------------|------------------------------------------|
| `accel-sales-research-supervisor`      | `supervisor`                             |
| `accel-account-planner`                | `account_planner`                        |
| `accel-icp-fit-analyst`                | `nnr_agent` + `portfolio_planner`        |
| `accel-competitive-context`            | `compete_advisor` + `cloud_footprint`    |
| `accel-outreach-personalizer`          | (loose) `content_curator` personalization |
