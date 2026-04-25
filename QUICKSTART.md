# QUICKSTART — Deploy an Agentic AI Solution in ~15 minutes

> Partner's 5-step path from "new customer meeting" to "working agent in customer Azure."

> **Before you start:** Step 5 authenticates against the customer's Azure tenant (`az login --tenant <customer-tenant-id>` + `azd up`), so confirm two things first — you have the rights to create resources in that tenant, and the customer has approved the expected `azd up` cost. Re-read this note before Step 5; the rest of the steps are local.

---

## Before Step 1 — read these if any apply to you

- **New here?** This is a Microsoft-published template repo partners fork per customer engagement to deliver an agentic AI solution on **Azure AI Foundry + Microsoft Agent Framework**. Skim [Orientation](docs/getting-started/index.md) once.
- **First time on this accelerator?** Strongly recommended to complete [`docs/enablement/hands-on-lab.md`](docs/enablement/hands-on-lab.md) in a sandbox subscription **before** your first customer-facing deployment. The happy path below assumes you've run it once end-to-end.
- **Engineer joining after discovery is complete?** Jump straight to [Step 3 — Scaffold the solution from the brief](#step-3--scaffold-the-solution-from-the-brief).
- **Scoping an engagement or running the discovery workshop?** Read [`docs/partner-playbook.md`](docs/partner-playbook.md) for the full 7-stage motion; this QUICKSTART is the mechanics summary.
- **Customer already provided a PRD / BRD / functional spec?** Run `/ingest-prd` before `/discover-scenario` to pre-draft the brief — full flow: [`docs/discovery/how-to-use.md`](docs/discovery/how-to-use.md).

---

## Step 1 — Clone the template

```bash
# Replace <customer-short-name> with your customer's short name (e.g., contoso, fabrikam)
gh repo create <customer-short-name>-agents --template Azure-Samples/agentic-ai-solution-accelerator --private
cd <customer-short-name>-agents
code .
```

VS Code opens with Copilot already configured via `.github/copilot-instructions.md`. Copilot now knows the hard rules:

- Agent Framework + Foundry only
- DefaultAzureCredential only — no keys
- HITL required for every side-effect tool call
- PR evals gate merges; a post-deploy regression suite guards `main`
- Content filters configured via IaC, not the portal

---

## Step 2 — Run the discovery workshop

> **Full discovery sequence** (canvas → facilitation guide → workbook → `/discover-scenario` → ROI calc, plus the `/ingest-prd` branch when a PRD/BRD/spec exists) lives in [`docs/discovery/how-to-use.md`](docs/discovery/how-to-use.md). **Read it before running the chatmode** — the five artifacts have a fixed order and the workshop-readiness gate sits upstream.

In Copilot Chat:

```
/discover-scenario
```

Copilot interviews you — either after a customer workshop or live in the room — and writes `docs/discovery/solution-brief.md`. The brief captures:

- Business context, sponsor, problem statement
- Users, journeys, success criteria
- **ROI hypothesis** (baseline cost, target savings, payback, KPIs to instrument)
- Solution shape (single-agent · supervisor · chat-with-actioning)
- Constraints (residency, identity, compliance)
- Acceptance evals (quality, groundedness, safety, latency, cost)

The brief is the **single source of truth** for the engagement. Every downstream artifact derives from it.

---

## Step 3 — Scaffold the solution from the brief

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

Before `azd up`, make two decisions and wire one piece of OIDC plumbing. These take 5–15 minutes and prevent the most common first-deploy failures.

```
/configure-landing-zone     # pick standalone | avm | alz-integrated; updates accelerator.yaml + infra/
/deploy-to-env <env-name>   # e.g., dev, uat, prod — registers the GitHub Environment, wires OIDC, scopes secrets
```

`/configure-landing-zone` walks you through the tier decision (Tier 1 standalone for pilots / SMB; Tier 2 `avm` for private endpoints; Tier 3 `alz-integrated` for an existing customer ALZ hub). `/deploy-to-env` adds the env to `deploy/environments.yaml`, creates the matching GitHub Environment, and wires the OIDC federated credential so CI can deploy without a service-principal secret. Skip this and your first PR will fail auth.

---

## Step 5 — Provision + deploy to customer's Azure

> **Authoring agent instructions.** Agent system instructions live in
> `docs/agent-specs/<agent>.md` under the `## Instructions` heading —
> edit those Markdown files, not Python. On `azd up`,
> `scripts/foundry-bootstrap.py` syncs each spec verbatim to the
> Foundry portal. `prompt.py` is for *per-request* input construction
> only.

```bash
# Replace <customer-tenant-id> with the customer's Azure tenant GUID, and
# <customer-short-name> with the customer's short name (e.g., contoso)
az login --tenant <customer-tenant-id>
azd auth login
azd env new <customer-short-name>-dev
azd up
```

`azd up` provisions: Azure AI Foundry · Azure AI Search · Key Vault · Container Apps · Application Insights · Managed Identity. No keys. Content filters via IaC. Dashboards pre-wired to the brief's KPI events.

~10–15 minutes; URL of the deployed agent prints at the end.

---

## Step 6 — Iterate with Copilot; ship through CI gates

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

## Step 7 — Ship a UI

Steps 1–6 give you a working SSE API. To put a UI in front of it for your
customer, fork the [frontend pattern](patterns/sales-research-frontend/README.md) —
a minimal React + Vite + TypeScript starter that consumes `/research/stream`
and is deployable to Azure Static Web Apps. It's reference material, not a
finished product: the customer's real UX is the partner's value-add.

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
