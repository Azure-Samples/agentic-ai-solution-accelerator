# `infra/avm-reference/` — AVM-equivalent module exemplars (study-only)

**Read `docs/patterns/azure-ai-landing-zone/README.md` first** — this
folder is the Tier 2 (`landing_zone.mode: avm`) reference material.

## What this folder is

Hand-picked **Azure Verified Modules** (AVM) snippets that the partner
copies into `infra/modules/` (replacing the hand-rolled equivalents)
when moving from `standalone` → `avm`. Each file is a **self-contained
Bicep block** showing the AVM module reference, the canonical
parameters, and inline comments pointing at the AVM docs.

These files are **NOT wired into `infra/main.bicep`**. They do not
deploy on their own. The `/configure-landing-zone` chatmode walks the
partner through copying them in.

## What's in here today

| Resource | Hand-rolled (Tier 1) | AVM reference (Tier 2) | Status |
|---|---|---|---|
| Key Vault | `../modules/key-vault.bicep` | `key-vault.bicep` | Shipped |
| AI Search | `../modules/ai-search.bicep` | *(pending — partner vibecodes)* | Contributed by partners |
| Container App | `../modules/container-app.bicep` | *(pending)* | Contributed by partners |
| Monitor / Log Analytics | `../modules/monitor.bicep` | *(pending)* | Contributed by partners |

Start with the Key Vault exemplar — it shows the pattern clearly
(module reference, parameters, PE block, role assignments) and is the
easiest to diff against the hand-rolled version.

## Why Foundry is not in here

`Microsoft.CognitiveServices/accounts` (Foundry) does not have a
fully-GA AVM res module as of this writing. Track
<https://github.com/Azure/Azure-Verified-Modules/issues?q=cognitiveservices>.
Until then, keep `infra/modules/foundry.bicep` hand-rolled in Tier 2
as well, but add the AI ALZ-recommended parameters
(`networkAcls.defaultAction: Deny`, `publicNetworkAccess: Disabled`,
private endpoint binding) when moving to Tier 3.

## Upgrade cadence

When a new AVM module becomes GA that replaces one of our hand-rolled
modules, add an exemplar here (don't rewrite `infra/modules/` directly
— partners vibecode that swap themselves). Update this table and open
a PR; the `ga-sdk-freshness` schedule will flag stale references.
