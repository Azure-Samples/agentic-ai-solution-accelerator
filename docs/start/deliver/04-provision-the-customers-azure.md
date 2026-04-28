# 7. Provision the customer's Azure

*Step 7 of 10 · Deliver to a customer*

!!! info "Step at a glance"
    **🎯 Goal** — Stand up the customer's Foundry + supporting infra in their tenant via `azd up`, against a GitHub Environment that holds the customer's OIDC credentials.

    **📋 Prerequisite** — [6. Scaffold from the brief](03-scaffold-from-the-brief.md) complete — lint green; brief committed.

    **💻 Where you'll work** — VS Code (Copilot Chat + integrated terminal); GitHub web (Settings → Environments — `/deploy-to-env` walks you there); Azure portal (resource group inspection after).

    **✅ Done when** — Resource group exists in customer tenant; `/healthz` returns 200; Foundry agents are reachable; App Insights is wired; HITL approver endpoint is configured for the environment.

---

This step is two preflight chatmodes plus one `azd up`. The chatmodes do the GitHub plumbing (manifest entry, GitHub Environment, OIDC federated credential) so CI can deploy without a service-principal secret.

## Preflight: pick a landing-zone tier

```
/configure-landing-zone
```

The chatmode walks the partner through three tiers:

- **Tier 1 — `standalone`** — single-RG, public endpoints, Entra-only. For pilots and SMB.
- **Tier 2 — `avm`** — Azure Verified Modules + private endpoints + private DNS. For mid-market.
- **Tier 3 — `alz-integrated`** — overlays the customer's existing AI ALZ hub via `infra/alz-overlay/`. For regulated / enterprise.

Tier choice writes to `accelerator.yaml -> landing_zone.mode` and selects the matching `infra/` shape. The lint rule `landing_zone_mode_consistent` enforces the match.

For regulated customers: set `controls.private_endpoints = required` (implies Tier 2 or Tier 3).

→ Detail: [Reference → Architecture & governance → Azure AI landing zone](../../patterns/azure-ai-landing-zone/README.md).

## Preflight: register the customer environment

```
/deploy-to-env <env-name>      # e.g., dev, uat, prod
```

The chatmode adds an entry to `deploy/environments.yaml`, creates the matching **GitHub Environment**, wires the OIDC federated credential between the customer's Entra app registration and the GitHub Environment, scopes the per-environment secrets (`AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID`) and variable (`AZURE_LOCATION`), and dispatches a first deploy.

!!! warning "Never hand-edit `deploy.yml` to add envs"
    The manifest + the `resolve-env` job is the contract; the `deploy_matrix_matches_azure_envs` lint rule rejects drift. The azd environment name is **always** derived from `deploy/environments.yaml` — never set `vars.AZURE_ENV_NAME`.

If the environment will gate side-effect tools through a webhook approver (Logic Apps, Teams, ServiceNow), set `HITL_APPROVER_ENDPOINT` as an Environment secret on the same screen. Failures to reach the approver are treated as rejections (fail-closed).

## Provision + deploy

```bash
# Replace <customer-tenant-id> with the customer's Azure tenant GUID, and
# <customer-short-name> with the customer's short name (e.g., contoso)
az login --tenant <customer-tenant-id>
azd auth login
azd env new <customer-short-name>-dev
azd up
```

`azd up` provisions, in ~10–15 minutes:

- Cognitive Services account (`kind=AIServices`, GA)
- Default content filter (`accelerator-default-policy`) blocking Medium+ on Hate/Sexual/Violence/Selfharm
- Model deployment (default `gpt-5-mini`, `GlobalStandard`, 30 TPM) bound to the content filter
- Foundry project (`accelerator-default`)
- Azure AI Search · Key Vault (RBAC) · Container App · Log Analytics + App Insights
- User-assigned managed identity with Cognitive Services OpenAI User + Azure AI Developer roles

The deployed API URL prints at the end — keep it; the next step uses it.

## Confirm the deploy is healthy

```bash
# Replace <api-url> with the URL azd up printed
curl <api-url>/healthz
```

200 = bootstrap succeeded (Foundry agents synced from `docs/agent-specs/`, AI Search index seeded, content filter attached, MI roles propagated).

If `/healthz` returns 503, the FastAPI startup bootstrap is failing — most often RBAC propagation lag (1–3 minutes). Watch in App Insights:

```kusto
traces | where operation_Name == "lifespan.startup"
```

→ Full troubleshooting: [Reference → Set up your machine → Troubleshooting](../ready/02-set-up-your-machine.md#troubleshooting--top-5-per-machine).

---

**Continue →** [8. Iterate & evaluate](05-iterate-and-evaluate.md)
