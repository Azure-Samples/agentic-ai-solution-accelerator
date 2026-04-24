# Customer runbook — day-2 operations

This runbook is for the **customer's ops team** after the partner has
deployed the accelerator into the customer's Azure and handed off. It
covers the operations the customer owns: monitoring, killswitch, evals
re-run, model swap, incident response, cost tracking, and scaling.

The partner's engagement-specific handover packet (endpoint URLs,
HITL approver wiring, customer-specific alert rules, SLA details)
complements this runbook. When the two conflict, the partner's packet
wins — it describes the customer-specific wiring this generic runbook
cannot.

**Audience:** customer SRE / platform / AI-ops on-call. Assumes access
to the Azure subscription hosting the deployment, App Insights, Azure
AI Foundry, and (if the partner used the forked-template pattern) the
customer's GitHub fork.

**Not in scope here:**

- Commercial / SOW / SLA questions → partner delivery lead
- Redesigning the scenario or adding a new one → new engagement,
  back to `/discover-scenario` + `/scaffold-from-brief`
- Source-code changes to the accelerator template itself → upstream
  Issues; the customer's fork is the day-2 change surface

---

## What you inherited

At handover, the customer owns a deployed environment provisioned by
`azd up` against `infra/main.bicep` (resource-group scope). The
resource-group name is set by the partner during provisioning — see
the partner's handover notes for the exact value. Inside the group:

- **Foundry (AIServices) account + project** — hosts agent definitions
  and model deployment(s). Model deployment names come from
  `accelerator.yaml.models[]` via `scripts/sync-models-from-manifest.py`.
- **Azure AI Search** — index(es) declared in
  `accelerator.yaml → scenario.retrieval.indexes[]`. Seeded by
  `scripts/seed-search.py` in the `azd` postprovision hook.
- **Key Vault** — present for partner-added secrets, accessed via
  RBAC + Managed Identity.
- **Container App (API)** — runs the scenario workflow and exposes the
  endpoint. Env vars (`APPLICATIONINSIGHTS_CONNECTION_STRING`,
  `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_MODEL`,
  `AZURE_AI_SEARCH_ENDPOINT`) are set from Bicep outputs as plain env
  values — there are no Key Vault secret references wired by default.
- **User-assigned Managed Identity** — shared principal that holds RBAC
  on Foundry, Search, and Key Vault.
- **Application Insights + Log Analytics** — telemetry sink.

**Tier 3 (`landing_zone.mode: alz-integrated`) additions:**

- Private endpoints on Foundry / AI Search / Key Vault are created by
  the **workload modules** (`infra/modules/{foundry,ai-search,
  key-vault}.bicep`) when `enablePrivateLink = true`.
- `infra/alz-overlay/` is a separate subscription-scope deploy the
  platform team runs once to provision the spoke (vNet, workload
  subnet, peering to the hub). It **consumes** existing hub private
  DNS zone resource IDs supplied by the customer's CCoE and
  optionally creates vNet links from those zones to the spoke
  (controlled by `createDnsZoneLinks`). It does not create the hub
  zones themselves — those are hub-owned. Zone IDs and the subnet
  ID flow into `infra/main.bicep` via azd env vars.
- `tier3InputGuard` in `infra/main.bicep` fails provision fast if any
  of those env vars are missing; it does **not** monitor for
  post-deploy drift.

Everything above is redeployed idempotently by `azd up` against a
given commit. Rollback is `azd down --purge` + `azd up` at a prior
commit.

---

## 1. Monitoring

### Telemetry plane

Every workflow, worker, tool, and HITL checkpoint emits typed
OpenTelemetry events to Application Insights via the
`APPLICATIONINSIGHTS_CONNECTION_STRING` env var on the Container App.
Event definitions live in `src/accelerator_baseline/telemetry.py`.

**Events emitted by the shipped flagship today:**

| Event                   | Emitted from                                                | Fires when                                             |
|-------------------------|-------------------------------------------------------------|--------------------------------------------------------|
| `request.received`      | `src/scenarios/sales_research/workflow.py`                  | a request enters the scenario workflow                 |
| `supervisor.routed`     | `src/workflow/supervisor.py`                                | supervisor chose which workers to run                  |
| `worker.completed`      | `src/workflow/supervisor.py`                                | a worker returned successfully                         |
| `worker.skipped`        | `src/workflow/supervisor.py`                                | a worker skipped (e.g., dependency failed)             |
| `tool.executed`         | `src/tools/*.py`                                            | any tool (read-only or side-effect) executed           |
| `tool.hitl_approved`    | `src/accelerator_baseline/hitl.py`                          | human reviewer approved a tool call                    |
| `tool.hitl_rejected`    | `src/accelerator_baseline/hitl.py`                          | human reviewer rejected a tool call                    |
| `tool.hitl_misconfigured` | `src/accelerator_baseline/hitl.py`                        | production had no `HITL_APPROVER_ENDPOINT`             |
| `retrieval.returned`    | `src/retrieval/ai_search.py` + `src/scenarios/sales_research/workflow.py` | AI Search call completed; workflow also emits this with `ok=False` on exception |
| `response.returned`     | `src/main.py` + `src/scenarios/sales_research/workflow.py`  | workflow returned to caller (with `ok: true\|false`)   |

