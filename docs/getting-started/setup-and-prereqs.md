# Setup & prereqs

**One-time** workstation + subscription readiness. Run this once per partner machine and once per Azure subscription you'll deploy into; you do not re-read this every customer engagement. This is the authoritative reference for **setup, prereqs, secrets, and troubleshooting**. It complements — not replaces — the other partner-facing docs:

- For the end-to-end delivery motion (discovery → handover → measure) see [`docs/partner-playbook.md`](../partner-playbook.md).
- For the eight-step happy-path skim, see [`QUICKSTART.md`](../../QUICKSTART.md).
- For a sandbox rehearsal before your first customer, see [`docs/enablement/hands-on-lab.md`](../enablement/hands-on-lab.md).

When those docs and this one disagree on **setup mechanics** (prereqs, secrets, `azd` invocation, troubleshooting), this file wins. When they disagree on **delivery motion** (when to run discovery, how to scope an SOW, handover sequence), the playbook wins. The chatmodes in `.github/chatmodes/` win over both on the executable surface they drive.

## Where you'll work

This document is the authoritative reference for prereqs, secrets, and troubleshooting — most of it is something you'll *configure* (Terminal for CLI installs, GitHub web for environment secrets, Azure portal for quota). The QUICKSTART and hands-on-lab carry the same orientation table for the partner motion itself.

