# Getting started

> Status: **D1 preview — secrets table + prereqs only.** The full walkthrough
> (exact 15-minute timeline, troubleshooting, HITL end-to-end) lands in D3.

This is the single source of truth for onboarding a partner onto the accelerator.
If something here disagrees with README or another doc, this file wins.

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
(default `gpt-4o-mini`, 30k TPM). Confirm quota in your target region before
running `azd up`.

## Required GitHub secrets and variables

Every secret / variable referenced in `.github/workflows/*.yml` is listed
below. The accelerator lint (`scripts/accelerator-lint.py`) fails the build if
a workflow references a name that does not appear here.

### Secrets (repo → Settings → Secrets and variables → Actions → Secrets)

| Name | Purpose | Source |
|------|---------|--------|
| `AZURE_CLIENT_ID` | Federated-credentials client id used by `Azure/login@v2` | Entra app registration for CI |
| `AZURE_TENANT_ID` | Entra tenant id | Entra portal → Overview |
| `AZURE_SUBSCRIPTION_ID` | Subscription that hosts the accelerator | `az account show` |

### Variables (repo → Settings → Secrets and variables → Actions → Variables)

| Name | Purpose | Example |
|------|---------|---------|
| `AZURE_ENV_NAME` | `azd` environment name (used in resource naming) | `dev` |
| `AZURE_LOCATION` | Azure region | `eastus2` |
| `EVALS_API_URL` | URL of the deployed API that evals run against | `https://api-dev-xxxx.containerapps.io` |

### Local `.env` (for development, not CI)

| Name | Purpose |
|------|---------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | Foundry project endpoint (Bicep output) |
| `AZURE_AI_FOUNDRY_ACCOUNT_NAME` | Parent Cognitive Services account name (Bicep output) |
| `AZURE_AI_FOUNDRY_MODEL` | Model deployment name, default `gpt-4o-mini` |
| `AZURE_SUBSCRIPTION_ID` | Subscription for management-plane pre-flight checks |
| `AZURE_RESOURCE_GROUP` | RG holding the Foundry account |
| `HITL_APPROVER_ENDPOINT` | Webhook URL for side-effect approvals (prod) |
| `HITL_DEV_MODE` | Set to `1` to auto-approve in dev — never in prod |

## CI chain

`.github/workflows/deploy.yml` runs three jobs in order:

1. `accelerator-lint` — runs ruff, pyright, and `scripts/accelerator-lint.py`
2. `evals` — runs quality + red-team evals against `EVALS_API_URL` and enforces `accelerator.yaml::acceptance`
3. `azd-up` — `needs: [accelerator-lint, evals]`. Cannot run until both are green.

This gate is enforced by `deploy_gated_on_lint_and_evals` in the accelerator lint.

## What `azd up` provisions

- Cognitive Services account (`kind=AIServices`, GA)
- Default content filter (`accelerator-default-policy`) blocking Medium+ on Hate/Sexual/Violence/Selfharm
- Model deployment (`gpt-4o-mini`, `GlobalStandard`, 30 TPM) bound to the content filter
- Foundry project (`accelerator-default`)
- Azure AI Search, Key Vault (RBAC), Container App, Log Analytics + App Insights
- User-assigned managed identity with Cognitive Services OpenAI User + Azure AI Developer roles

## Troubleshooting

Expanded in D3. Common D1-era issues:

- `preflight: model deployment 'gpt-4o-mini' not found` → re-run `azd up` or
  increase `GlobalStandard gpt-4o-mini` quota in your region.
- `preflight: has no RAI (content filter) policy bound` → re-run `azd up` so
  Bicep reapplies the default policy.
- `secrets-doc` lint failure → add any new workflow secret/var to the tables
  above before merging.