The registry also declares `tool.hitl_skipped` (emitted when a tool
call passes `policy="never"` into `checkpoint()`), but **both
side-effect tools shipped with the flagship (`crm_write_contact`,
`send_email`) use `HITL_POLICY = "always"`**, so this event does not
fire in the out-of-the-box flagship. A scenario whose tool code
explicitly passes `policy="never"` (typically aligned with
`accelerator.yaml.solution.hitl = none` for reversible actions) would
produce it.

**Registered but not emitted by the shipped flagship:**

- `aggregator.composed` — reserved for scenarios that compose worker
  outputs in an aggregator stage. The flagship doesn't use that
  pattern; a scenario that does must `emit_event` manually.
- `cost.call` — the emitter `record_call_cost(agent, UsageSample(…))`
  lives in `src/accelerator_baseline/cost.py` but is **not called from
  the flagship workflow by default**. Partners wire it into their
  Foundry call path when cost-per-call reporting is in scope.
- `eval.result` — emitted only if the partner wired the eval runner to
  push each case's result into App Insights (the shipped runners
  write to `results.jsonl` only).

The partner's handover packet should list which of these additional
events they wired, if any.

### Dashboard

`infra/dashboards/roi-kpis.json` is an Azure Monitor workbook **template**
(ARM JSON). It is **not auto-deployed**. To use it: Application Insights
→ Workbooks → New → Advanced editor → paste the JSON → Save.

It ships 5 panels. Which ones show data depends on what your partner
wired:

| Panel                               | Works out of the box? | Depends on                                  |
|-------------------------------------|-----------------------|---------------------------------------------|
| Successful responses per day        | Yes                   | `response.returned` (always emitted)        |
| HITL approval rate                  | Yes when HITL is in use | `tool.hitl_approved`, `tool.hitl_rejected` |
| P95 request latency                 | Yes                   | Container App request telemetry (`cloud_RoleName endswith 'api'`) |
| $ per call (estimated)              | **Only if partner wired `cost.call`** | `cost.call` events                |
| Groundedness eval score trend       | **Only if partner wired `eval.result`** | `eval.result` events          |

Only the latency panel filters by `cloud_RoleName` today. The event
panels query `customEvents` across the whole App Insights resource —
if the resource is shared with other workloads, add a
`cloud_RoleName` filter before operationalizing.

### Alerts

The accelerator **does not ship Azure Monitor alert rules** — you
wire them. Starting points (copy the KQL from the workbook):

- **Error-rate alert** — `response.returned` with
  `customDimensions.ok == 'false'` exceeding N% over 15 minutes
- **P95 latency alert** — P95 over 1h above the threshold in
  `accelerator.yaml.acceptance.p95_latency_ms`
- **HITL misconfiguration alert** — any `tool.hitl_misconfigured`
  event (this indicates production is running without an approver)
- **HITL rejection spike** — `tool.hitl_rejected` > N / hour

Thresholds are customer-owned. The accelerator does not opine.

---

## 2. Operational dials at runtime

### Killswitch

`src/accelerator_baseline/killswitch.py::assert_enabled(scope)` raises
`KillSwitchEngaged` when the env var `KILLSWITCH_<SCOPE>` is
`"1" | "true" | "on"` (case-insensitive). Default scope is `tools`.

**Flip the switch on the Container App:**

```bash
az containerapp update \
  --name <api-container-app-name> \
  --resource-group <rg> \
  --set-env-vars KILLSWITCH_TOOLS=on
```

This halts every side-effect tool call (read-only retrieval + agent
inference keep working). Re-enable by setting the var back to empty
or `off`.

**Important:** env vars set via `az containerapp update` **will be
overwritten** the next time `azd provision` runs (the Bicep template
is the source of truth). For anything longer than an incident
mitigation, add the variable to `infra/modules/container-app.bicep`
in the customer's fork and redeploy. For partners who need a
portal-style toggle, the killswitch docstring points at Azure App
Configuration feature flags as an extension pattern.

