# QUICKSTART — Deploy an Agentic AI Solution in ~15 minutes

> **Recommended path:** Use the [partner walkthrough](docs/start/index.md) — *Get ready* (one-time) + *Deliver to a customer* (seven steps per engagement). This file is the printable cheat-sheet version of the per-customer steps; keep it open as a reference during an engagement.

> **First time on this accelerator?** Do *Get ready* in the walkthrough first — [1. Get oriented](docs/start/ready/01-get-oriented.md) → [2. Set up your machine](docs/start/ready/02-set-up-your-machine.md) → [3. Rehearse in a sandbox](docs/start/ready/03-rehearse-in-a-sandbox.md) — **before** Step 1 below.

> **Before Step 5:** You'll authenticate against the customer's Azure tenant (`az login --tenant <customer-tenant-id>` + `azd up`). Confirm you have the rights to create resources there and the customer has approved the expected `azd up` cost.

> **Joining mid-engagement?** If discovery is already complete, jump to [Step 3 — Scaffold from the brief](#step-3--scaffold-the-solution-from-the-brief). If a brief doesn't yet exist, hand back to the delivery lead — discovery is owned in the [Discovery kit](docs/discovery/how-to-use.md), not here.

---

## Where you'll work

You'll move between three places as you go through this guide. Every step below opens with a **Where** line so you know which one to be in.

| Where | What you do there | How to open it |
|---|---|---|
| **VS Code** | Run all repo-local commands in the integrated terminal (`` Ctrl+` ``), edit files (`accelerator.yaml`, agent specs, `solution-brief.md`), and talk to GitHub Copilot Chat in the right sidebar (💬 icon or `Ctrl+Alt+I`). Pick a custom agent from the **agents dropdown** at the top of the Chat panel — `/discover-scenario`, `/scaffold-from-brief`, `/define-grounding`, `/implement-workers`, `/configure-landing-zone`, `/deploy-to-env`, `/add-tool`, `/explain-change`, `/delivery-guide`, etc. VS Code auto-discovers files under `.github/agents/` (no workspace setting required) — **trust the workspace** when prompted, otherwise the dropdown stays empty. | After cloning, `code .` from any shell opens it on the repo |
| **GitHub web (github.com)** | Configure repo Settings → Environments (secrets + OIDC), open PRs, watch Actions runs | Your browser, on the cloned repo |
| **Azure portal (portal.azure.com)** | Inspect the resource group, Foundry quota, Application Insights logs and dashboards | Your browser, signed into the customer's tenant |

---

## Step 1 — Clone the template

**Where:** VS Code. Run the `gh` commands from the integrated terminal (`` Ctrl+` ``), then load the cloned folder into your current VS Code window via **File → Open Folder** (`Ctrl+K Ctrl+O` on Windows/Linux, `Cmd+K Cmd+O` on macOS) and pick the new `<customer-short-name>-agents` folder. (If you're running from a standalone shell instead, `code <customer-short-name>-agents` opens it in a fresh window.)

```bash
# Replace <customer-short-name> with your customer's short name (e.g., contoso, fabrikam)
gh repo create <customer-short-name>-agents --template Azure-Samples/agentic-ai-solution-accelerator --private --clone
cd <customer-short-name>-agents
```

VS Code opens with Copilot already configured via `.github/copilot-instructions.md`. Copilot now knows the hard rules:

- Agent Framework + Foundry only
- DefaultAzureCredential only — no keys
- HITL required for every side-effect tool call
- PR evals gate merges; a post-deploy regression suite guards `main`
- Content filters configured via IaC, not the portal

---

## Step 2 — Run the discovery workshop

**Where:** VS Code (Copilot Chat sidebar). The use-case canvas and discovery workbook are partner-fillable templates you handle in your usual editor before this step.

> **The full discovery sequence** — canvas → facilitation guide → workbook → `/discover-scenario` → ROI calc, plus the `/ingest-prd` branch for customers who already have a PRD/BRD/spec — is owned by the [Discovery kit](docs/discovery/how-to-use.md). **Read it first** if you haven't run discovery on this accelerator before; the five artifacts have a fixed order and a workshop-readiness gate sits upstream.

In Copilot Chat:

```
/discover-scenario
```

Copilot interviews you (in a workshop or live in the room) and writes `docs/discovery/solution-brief.md`. The brief is the **single source of truth** for the engagement — every downstream artifact derives from it.

---

## Step 3 — Scaffold the solution from the brief

**Where:** VS Code (Copilot Chat sidebar). The chatmode writes files into the open repo; review the diff in VS Code's Source Control panel afterwards.

```
/scaffold-from-brief
```

Copilot reads the filled brief and customizes the repo. The **Lands in** column below shows paths for the flagship scenario (`sales-research`).

If you scaffold a new scenario via `python scripts/scaffold-scenario.py <scenario-id>` (e.g., `sales-research`, `customer-service`), substitute `<scenario-id>` for `sales_research` in the `src/scenarios/<...>/` paths. Everything outside `src/scenarios/` is scenario-agnostic and stays put.

| Brief field → | Lands in (flagship paths shown; `src/scenarios/<id>/` for custom scenarios) |
|---|---|
| Problem + persona | `src/scenarios/sales_research/agents/supervisor/prompt.py` system prompt |
| Solution shape | Keep flagship OR run `/switch-to-variant` for a walkthrough of re-authoring under `patterns/single-agent` or `patterns/chat-with-actioning` (manual re-authoring walkthroughs, not drop-ins) |
| Grounding sources | `src/retrieval/ai_search.py` (scenario-agnostic client) + scenario-specific index schema at `src/scenarios/sales_research/retrieval.py` + `infra/modules/ai-search.bicep` |
| Side-effect tools | New files under `src/tools/` with HITL scaffolding |
| HITL gates | `src/accelerator_baseline/hitl.py` rules |
| Constraints | `infra/main.parameters.json` + `accelerator.yaml` |
| Success criteria | `evals/quality/golden_cases.jsonl` + CI gates |
| RAI risks | `evals/redteam/` custom adversarial cases |
| ROI KPIs | `src/accelerator_baseline/telemetry.py` events + `infra/dashboards/roi-kpis.json` (panels are scenario-agnostic; rename the dashboard per engagement) |

Commit the scaffolded changes. CI lint now runs; it will flag anything missing.

---

## Step 4 — Preflight: landing zone + GitHub Environment

**Where:** VS Code (Copilot Chat sidebar) for both chatmodes. `/deploy-to-env` will also have you confirm settings on github.com → your repo → Settings → Environments at the end.

Before `azd up`, make two decisions and wire one piece of OIDC plumbing. These take 5–15 minutes and prevent the most common first-deploy failures.

```
/configure-landing-zone     # pick standalone | avm | alz-integrated; updates accelerator.yaml + infra/
/deploy-to-env <env-name>   # e.g., dev, uat, prod — registers the GitHub Environment, wires OIDC, scopes secrets
```

`/configure-landing-zone` walks you through the tier decision (Tier 1 standalone for pilots / SMB; Tier 2 `avm` for private endpoints; Tier 3 `alz-integrated` for an existing customer ALZ hub). `/deploy-to-env` adds the env to `deploy/environments.yaml`, creates the matching GitHub Environment, and wires the OIDC federated credential so CI can deploy without a service-principal secret. Skip this and your first PR will fail auth.

---

## Step 5 — Provision + deploy to customer's Azure

**Where:** VS Code's integrated terminal (`` Ctrl+` ``), signed into the customer's Azure tenant. The deployed API URL prints in the terminal at the end of `azd up` — keep it open; you'll reuse it in Step 6.

> **Authoring agent instructions.** Agent system instructions live in
> `docs/agent-specs/<agent>.md` under the `## Instructions` heading —
> edit those Markdown files, not Python. On `azd up`, the FastAPI
> startup bootstrap (`src/bootstrap.py`) syncs each spec verbatim to
> the Foundry portal once the Container App boots. `prompt.py` is for
> *per-request* input construction only.

```bash
# Replace <customer-tenant-id> with the customer's Azure tenant GUID, and
# <customer-short-name> with the customer's short name (e.g., contoso)
az login --tenant <customer-tenant-id>
azd auth login
azd env new <customer-short-name>-dev
azd up
```

`azd up` provisions: Microsoft Foundry · Azure AI Search · Key Vault · Container Apps · Application Insights · Managed Identity. No keys. Content filters via IaC. Dashboards pre-wired to the brief's KPI events.

~10–15 minutes; URL of the deployed agent prints at the end.

---

## Step 6 — Establish the acceptance baseline

**Where:** VS Code's integrated terminal (repo root). Use the same terminal session as Step 5 so the API URL is still on screen.

Before you start iterating, run the acceptance chain once against the freshly deployed flagship. The numbers it produces are the engagement's **known-good starting point**: every PR in Step 7 has to clear this same bar.

```bash
# Replace <api-url> with the URL azd up printed in Step 5
python evals/quality/run.py --api-url <api-url>
python evals/redteam/run.py --api-url <api-url>
python scripts/enforce-acceptance.py
```

`enforce-acceptance.py` reports pass / fail against every threshold in `accelerator.yaml.acceptance` (quality, groundedness, safety, P50/P95 latency, cost per call). If a threshold fails on the unmodified flagship, fix the deploy first — quotas, model region, or grounding seed are the usual culprits — before you start authoring scenario-specific changes.

Capture the output (a screenshot or `enforce-acceptance.py > baseline.txt` in the customer fork) so the team has a reference when later PRs move a number.

---

## Step 7 — Iterate with Copilot; ship through CI gates

**Where:** VS Code (Copilot Chat sidebar for the agent edits, integrated terminal for `git push`), then GitHub web (github.com → your repo → Pull requests / Actions) to watch CI.

In VS Code, just talk to Copilot:

> *"Add a tool to create a ticket in ServiceNow; it should require HITL for anything with priority high."*

Copilot follows `copilot-instructions.md` — creates `src/tools/servicenow_ticket.py` with HITL scaffolding, wires it, adds a unit test.

```bash
git checkout -b feat/servicenow-tool
git add -A && git commit -m "Add ServiceNow tool"
gh pr create
```

The PR triggers:
1. `scripts/accelerator-lint.py` (30 deterministic rules)
2. `evals/quality/` (must clear thresholds in `accelerator.yaml -> acceptance`)
3. `evals/redteam/` (XPIA + jailbreak must pass)
4. `build + type check`

Any red light blocks merge. Green = `azd deploy` against customer env.

---

## Step 8 — Ship a UI

**Where:** VS Code — edit the React + Vite + TypeScript starter under `patterns/sales-research-frontend/` in the editor; run `npm install` / `npm run dev` / `swa deploy` from the integrated terminal.

Steps 1–7 give you a working SSE API. To put a UI in front of it for your
customer, fork the [frontend pattern](patterns/sales-research-frontend/README.md) —
a minimal React + Vite + TypeScript starter that consumes `/research/stream`
and is deployable to Azure Static Web Apps. It's reference material, not a
finished product: the customer's real UX is the partner's value-add.

**Before customer-facing**, you also wire — none of which the accelerator ships: end-user auth (Easy Auth / App Gateway / Front Door), state persistence (Cosmos / Postgres / Redis), and the HITL approval surface (Logic Apps / Teams / ServiceNow that `HITL_APPROVER_ENDPOINT` resolves to). The full ownership boundary lives in [`docs/partner-playbook.md`](docs/partner-playbook.md#what-the-accelerator-gives-you-vs-what-you-still-own) — call it out in the SOW.

If your customer already has an internal portal or Power Platform surface,
the same pattern shows how to call the SSE endpoint from any client; lift
`src/services/researchClient.ts` and the `StreamEvent` types in
`src/types/research.ts` into their codebase.

---

## Need a different shape?

The variants below are **manual re-authoring walkthroughs** (documented in `patterns/<variant>/README.md`), not drop-in packages. Run `/switch-to-variant` for a guided walkthrough of re-authoring the scenario under `src/scenarios/<new-id>/`:

- **Simpler** than supervisor-routing? `/switch-to-variant` → pick `single-agent`.
- **Conversational** front-end? `/switch-to-variant` → pick `chat-with-actioning`.
- **Different business scenario?** See `docs/references/` for Customer Service and RFP Response walkthroughs.

## Need help?

- `docs/getting-started/setup-and-prereqs.md` — authoritative prereqs, secrets, troubleshooting
- `docs/discovery/SOLUTION-BRIEF-GUIDE.md` — how to run the workshop
- `docs/version-matrix.md` — known-good SDK pins
- `docs/agent-specs/README.md` — per-agent system instructions and bootstrap mechanics
- Issues in this repo — intake for feedback and new patterns
