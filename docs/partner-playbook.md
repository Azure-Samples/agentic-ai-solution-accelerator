# Partner playbook — end-to-end delivery motion

This playbook is the narrative companion to the `/delivery-guide` chatmode. It
is written for a **Microsoft partner delivery lead** running an engagement from
SOW to production handover using this accelerator. It explains **why** the
motion is shaped this way and **what "done" looks like** at each stage.

> See [Orientation → Precedence rules](getting-started/index.md#precedence-when-docs-conflict) for how this playbook relates to Quickstart, Setup, and the chatmodes.

---

## The motion, in one picture

```
discover ──► scaffold ──► provision ──► iterate ──► UAT ──► handover ──► measure
   (1)         (2)          (3)          (4)        (5)        (6)          (7)
   │           │            │            │          │          │            │
   │           │            │            │          │          │            └─ monthly KPI review
   │           │            │            │          │          └─ alerting on App Insights KPI events
   │           │            │            │          └─ acceptance thresholds in accelerator.yaml
   │           │            │            └─ PR-gated: lint + quality evals + redteam
   │           │            └─ azd up against a GitHub Environment (per deploy/environments.yaml)
   │           └─ /scaffold-from-brief drives src/, infra/, evals/, telemetry, dashboards
   └─ /discover-scenario produces docs/discovery/solution-brief.md + updates accelerator.yaml
```

Stages **1–2** are partner-facing ("co-build with the customer in real time"). Stages
**3–7** are engineering execution with the customer's Azure tenant in the loop.

---

## What the accelerator gives you vs. what you still own

This matters for scoping the SOW honestly.

| Concern                      | In the accelerator                                                                 | Partner owns                                        |
|------------------------------|-------------------------------------------------------------------------------------|-----------------------------------------------------|
| Discovery structure          | `/discover-scenario` chatmode + `docs/discovery/solution-brief.md` template         | Customer workshop facilitation, stakeholder map     |
| Scenario scaffold            | `/scaffold-from-brief` + `scripts/scaffold-scenario.py` + `scripts/scaffold-agent.py` | Scenario-specific prompts, tools, grounding sources |
| Infra                        | `infra/` (AVM-based) + `azure.yaml` + `deploy/environments.yaml`                     | Customer network / private-link overlay if required |
| CI / CD                      | `.github/workflows/{deploy,evals,lint}.yml` + `scripts/accelerator-lint.py`         | Branch protection, required reviewers               |
| Quality + safety evals       | `evals/quality/`, `evals/redteam/`                                                  | Customer golden cases, customer-specific redteam    |
| Agent definitions            | Bootstrap script + agent-spec docs (`docs/agent-specs/`)                            | Foundry portal instructions + tool attachment       |
| Telemetry baseline           | `src/accelerator_baseline/` (telemetry / HITL / killswitch / cost / evals helpers)  | Customer dashboards, alerting thresholds            |
| Landing-zone overlay         | `infra/avm-reference/` + `infra/modules/` (Tier 2 `avm`) and `infra/alz-overlay/` (Tier 3 `alz-integrated`) | Customer ALZ alignment, change control              |
| End-user / app-level auth    | Service-to-service Managed Identity everywhere (Foundry, Search, Key Vault all Entra-only, no keys); HTTPS-only ingress | **Who can call the API / load the UI** — Entra Easy Auth on Container Apps, App Gateway + WAF, or Front Door. The shipped API has no end-user auth dependency. |
| State persistence            | **Nothing.** `/research/stream` is in-memory per request; no datastore in `infra/`.                                       | Cosmos / Postgres / Redis / browser IndexedDB if the customer UX needs run history, multi-user separation, or durable HITL state. |
| HITL approval surface        | The **contract**: `HITL_POLICY` constant + `checkpoint(...)` call + lint enforcement + `tool.hitl_*` events + `HITL_DEV_MODE=1` stub for labs/evals | The **production approver** — Logic Apps, Teams adaptive card, ServiceNow, email — that `HITL_APPROVER_ENDPOINT` points at. The accelerator does not ship an approval UI. |
| Customer-facing UI           | Reference frontend at `patterns/sales-research-frontend/` — plain React + Vite + TypeScript, deployable to Azure Static Web Apps. Proves the SSE wiring. | UX, branding, design system, run history, auth flow, HITL approval surface. Fork as a starter; the customer's real UX is the partner team's value-add. |
| SOW / commercial terms       | **Nothing**                                                                         | **You** — templates live in your partner practice   |
| Customer training material   | **Nothing shipped today.** The shipped partner-team self-paced walkthrough is `docs/enablement/hands-on-lab.md`; customer-facing training is partner-owned. | Role-based customer training, support ops |

**Call out explicitly in your SOW:** the accelerator is not a shipping product
for the customer. It is a template a partner team customizes, deploys, and
operates. The customer gets the deployed solution (their Azure, their data,
their branding) — not the template itself.

---

## Stage 1 — Discovery

**Where:** Customer workshop room (or Teams) for the conversation; **VS Code** (Copilot Chat sidebar) to drive `/discover-scenario` (and `/ingest-prd` if a PRD/BRD/spec exists). The brief lands in `docs/discovery/solution-brief.md` for review in the editor.

**Goal:** produce a complete `docs/discovery/solution-brief.md` and update
`accelerator.yaml` so the scaffolding step has everything it needs.

**How:** run `/discover-scenario` in GitHub Copilot Chat (or any chat-mode-aware
IDE). The chatmode walks you (or you + customer live) through 7
sections: business context, personas, measurable success criteria, ROI
hypothesis, solution shape, constraints/risks, acceptance evals.

> **Customer already provided a PRD / BRD / functional spec?** Run `/ingest-prd` first to pre-draft the brief from the source doc, then `/discover-scenario` enters gap-fill mode on the remaining `TBD`s. Full flow: [`docs/discovery/how-to-use.md`](discovery/how-to-use.md), "If the customer already provided a PRD / BRD / functional spec" section.

**What "good" looks like:**

- Every section filled — no `TBD` left by the time you exit the session
- Success criteria are **numeric** (baseline → target, with %)
- 3–6 concrete KPI event names picked — these become typed telemetry events
  in `src/accelerator_baseline/telemetry.py` and App Insights alerts later
- Solution pattern chosen: **supervisor-routing** (flagship default),
  **single-agent**, or **chat-with-actioning**
- RAI risks listed as 3–5 concrete statements — these become redteam cases

**What to push back on:**

- "We want it fast" → "What's the current time, and what does 'fast enough'
  mean to the executive sponsor?"
- "Just use AI Search" → walk through `docs/foundry-tool-catalog.md` to pick
  the right grounding tool (File Search vs Azure AI Search vs SharePoint vs
  Fabric — they each have different prereqs and auth stories)
- Missing HITL gates → "Which tool calls are irreversible? Those need approval
  thresholds, not just logging."

**Deliverable:** `docs/discovery/solution-brief.md` + edits to
`accelerator.yaml` (`solution.pattern`, `solution.hitl`,
`solution.data_residency`, `solution.identity`, `acceptance.*`, `kpis[].name`).

---

## Stage 2 — Scaffold

**Where:** VS Code throughout — Copilot Chat sidebar for `/scaffold-from-brief`, editor for the manual customizations (rewriting `prompt.py`, editing `accelerator.yaml`, authoring agent specs), integrated terminal for `python scripts/scaffold-scenario.py`, `accelerator-lint.py`, and `pytest`.

**Goal:** adapt the repo to the customer's scenario — a clean diff reviewers
can follow.

**How:** run `/scaffold-from-brief`. The chatmode is a thin wrapper over
`scripts/scaffold-scenario.py`; it drives the CLI and then walks you
through the customization steps below.

**What the CLI materializes automatically** (one command,
`python scripts/scaffold-scenario.py <scenario-id>`):

- `src/scenarios/<package>/{__init__,schema,workflow,retrieval}.py`
- `src/scenarios/<package>/agents/supervisor/{__init__,prompt,transform,validate}.py`
- `docs/agent-specs/accel-<scenario-id>-supervisor.md`
- `data/samples/<package>.json`
- A `scenario:` snippet printed to stdout to paste into
  `accelerator.yaml`

**Manual follow-ups after the CLI runs** (chatmode step 3):

- Paste the `scenario:` snippet into `accelerator.yaml` and re-sync
  `solution.*`, `acceptance.*`, and `kpis[]` from the brief
- Rewrite the supervisor's `prompt.py` intro for the scenario
- If the chosen pattern is not supervisor-routing, reshape `workflow.py` for
  `single-agent` or `chat-with-actioning`
- Edit `retrieval.py` to match the chosen grounding sources
- Create `src/tools/<tool_name>.py` per side-effect tool (each wrapped in
  `hitl.checkpoint(...)`)
- Register KPI events in `src/accelerator_baseline/telemetry.py` and add a
  chart per KPI in `infra/dashboards/roi-kpis.json`
- Replace flagship golden cases in `evals/quality/golden_cases.jsonl`
  (5+ for this scenario)
- Add a redteam case per RAI risk in `evals/redteam/cases.jsonl`
- Add additional worker agents with `/add-worker-agent` (or directly via
  `python scripts/scaffold-agent.py <agent_id> --scenario <scenario-id> --capability "<one-sentence capability>"`).
  Each new agent needs a matching `docs/agent-specs/<foundry_name>.md` spec;
  `src/bootstrap.py` picks them up at FastAPI startup on the next `azd up` / `azd deploy`.

**What "good" looks like:**

!!! tip "Authoring agent instructions"
    **Agent system instructions live in `docs/agent-specs/<foundry_name>.md` under `## Instructions`.** Edit those Markdown files, not Python — `src/bootstrap.py` syncs them verbatim to the Foundry portal at FastAPI startup on `azd up` / `azd deploy`. `prompt.py` is for per-request input only.

- `python scripts/accelerator-lint.py` passes with **0 blocking, 0 warning**
- `pytest tests/` passes (supervisor-DAG test stays green)
- Each `prompt.py` is a **per-request input builder only** — no system
  instructions inline. The agent's system instructions live in
  `docs/agent-specs/<foundry_name>.md` (see [agent-specs README](agent-specs/README.md))
  and `src/bootstrap.py` syncs them to Foundry on every deploy.
- Every worker agent has `transform.py` returning a normalized dict and
  `validate.py` enforcing the schema. Reject any PR that skips either step.

**If the pattern is single-agent or chat-with-actioning** instead of the
flagship supervisor pattern, use `/switch-to-variant` to swap in the
`patterns/single-agent/` or `patterns/chat-with-actioning/` scaffold.

**Deliverable:** a PR-sized diff with all new files named per the scenario
ID and the build still green.

---

## Stage 3 — Provision

**Where:** VS Code (Copilot Chat sidebar for `/configure-landing-zone` and `/deploy-to-env`; integrated terminal — signed into the customer's Azure tenant — for `azd env new` + `azd up` and the baseline eval chain); github.com → repo → Settings → Environments to confirm OIDC + secrets landed; Azure portal (portal.azure.com → resource group) to verify the deployed resources.

**Goal:** deploy the scaffolded solution to the customer's Azure against a
named environment.

**How:**

1. `/configure-landing-zone` to pick the Azure AI Landing Zone tier and
   update `accelerator.yaml` + `infra/` accordingly. The chatmode covers
   three tiers:
   - **Tier 1 — `standalone`** (default; pilot / SMB greenfield / partner
     self-host): public endpoints, minimal infra.
   - **Tier 2 — `avm`** (customer has a CCoE mandate for private endpoints
     + CAF guardrails on day one): private-link + AVM-shaped modules under
     `infra/modules/` and `infra/avm-reference/`.
   - **Tier 3 — `alz-integrated`** (customer already has an ALZ — hub vNet,
     shared private DNS zones, policy assignments): wires the overlay in
     `infra/alz-overlay/` and enforces the `tier3InputGuard` in
     `infra/main.bicep`.
2. `/deploy-to-env <env-name>` to register a new GitHub Environment entry in
   `deploy/environments.yaml` and scaffold the required secrets / variables
   per the "Required GitHub secrets and variables" section of `docs/getting-started/setup-and-prereqs.md`.
3. From the customer's deployment-owner machine: `azd env new <customer-short-name>-dev`
   (e.g., `azd env new contoso-dev`) then `azd up`. First deploy takes ~15 min on a clean subscription. The
   `azd` hooks in `azure.yaml` run automatically as part of `azd up`:
   - `preprovision` → none (Bicep `loadYamlContent` parses `accelerator.yaml -> models[]` at compile time)
   - `postprovision` → none. Foundry agent create/update **and**
     AI Search index seeding both run inside the Container App at FastAPI startup via `src/bootstrap.py` (creates/verifies Foundry agents declared in
     `accelerator.yaml` + seeds every index declared in
     `scenario.retrieval.indexes[]`; the flagship scenario ships one
     `accounts` index, scaffolded scenarios declare their own)
4. Smoke-test the deployed endpoint — either the container URL or the SDK
   path in `src/main.py`, depending on scenario shape.
5. Confirm each Foundry agent appears in the portal with the placeholder
   instructions ready for editing. Restart the Container App revision (Container Apps -> Revisions -> Restart) or
   rerun `azd deploy` for recovery / troubleshooting — normal
   `azd up` cycles handle both.
6. **Establish the acceptance baseline** before exiting this stage. Run the full chain against the dev environment:

   ```bash
   python evals/quality/run.py --api-url <api-url>
   python evals/redteam/run.py --api-url <api-url>
   python scripts/enforce-acceptance.py
   ```

   The numbers are the engagement's known-good starting point. Every PR in Stage 4 has to clear this same bar — capture the output (`> baseline.txt` in the customer fork is enough) so the team has a reference when later changes move a number. If a threshold fails on the unmodified flagship, fix the deploy first (quotas, model region, grounding seed) before scaffolding scenario logic.

**What "good" looks like:**

- `infra/main.bicep` tags every resource with `azd-env-name` and
  `workload=<scenarioId>-accelerator` (wired from `scenarioId` param). If
  the customer needs additional tags (e.g. `engagement`, `costcenter`), add
  them to the `tags` object in `infra/main.bicep` — they do **not**
  propagate automatically from GitHub Environment variables today.
- Managed Identity on the Container App has the RBAC pairs documented in
  `docs/foundry-tool-catalog.md` for the tools this scenario uses.
- `APPLICATIONINSIGHTS_CONNECTION_STRING` is populated in the container's
  env (wired by `infra/modules/container-app.bicep`). Key Vault is
  referenced via RBAC + MI, not via a `KEY_VAULT_URI` env var; secrets are
  resolved at runtime by the SDK.
- `infra/alz-overlay/` guard passes if Tier 3 is enabled (`tier3InputGuard`
  in `infra/main.bicep` fails fast on missing inputs).

**If `azd up` fails:** first place to look is `docs/getting-started/setup-and-prereqs.md`
("Troubleshooting — top 5"). The most common failures are model-quota (wrong region),
OIDC (federated credentials not wired), and AI Search role assignment (needs
**Search Index Data Contributor** + **Search Service Contributor**, not
"Data Reader").

---

## Stage 4 — Iterate

**Where:** VS Code (Copilot Chat sidebar for prompt / tool / grounding edits and `/explain-change` preflights; integrated terminal for `git push`); github.com → repo → Pull requests / Actions to watch the four CI gates; Azure portal → App Insights for latency and KPI signals between PRs.

**Goal:** move the agent quality from "it runs" to "it meets acceptance."

**How:** partner refines prompts, tools, and grounding via Copilot Chat
inside the repo. Every change is a PR. CI runs four gates, all of
which must pass before merge:

- `scripts/accelerator-lint.py` — ~30 deterministic policy checks (AST-only,
  fast); see the `acceptance` section of `accelerator.yaml` for the policy set
- `evals/quality/run.py` — quality evals against golden cases
- `evals/redteam/run.py` — safety evals against the scenario's RAI cases
- `build + type check` — backend build and typing gate wired in
  `.github/workflows/deploy.yml`

**Where agent instructions live:** `docs/agent-specs/<foundry_name>.md` is
the **authoring source of truth**; `src/bootstrap.py` syncs the spec verbatim
to the Foundry portal at FastAPI startup on every `azd up` / `azd deploy`.
Treat the repo as the audit trail — every PR that edits a `prompt.py`, an
agent spec, a tool, or an acceptance threshold is the durable record. The
`/explain-change` chatmode is a **read-only CI preflight** — it tells you
which lint rules and evals will fire for the current diff; it does not write
changelogs.

**What "good" looks like:**

- Golden-case count > 20 by end of stage — `evals/quality/golden_cases.jsonl`
- Redteam passes on every PR — no deferred exceptions
- Cost per call trending toward the acceptance target (instrument via
  `src/accelerator_baseline/cost.py`)
- P50 / P95 latency visible in App Insights KPI events
- **At least one irreversible HITL tool exercised end-to-end before exiting Stage 4** — trigger a tool call that hits `hitl.checkpoint(...)`, the approver endpoint receives the request, the approver approves it, the tool executes, and the redteam case for that tool passes. UAT is not the place to discover that the approval flow is mis-wired; surface it here.

**When a worker is underperforming:** add a new case to `golden_cases.jsonl`
showing the failure, then fix the prompt / tool in a PR. Close the loop:
the case stays green or the PR blocks.

**Building the customer-facing UI:** the accelerator API is headless. Start
from [`patterns/sales-research-frontend/`](../patterns/sales-research-frontend/README.md)
— a minimal React + Vite + TypeScript starter that consumes `/research/stream`
and deploys to Azure Static Web Apps. Fork it as the baseline for your
customer's UX work; auth, branding, and any HITL approval surfaces are
partner-wired on top.

---

## Stage 5 — UAT

**Where:** Customer-facing sessions (browser → deployed UI for the customer's golden cases); VS Code (editor to add each customer case to `evals/quality/golden_cases.jsonl`, integrated terminal to re-run the eval chain); Azure portal → App Insights for the dashboards the sponsor walks through at sign-off.

**Goal:** customer accepts the solution against their own bar.

**How:** customer runs their golden cases on the deployed dev environment.
Partner adds each customer case to `evals/quality/golden_cases.jsonl` so it's
permanently regression-protected. The pass bar is
`accelerator.yaml.acceptance.*` — quality threshold, groundedness threshold,
safety pass, P50/P95 latency, cost per call.

**What "good" looks like:**

- Customer signs off against the acceptance thresholds — not against vibes
- HITL exercised end-to-end for at least one irreversible tool (e.g., CRM
  write, email send). **The accelerator does not ship a HITL approval UI:**
  the flagship HITL pattern (`docs/patterns/rai/README.md`, "Principle 3") is
  a partner-wired approval flow (Logic Apps, Teams adaptive card, ticketing
  system) that the tool blocks on until the approver endpoint
  returns. `src/accelerator_baseline/hitl.py` is the checkpoint contract.
- Killswitch flipped and verified — `src/accelerator_baseline/killswitch.py`
- Dashboards in App Insights show the KPI events the sponsor cares about

**When UAT fails:** it is almost always one of (1) grounding source coverage,
(2) prompt specificity, or (3) tool guard strictness. The delivery-guide
chatmode has a triage tree for each.

---

## Stage 6 — Production handover

**Where:** VS Code (Copilot Chat sidebar for `/deploy-to-env <customer-short-name>-prod`; integrated terminal for `azd env new` + `azd up` against prod; editor to fill in `docs/handover/handover-packet-template.md`); Azure portal → App Insights for alert wiring; live customer ops handover meeting (Teams + screen share) to walk the packet, runbook, killswitch, and approvers.

**Goal:** move the solution to the customer's production environment and
hand day-2 operations over.

**How:**

1. `/deploy-to-env <customer-short-name>-prod` (e.g., `contoso-prod`) to register the prod environment
2. `azd env new <customer-short-name>-prod`; `azd up` in prod — the `postprovision`
   startup bootstrap (`src/bootstrap.py`) re-runs Foundry agent create/update and AI Search seeding automatically
   against the prod project + search service
3. Wire App Insights alerting on the KPIs the engagement committed to
   in `accelerator.yaml.kpis[]` (customer-owned — `kpis[]` carries
   `{name, type, baseline, target}` metadata only; the matching telemetry
   event per KPI is wired in scenario code, and neither
   alerts nor dashboards beyond `infra/dashboards/roi-kpis.json` are
   auto-created)
4. Capture the handover artifacts — deployment URL, alert configuration,
   the HITL approver endpoint URL + runbook, killswitch procedure,
   and the archived `docs/discovery/solution-brief.md` copy

**Handover to whom:** the customer's internal owner per the SOW. If the
partner is retaining operations, skip to stage 7. If the customer's ops
team is taking over, share `docs/customer-runbook.md` — the shipped
day-2 runbook covering monitoring, killswitch, evals re-run, model swap,
secret rotation, incident response, and scaling. Add your engagement-specific
handover notes on top using [`docs/handover/handover-packet-template.md`](handover/handover-packet-template.md)
(endpoint URLs, HITL approver runbook, alert rules, killswitch, rollback
path, customer-specific deviations from shipped defaults, SLAs, contacts).

**What "good" looks like:**

- Zero manual steps outside the documented scripts — anything that isn't in
  a script or chatmode is a risk item in the handover
- Customer can repro `azd up` from scratch against a new env without
  partner assistance
- The handover packet lists owner, SLA, alerting, and rollback — no
  implicit knowledge

---

## Stage 7 — Measure

**Where:** Azure portal → App Insights → Logs (the KPI events the scenario emits are the source of truth); customer monthly value-review meeting to walk the deck.

**Goal:** prove value monthly against the KPIs agreed in stage 1.

**How:** run the value review against `accelerator.yaml.kpis`. The App
Insights events the scenario emits are the **only** numbers that count —
no spreadsheets, no screenshots of runs.

**What "good" looks like:**

- Monthly value-review deck populated from App Insights queries, not from
  memory
- At least one KPI moved from baseline toward target within 30 days of go-live
- Feedback captured back to Microsoft in this repo's Issues — both what
  worked and what didn't. The accelerator improves only when partner
  teams file issues.

---

## Chatmodes and scripts at a glance

| When you need to…                            | Use                                                                  |
|----------------------------------------------|----------------------------------------------------------------------|
| Run structured discovery                     | `/discover-scenario`                                                 |
| Adapt the repo to the brief                  | `/scaffold-from-brief`                                               |
| Add a worker agent post-scaffold             | `/add-worker-agent`                                                  |
| Add a tool (local Python or Foundry)         | `/add-tool`                                                          |
| Swap from flagship to a variant pattern      | `/switch-to-variant`                                                 |
| Choose landing-zone tier / reconfigure infra | `/configure-landing-zone`                                            |
| Register a new GitHub Environment            | `/deploy-to-env`                                                     |
| Preflight the current diff / see which CI checks will fire | `/explain-change`                                                    |
| Full engagement companion                    | `/delivery-guide`                                                    |
| Scaffold a scenario from the CLI             | `python scripts/scaffold-scenario.py <id>`                           |
| Scaffold an agent from the CLI               | `python scripts/scaffold-agent.py <agent_id> --scenario <scenario-id> --capability "<one-liner>"` |
| Lint the repo against policy                 | `python scripts/accelerator-lint.py`                                 |
| Create / update Foundry agents               | restart the Container App revision (`azd deploy` or portal)         |
| Seed the AI Search index                     | restart the Container App revision (`azd deploy` or portal)         |
| Check SDK pin freshness                      | `python scripts/ga-sdk-freshness.py`                                 |
| Enforce acceptance thresholds                | `python scripts/enforce-acceptance.py`                               |

These scripts are mostly Python / Azure-SDK-based; a few utility scripts
(e.g., `explain-change.py`) shell out to
standard developer tooling (`git`, `azd`) — already installed if you
followed the "Prerequisites" section of `docs/getting-started/setup-and-prereqs.md`.

---

## Escalation and feedback

- Technical issues with the accelerator template → file a GitHub Issue on this
  repo
- Security issues → see `SECURITY.md`
- Guidance on Foundry tool choices that aren't clearly covered in
  `docs/foundry-tool-catalog.md` → file an Issue with the engagement's
  `solution.pattern` and the tool under consideration
- Engagement commercial questions → your partner practice, not this repo

---

## What this playbook is NOT

- A replacement for Microsoft Learn. Every Foundry / Azure detail in this
  accelerator has an authoritative Learn page — always check it when pricing,
  regions, or GA/preview status matter.
- A replacement for your partner practice's SOW, rate card, or staffing model.
- A promise that `azd up` will succeed on a subscription with wrong quotas,
  missing OIDC, or a conflicting ALZ policy. Stage 3 is iterative; the
  getting-started troubleshooting matrix is where failures go to die.
- A substitute for customer-specific training. The shipped partner-team
  self-paced walkthrough lives at `docs/enablement/hands-on-lab.md` —
  it gets partner engineers comfortable with the template, not a
  customer's end users. Customer end-user training is partner-owned
  either way.