### HITL approver

HITL is a **partner-authored webhook**, not a UI this accelerator
ships. The contract (from `src/accelerator_baseline/hitl.py`):

- `HITL_APPROVER_ENDPOINT` = URL of the partner's approver service.
  `checkpoint()` posts the action + args and blocks until a
  decision returns.
- `HITL_DEV_MODE=1` = local development auto-approve with a loud
  warning. **Never set this in production.**
- Neither set = `checkpoint()` raises `HITLMisconfigured` and emits
  `tool.hitl_misconfigured` — a deliberately loud failure so a
  misconfigured production does not side-effect without a human.

The partner's handover packet lists the actual approver URL, the
approvers, the SLA, and the escalation path. Day-2 ops owns
**reachability** of that endpoint; the partner owns its logic.

### Content filter

Azure AI content filter is bound to the model deployment in
`infra/modules/foundry.bicep` via IaC. Severity thresholds live in
the Bicep — changing them requires a Bicep edit and `azd provision`.
Editing the filter in the Foundry portal is **not supported** — the
postprovision `foundry-bootstrap.py` pre-flight will still verify
a filter is bound, but portal drift from the IaC is undefined
behavior. Do not disable the filter; the RAI pattern doc
(`docs/patterns/rai/README.md`) calls this out as out-of-support.

---

## 3. Cost

### Where the numbers come from

`MODEL_PRICE_USD_PER_1K_TOKENS` in `src/accelerator_baseline/cost.py`
ships rough defaults for `gpt-5.2` and `gpt-5-mini`. The shipped
template default deployment is `gpt-4o-mini` (from
`infra/main.parameters.json`), which is **not** in that price table.

Crucially, `cost.call` telemetry **does not fire by default in the
shipped flagship** — the emitter `record_call_cost(agent,
UsageSample(model, input_tokens, output_tokens))` is exported from
`src/accelerator_baseline/cost.py` but is not invoked anywhere in
the flagship workflow. To get cost signal in production a partner
must do **both**:

1. Wire `record_call_cost(...)` into the Foundry call site so the
   event actually emits, AND
2. Populate `MODEL_PRICE_USD_PER_1K_TOKENS` with the deployed
   model's pricing so `estimate_call_cost()` returns a non-zero
   `value`.

Confirm with the partner whether they wired both. If they did not,
`cost.call` events will not appear in App Insights, the cost-per-call
dashboard panel will be empty, and the `cost_per_call_usd` acceptance
gate will trip a loud failure on every eval run (see §4).

### Azure-side cost monitoring

`infra/main.bicep` tags every resource with `azd-env-name=<envName>`
and `workload=<scenarioId>-accelerator`. Use those tags as filters
in Azure Cost Management views. Additional chargeback tags
(`costcenter`, `businessunit`) are a partner-scope Bicep edit.

---

## 4. Re-running evals against the deployed environment

### Quality evals

```bash
python evals/quality/run.py --api-url https://<container-app-fqdn>
```

Hits the deployed endpoint for each case in
`evals/quality/golden_cases.jsonl`, writes
`evals/quality/results.jsonl`, and returns non-zero if individual
cases fail their per-case check.

### Redteam evals

```bash
python evals/redteam/run.py --api-url https://<container-app-fqdn>
```

Same shape — cases in `evals/redteam/cases.jsonl`, output in
`evals/redteam/results.jsonl`.

### Acceptance enforcement

Threshold enforcement (from `accelerator.yaml.acceptance`) is a
**second step**. After both runners finish:

```bash
python scripts/enforce-acceptance.py
```

Reads both `results.jsonl` files and
`src/accelerator_baseline/evals.py::evaluate_acceptance` enforces:

- average quality score ≥ `quality_threshold`
- average groundedness ≥ `groundedness_threshold`
- P95 latency ≤ `p95_latency_ms`
- average `cost_usd` ≤ `cost_per_call_usd` (**fails if no
  `cost_usd` values were recorded — a silent inert gate is treated
  as a failure**)
- if `redteam_must_pass: true`, zero redteam cases may fail

The same two-step runs automatically in CI:

- `.github/workflows/evals.yml` (PR gate) — requires the repo
  variable `EVALS_API_URL` pointing at the long-lived deployed
  environment. See `docs/getting-started.md` §"Required GitHub
  secrets and variables".
- `.github/workflows/deploy.yml` (post-deploy check) — passes
  `needs.azd-up.outputs.api_url` (the URL just deployed) directly to
  the eval runners; no `EVALS_API_URL` variable is required for this
  workflow.

