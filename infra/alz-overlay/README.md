# `infra/alz-overlay/` — Azure AI Landing Zone integration skeleton

**Read `docs/patterns/azure-ai-landing-zone/README.md` first** — this
folder is the Tier 3 (`landing_zone.mode: alz-integrated`) reference
material.

## What this folder is

A **subscription-scope** Bicep deployment that wires the accelerator's
spoke resources into a customer's existing AI ALZ. It is NOT part of
`infra/main.bicep` (which is resource-group-scope). The partner runs
`main.bicep` in here first (to stand up the spoke RG with diagnostics
and private DNS zone *group* references pointing at the hub), then
runs the workload `infra/main.bicep` with the Tier-3 parameter file.

This folder ships as a **skeleton** — it compiles and has the right
shape, but the hub resource IDs are placeholders. The partner fills
them in via the `/configure-landing-zone` chatmode.

## Pre-requisites (partner collects from customer CCoE)

- **Management group path** for AI workloads (e.g. `.../mg-alz/mg-landingzones/mg-ai`).
- **Spoke subscription ID** (pre-vended from the customer's subscription vending process).
- **Hub vNet resource ID** for peering.
- **Private DNS zone resource IDs** under the hub's `rg-dns` (or equivalent):
  - `privatelink.cognitiveservices.azure.com`
  - `privatelink.openai.azure.com`
  - `privatelink.vaultcore.azure.net`
  - `privatelink.search.windows.net`
  - `privatelink.monitor.azure.com` (for Private Link Scope, optional)
- **Log Analytics workspace resource ID** in the hub's management subscription.
- **Allowed locations** from the customer's ALZ policy initiative.

## What `main.bicep` does today

1. Creates the spoke resource group (at subscription scope).
2. Creates a spoke vNet.
3. Establishes vNet peering to the hub vNet (bidirectional config on the
   spoke side; the hub-side peering must be created by the customer's
   CCoE with `allowForwardedTraffic` + `useRemoteGateways` as appropriate).

That's it. This is deliberately a minimal scaffold; it compiles clean
and is enough to hand to a customer CCoE as a starting point.

## What `main.bicep` does NOT do (yet)

The following are **planned for H9** and are explicitly out of scope
for this Tier 3 preview:

- Private DNS zone group bindings (privatelink.* resolution via hub).
- Private endpoints for Foundry / Search / Key Vault / Container App.
- Route tables forcing egress through the hub firewall.
- NSGs on the workload subnet.
- Diagnostic settings binding the spoke RG's activity log to the hub
  Log Analytics workspace.
- ALZ policy assignments (those are inherited from the MG and are
  customer-owned anyway).
- Foundry account, Key Vault, Search, Container App — those are still
  `infra/main.bicep` run afterward with `main.parameters.alz.json`.

Until H9 lands, the partner must wire PE + DNS + diagnostics by hand
(or in coordination with the customer CCoE). Be transparent about this
with the customer — deploying Tier 3 as-shipped flips public access
off but does **not** make the workload reachable.

## Deploy sequence

```bash
# Step 1 — subscription-scope overlay (one-time per spoke)
az deployment sub create \
  --location <region> \
  --template-file infra/alz-overlay/main.bicep \
  --parameters infra/alz-overlay/main.parameters.json

# Step 2 — workload deploy (every azd up)
azd env set AZURE_PE_SUBNET_ID   "<output from step 1>"
azd env set AZURE_PRIVATE_DNS_KV "<customer-provided DNS zone ID>"
# ... etc
azd up
```

## Consistency with the rest of the repo

The `landing_zone_mode_consistent` lint rule asserts that when
`accelerator.yaml.landing_zone.mode == 'alz-integrated'`:
- `infra/alz-overlay/main.bicep` exists and has no `CHANGEME`
  placeholders in `main.parameters.json`.
- `infra/main.parameters.alz.json` exists and sets
  `enablePrivateLink: true` and `externalIngress: false`.
- Workload modules (`key-vault.bicep`, `container-app.bicep`) accept
  the `publicNetworkAccess` / `externalIngress` parameter rather than
  hardcoding `Enabled` / `true`.

Fix lint findings by completing the chatmode walkthrough.