| Where | What you do here |
|---|---|
| **VS Code** | Run installs and verify versions in the integrated terminal (`` Ctrl+` ``); run `azd up` and the eval chain there too; edit `.env` for local dev; edit `accelerator.yaml` and `infra/main.parameters.json` to override defaults |
| **GitHub web (github.com)** | Repo → Settings → Environments → wire `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` and `AZURE_LOCATION` per environment; Settings → Secrets and variables → Actions for repo-level vars |
| **Azure portal (portal.azure.com)** | Confirm Foundry quota in your target region (Foundry → Quotas) before `azd up`; inspect the deployed resource group and resources after |

## What you ship

A partner clone of this template deploys a working agentic AI solution into the
customer's Azure in ~15 minutes via `azd up`. The flagship scenario (Sales
Research & Personalized Outreach) is runnable out of the box; swap it for your
own scenario by editing `accelerator.yaml -> scenario:` and scaffolding under
`src/scenarios/<id>/` with `python scripts/scaffold-scenario.py <id>`.

## Prerequisites

You will need:

| Tool | Why |
|------|-----|
| Azure subscription (Contributor) | `azd up` creates resources here |
| Azure CLI `>= 2.60` | fallback for targeted `az` calls |
| Azure Developer CLI (`azd`) `>= 1.11` | one-shot provision + deploy |
| GitHub CLI (`gh`) `>= 2.50` | repo bootstrap + secrets |
| Python `3.11` | backend, evals, lint, bootstrap |
| Docker or compatible runtime | local container builds |

Model quota: the accelerator deploys a `GlobalStandard` Azure OpenAI model
(default `gpt-5-mini`, 30k TPM — see `infra/main.bicep` params `modelName`,
`modelDeploymentName`, `modelCapacity`). Confirm quota in your target region
before running `azd up`, or override the params for a different model.

## Required GitHub secrets and variables

Every secret / variable referenced in `.github/workflows/*.yml` is listed
below. The accelerator lint (`scripts/accelerator-lint.py` →
`workflow_secrets_documented`) fails the build if a workflow references a name
that does not appear here.

This template supports **multi-environment BYO-Azure deploys**: `deploy/environments.yaml`
lists every Azure environment the pipeline can target, and each entry maps to a
**GitHub Environment** (repo → Settings → Environments) that holds its own scoped
OIDC credentials and region. Out of the box, the `dev` environment is registered.
Add more via the `/deploy-to-env` chat mode — never by hand-editing `deploy.yml`.

### Environment-scoped secrets (repo → Settings → Environments → `<env>` → Environment secrets)

Set these on **each** GitHub Environment you register (starting with `dev`). They are
read by `azd-up` inside `deploy.yml` after the `resolve-env` job picks which environment
to deploy to:

| Name | Purpose | Source |
|------|---------|--------|
| `AZURE_CLIENT_ID` | Federated-credentials client id used by `Azure/login@v2` | Entra app registration for CI |
| `AZURE_TENANT_ID` | Entra tenant id | Entra portal → Overview |
| `AZURE_SUBSCRIPTION_ID` | Subscription that hosts this environment's accelerator resources | `az account show` |

### Environment-scoped variables (repo → Settings → Environments → `<env>` → Environment variables)

| Name | Purpose | Example |
|------|---------|---------|
| `AZURE_LOCATION` | Azure region for this environment | `eastus2` |

Do **not** set `AZURE_ENV_NAME` anywhere. The azd environment name is derived from
`deploy/environments.yaml` (the `name:` field of the resolved entry). Setting it as
a variable would drift from the manifest; the `deploy_matrix_matches_azure_envs`
lint rule rejects that shape.

### Repo-level variables (repo → Settings → Secrets and variables → Actions → Variables)

| Name | Purpose | Example |
|------|---------|---------|
| `EVALS_API_URL` | API base URL used by the PR-triggered `evals` workflow (`.github/workflows/evals.yml`). Only required if you run evals standalone against an already-deployed environment. | `https://<ca-name>.<region>.azurecontainerapps.io` |

The `deploy.yml` workflow does NOT need `EVALS_API_URL` — it runs `azd up` first
and passes the API URL to the downstream evals job via a job output
(`needs.azd-up.outputs.api_url`). Only configure `EVALS_API_URL` if you want
PR-time evals to run against an existing deployment rather than waiting for a
full deploy chain.

### Local `.env` (for development, not CI)

| Name | Purpose |
|------|---------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | Foundry project endpoint (Bicep output) |
| `AZURE_AI_FOUNDRY_ACCOUNT_NAME` | Parent Cognitive Services account name (Bicep output) |
| `AZURE_AI_FOUNDRY_MODEL` | Model deployment name emitted by Bicep (`infra/modules/foundry.bicep` is the source of truth — agents never declare their own model) |
| `AZURE_SUBSCRIPTION_ID` | Subscription for management-plane pre-flight checks |
| `AZURE_RESOURCE_GROUP` | RG holding the Foundry account |
| `HITL_APPROVER_ENDPOINT` | Webhook URL for side-effect approvals (prod) |
| `HITL_DEV_MODE` | Set to `1` to auto-approve in dev — never in prod |

## Sandbox smoke-test (no customer involvement)

> **This path intentionally bypasses the discovery workshop** so a partner engineer can validate prereqs + infra shape end-to-end in their own subscription. For the full partner motion (discover → scaffold → provision → iterate → UAT → handover → measure) see [`docs/partner-playbook.md`](../partner-playbook.md). For a guided walkthrough of this same smoke-test with check-your-work gates, use [`docs/enablement/hands-on-lab.md`](../enablement/hands-on-lab.md) Lab 1.

```bash
# 1. Clone the template into your sandbox repo
# Replace <your-handle> with any short name (e.g., contoso → contoso-accel-sandbox)
gh repo create <your-handle>-accel-sandbox --template Azure-Samples/agentic-ai-solution-accelerator --private
cd <your-handle>-accel-sandbox
code .

# 2. Authenticate to your SANDBOX subscription (not a customer subscription for the smoke-test)
az login --tenant <your-sandbox-tenant-id>
azd auth login

# 3. Provision + deploy
azd env new sandbox-dev
azd up           # ~10-15 min: Foundry + Search + KV + ACA + App Insights
```

`azd up` returns the API URL. Hit `/healthz` to confirm the scenario loaded;
hit the scenario's endpoint (default `/research/stream`) with a sample payload
to run the flagship end-to-end.

Cleanup when done: `azd down --purge`.

## HITL setup

Every side-effect tool (CRM write, email send, ticket create) routes through
`src/accelerator_baseline/hitl.py`. Policies declared in
`accelerator.yaml -> solution.hitl` determine which actions block on approval.

Two modes:

- **Dev / demo** — set `HITL_DEV_MODE=1` in `.env` to auto-approve every
  checkpoint. Never ship this into a production env; the accelerator lint
  (`hitl_dev_mode_not_in_prod`) will block any infra template that bakes it in.
- **Prod / pilot** — set `HITL_APPROVER_ENDPOINT` to a webhook URL that the
  runtime `POST`s to when an action needs approval. The webhook is responsible
  for holding the checkpoint and returning an approve/reject decision. Simple
  shapes: a Slack/Teams bot, a Logic App, or a custom dashboard.

**Where you set these depends on the environment:**

| Where you're running | Where to set `HITL_*` |
|---|---|
| Local dev (running `uvicorn` or `python -m src.main` against your sandbox) | `.env` file in the repo root (loaded by `load_settings()`). `HITL_DEV_MODE=1` lives here only. |
| Sandbox `azd up` (manual deploy from your machine) | `azd env set HITL_APPROVER_ENDPOINT "<url>"` so it's persisted in `.azure/<env-name>/.env` and injected into the Container App. Never `azd env set HITL_DEV_MODE 1` for a deployed environment. |
| CI deploys (`deploy.yml` against a GitHub Environment) | github.com → repo → Settings → Environments → `<env>` → Environment secrets. Add `HITL_APPROVER_ENDPOINT` there; the workflow forwards it into `azd env set` before `azd up`. |

Failures to reach the approver are treated as rejections (fail-closed).

## Scenario customization

1. Read `docs/discovery/SOLUTION-BRIEF-GUIDE.md` and fill
   `docs/discovery/solution-brief.md` — or run `/discover-scenario` in Copilot
   Chat to generate it from a workshop.
2. Run `python scripts/scaffold-scenario.py <id>` to materialize a new
   scenario skeleton under `src/scenarios/<id>/` plus an agent-spec stub.
3. Paste the printed `scenario:` YAML block over the block in
   `accelerator.yaml`. The accelerator lint (`scenario_manifest_valid`)
   verifies every declared import resolves and every required key is present.
4. Customize the prompts, transforms, validators, retrieval schema, seed
   data, and eval golden cases to the brief.
5. `python scripts/accelerator-lint.py` locally before PR; CI re-runs it.

## Customizing models per agent

The accelerator provisions a **single default model deployment** out of the box
(`gpt-5-mini`). To give individual agents a different model — e.g. put the
supervisor on `gpt-5` while workers stay on `gpt-5-mini` for speed and cost —
add a `models:` block to `accelerator.yaml`:

```yaml
models:
  - slug: default                 # reserved slug; must be the default entry
    deployment_name: gpt-5-mini
    model: gpt-5-mini
    version: "2025-08-07"
    capacity: 30
    default: true
  - slug: planner                 # arbitrary slug; agents reference by slug
    deployment_name: gpt-5-planner
    model: gpt-5
    version: "2025-08-07"
    capacity: 10

scenario:
  agents:
    - { id: supervisor, foundry_name: accel-sales-research-supervisor, model: planner }
    - { id: account_planner, foundry_name: accel-account-planner }   # no `model:` → default
    # ...
```

How it flows:

1. **preprovision hook** (`scripts/sync-models-from-manifest.py`) reads the
   `models:` block and writes azd env vars: the default entry drives the
   existing `AZURE_AI_FOUNDRY_MODEL_NAME/VERSION/MODEL/CAPACITY` params, and
   non-default entries are packed into `AZURE_AI_FOUNDRY_EXTRA_DEPLOYMENTS_JSON`.
   The sync is convergent — removing the block from the manifest resets
   all managed env vars back to the template defaults so state doesn't
   drift across add/remove cycles.
2. **Bicep** (`infra/modules/foundry.bicep`) provisions the default deployment
   as before, then loops over the JSON array (`@batchSize(1)` — one at a
   time to avoid Foundry capacity-queue rejections) to create each extra
   deployment bound to the same shared RAI (content filter) policy. Output
   `AZURE_AI_FOUNDRY_MODEL_MAP` is a `slug -> deployment_name` object.
3. **postprovision** (`scripts/foundry-bootstrap.py`) resolves each Foundry
   agent's `scenario.agents[].model` slug via the map (or `default` when
   omitted) and creates/updates the agent with that deployment name. It also
   scans the Foundry account for **orphan deployments** — deployments that
   exist but are no longer in the manifest (ARM incremental mode doesn't
   delete them automatically) — and prints the concrete
   `az cognitiveservices account deployment delete` command per orphan so
   the partner can reclaim quota.

Lint enforcement (both BLOCKING):

- `models_block_shape` — every entry has slug/deployment_name/model/version/capacity;
  slugs and deployment names are unique; exactly one entry has `default: true`
  and uses `slug: default` (reserved).
- `agent_model_refs_exist` — every `scenario.agents[].model` references a declared
  slug; omitting the field falls through to slug `default`.

Omitting the whole `models:` block is supported: sync-models-from-manifest
then resets all managed env vars to the template defaults (gpt-5-mini /
2025-08-07 / capacity 30) — the same end state whether the block was ever
there or not. Partners who want to override the default deployment MUST
use the `models:` block with a single default entry — overriding via raw
env vars is unsupported because preprovision would clobber them on every
`azd up`.

## CI chain

`.github/workflows/deploy.yml` runs three jobs, chained so the first deploy
of a freshly cloned repo is green without any manual URL plumbing:

1. `accelerator-lint` — ruff, pyright, `scripts/accelerator-lint.py`
2. `azd-up` (`needs: [accelerator-lint]`) — runs `azd up` and publishes
   `api_url` as a job output
3. `evals` (`needs: [azd-up]`) — pulls `needs.azd-up.outputs.api_url`,
   runs quality + red-team evals, enforces `accelerator.yaml::acceptance`

This chain is enforced by `deploy_gated_on_lint_and_evals` in the
accelerator lint.

The separate `.github/workflows/evals.yml` runs on every PR against the
already-deployed `EVALS_API_URL` (if configured). Use this for fast feedback
between full `azd up` cycles.

## Private network access

Setting the Bicep param `enablePrivateLink=true` flips
`publicNetworkAccess` to `Disabled` on both the Cognitive Services
(Foundry) account and Azure AI Search, and sets `networkAcls.defaultAction`
to `Deny` on the Foundry account. Creating the actual private endpoints
and DNS zones requires a pre-existing VNet and subnet — this is
**bring-your-own** in the accelerator and not created by `azd up`. Add
private-endpoint + private DNS zone resources in your own fork when
targeting a regulated customer; the accelerator's shape (GA API versions,
disabled public access when requested) won't fight you.

## What `azd up` provisions

- Cognitive Services account (`kind=AIServices`, GA)
- Default content filter (`accelerator-default-policy`) blocking Medium+ on Hate/Sexual/Violence/Selfharm
- Model deployment (default `gpt-5-mini`, `GlobalStandard`, 30 TPM) bound to the content filter
- Foundry project (`accelerator-default`)
- Azure AI Search, Key Vault (RBAC), Container App, Log Analytics + App Insights
- User-assigned managed identity with Cognitive Services OpenAI User + Azure AI Developer roles

## Troubleshooting — top 5

1. **`preflight: model deployment 'gpt-5-mini' not found`** — the Foundry
   bootstrap (`scripts/foundry-bootstrap.py`) runs after `azd up` and verifies
   the deployment exists. If you changed `modelDeploymentName` or the region
   lacks quota, re-run `azd up` after fixing `infra/main.parameters.json` or
   requesting a quota increase for `GlobalStandard <model>`.
2. **`preflight: has no RAI (content filter) policy bound`** — Bicep attaches
   the default policy; if it drifted (portal edit, partial deploy), re-run
   `azd up` so the ARM deployment reapplies. The lint rule
   `content_filter_attached` catches this at template-edit time.
3. **`scenario_manifest_valid: module:attr does not resolve`** — the
   `scenario:` block in `accelerator.yaml` points at an import path the lint
   can't find. Verify the file exists under `src/<package path>/<module>.py`
   and the attribute is defined at module scope (the lint walks the AST; no
   import is attempted, so side-effect errors in the module don't hide the
   real issue).
4. **`secrets-doc` lint failure** — a workflow added a `secrets.NEW_NAME` or
   `vars.NEW_NAME` reference, but no entry was added to the tables above.
   Add it before merging.
5. **`azd up` completes but no API_URL emitted** — the bicep outputs
   (`API_URL` or `SERVICE_API_URI`) are empty. Confirm the Container App
   deployment succeeded in the Azure portal; the most common cause is the
   image build failing silently in an earlier `azd up` run. `azd deploy`
   rebuilds and redeploys the app without re-provisioning infra.