### When to run manually

- After a model swap
- After a prompt edit (see §6)
- Before a monthly value review
- On any production incident where output quality is suspected

---

## 5. Model swap

The **authoritative source of truth** for which model(s) are deployed
is `accelerator.yaml.models[]`, not `infra/main.bicep` param defaults.
On every `azd provision` or `azd up`, the preprovision hook
`scripts/sync-models-from-manifest.py` rewrites the five managed azd
env vars (`AZURE_AI_FOUNDRY_MODEL_NAME`, `_MODEL_VERSION`, `_MODEL`,
`_MODEL_CAPACITY`, `_EXTRA_DEPLOYMENTS_JSON`) from the manifest. Raw
`azd env set AZURE_AI_FOUNDRY_MODEL_NAME=…` overrides **will be
clobbered** on the next provision.

### Swap procedure

1. In the customer's fork, edit the `default: true` entry in
   `accelerator.yaml → models[]`:
   - `model` — OpenAI model name
   - `version` — model version string
   - `deployment_name` — Foundry deployment resource name
   - `capacity` — TPM in thousands
2. Confirm the target region has quota for the new model (Azure portal
   → Foundry account → Quotas).
3. (Optional) Update `MODEL_PRICE_USD_PER_1K_TOKENS` in `cost.py` so
   the cost gate isn't inert for the new model.
4. `azd provision` — preprovision syncs env vars, Bicep creates the
   new deployment, postprovision `foundry-bootstrap.py` re-verifies
   the agents against the new model.
5. Re-run quality + redteam evals (§4) and `enforce-acceptance.py`.
6. If acceptance holds, merge; if not, revert the manifest PR.

To run two models side-by-side (canary), add a second entry (not
`default: true`) and set its `slug` — scenario agents can point at it
via the `scenario.agents[].model` field.

**Do not swap models in production without re-running evals.** A model
that benchmarks equivalently often shifts quality / cost / latency in
the specific scenario.

---

## 6. Prompt / agent-instruction rollback

Agent instructions are stored in Foundry, but their **repo-side source
of truth** is `docs/agent-specs/<foundry_name>.md`. Every `azd
provision` runs `scripts/foundry-bootstrap.py` as the postprovision
hook, which overwrites each agent's portal-side instructions from the
matching spec file. Consequences:

- Direct Foundry portal edits to an agent's instructions are
  **transient** — they will be reverted on the next `azd provision`.
  The portal is the runtime source of truth *between* provisions but
  not a durable authoring surface.
- The supported rollback path is: revert the spec file in the
  customer's fork → `azd provision` → re-run evals.

If the partner's handover packet documents a different authoring
workflow (e.g., "prompts are portal-managed for this engagement and
`foundry-bootstrap.py` is disabled"), follow the packet.

---

## 7. Secret rotation

### Key Vault

The shipped accelerator does **not** read secrets from Key Vault at
runtime. `src/config/settings.py` loads configuration from env vars
only (`AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_SEARCH_ENDPOINT`,
`APPLICATIONINSIGHTS_CONNECTION_STRING`, `HITL_APPROVER_ENDPOINT`,
etc.); Bicep sets those values on the Container App as plain env
values from provisioning-time outputs. The Key Vault is provisioned
and MI-accessible, but no code path fetches secrets from it by
default.

If the partner wired a Key Vault-backed secret (either via Container
Apps secret references in `infra/modules/container-app.bicep`, or via
`SecretClient` / `DefaultAzureCredential` added to the scenario
code), rotation follows the standard Azure pattern for whichever path
they used. The partner's handover packet describes this if
applicable. Without such wiring, there are **no runtime secrets to
rotate** on the accelerator itself — rotation applies to partner-added
integrations.

### Managed Identity

Managed identities do not rotate — assignments are stable. Rotating
the MI itself is a full re-provision (`azd down --purge` + `azd
up`); new MI principal ID flows through Bicep role assignments.

### Partner-provided external secrets

If the partner wired an HITL approver with signed webhooks, a Bing
Grounding resource, or any other external service, secret rotation
for those follows the partner's runbook, not this one.

---

## 8. Incident response

### P1 — bad output or unsafe tool behavior in production

1. **Flip the killswitch** (§2). Side-effect tools halt immediately;
   read-only paths keep working so in-flight sessions don't error.
2. In App Insights, filter `customEvents` by `tool.executed`,
   `tool.hitl_*`, and `response.returned` with `ok == 'false'` over
   the incident window. Correlate to a specific agent / tool.
3. If a prompt regression is suspected, **do not** trust Foundry
   portal history as a durable record — check
   `docs/agent-specs/<foundry_name>.md` in the fork's git history.
   Revert the spec file + `azd provision` to roll back.
4. If a code regression is suspected, revert the offending commit
   in the fork + `azd deploy`.
5. Re-run evals (§4). Disengage the killswitch only when they pass.

### P1 — model outage

Manifests as elevated `response.returned` with `ok == 'false'` and
error strings mentioning Foundry. Confirm via Azure Service Health.

Mitigation: swap to a backup model (§5), re-run evals, deploy. Revert
when the primary region recovers. This is a partner-coordinated
change if they own the fork's release process.

### P1 — DNS / private-endpoint failure (Tier 3 only)

Tier 3 resolves Foundry / Search / Key Vault through **hub-provided**
private DNS zones. If the hub team removes or re-keys a zone link,
the Container App hits connection or DNS errors. Symptoms: sudden
burst of `response.returned` errors with transport-level messages.

Mitigation: the platform / networking team that owns the hub restores
the zone link. `tier3InputGuard` only fires at provision time — it
does not detect post-deploy drift, so this is a shared-ownership
incident.

### P2 — cost regression

Cost alerts fire (§1). Likely causes:

- Model swap without refreshing `MODEL_PRICE_USD_PER_1K_TOKENS`
- Prompt regression inflating output tokens
- Usage-pattern shift that increases retrieval frequency

Remediate by rolling back whichever change correlates. Do not
"fix" a cost regression by relaxing `cost_per_call_usd`.

### Security incidents

Follow `SECURITY.md` — vulnerabilities go to MSRC; customer-side
security incidents follow the customer's own IR process.

---

## 9. Scaling

### Container App

`infra/modules/container-app.bicep` ships `minReplicas: 1`,
`maxReplicas: 3` on the Consumption profile. Tune those values in
the fork and `azd provision`. Changing autoscale rules (CPU-based,
queue-based, cron-based) is a Bicep edit.

### Model capacity

Capacity is a **regional TPM quota** on the Foundry account.
Increase via `accelerator.yaml.models[].capacity` (§5). If the
region is at quota, request an increase in Azure portal → Foundry →
Quotas, or add a second deployment in another region (requires
partner-authored routing — not shipped in the flagship).

### AI Search

Change the SKU in `infra/modules/ai-search.bicep` (and `replicaCount`
/ `partitionCount` if tuned in the fork) then `azd provision`.
Some SKU transitions require re-indexing; confirm with
`seed-search.py` before going live.

---

## 10. Re-provisioning and rollback

### `azd provision`

Idempotent. Re-applies `infra/main.bicep`, then runs the preprovision
and postprovision hooks (`sync-models-from-manifest.py`,
`foundry-bootstrap.py`, `seed-search.py`). **It does touch:**

- Foundry agent instructions (overwritten from `docs/agent-specs/`)
- AI Search index schema and, if the index is empty or the seed
  script is written to re-seed, the index contents

Plan `azd provision` windows accordingly — it is not purely an
infra-plane operation.

### `azd deploy`

Pushes a new Container App image only. Does not touch Foundry,
Search, or Key Vault.

### `azd down --purge`

Destructive — tears down every resource in the environment. Use
only when decommissioning or recovering from a corrupted
environment.

### Rolling back code

`git revert` in the fork + `azd deploy`. Prompt/spec changes
require `azd provision` (see §6).

---

## 11. Monthly value review

Pull numbers from App Insights directly. `accelerator.yaml.kpis[]`
enumerates the KPIs the engagement committed to in discovery; each
entry has `{name, type, baseline, target}` only — it does **not**
auto-wire telemetry events. Partners wire specific events per KPI
when they implement the scenario. Confirm the mapping with the
partner and reuse the workbook panels (§1) plus custom KQL for
scenario-specific KPIs.

At the review, compare 30-day trends to the baseline and target in
`docs/discovery/solution-brief.md`. If a KPI drifts from target,
trigger a partner engagement for prompt / retrieval / tool tuning —
that work is out of day-2 scope.

---

## 12. Out of scope for this runbook

- Editing the upstream accelerator template itself
- Scaffolding a new scenario
- Partner-authored custom integrations (the partner's runbook owns
  those)
- Changes to the customer's landing zone, hub networking, or Azure
  policy outside this engagement's resource group
- End-user training material

For anything not covered: escalate to the partner delivery team, or
file a GitHub Issue on the template repo for upstream fixes.
