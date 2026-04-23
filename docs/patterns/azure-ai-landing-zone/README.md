# Pattern — Azure AI Landing Zone (AI ALZ) alignment

Partners deploy this accelerator into wildly different customer
environments: an SMB with a fresh tenant; a mid-market customer with a
platform team but no hub-spoke network; a regulated enterprise with a
full **Azure AI Landing Zone** already in place. One Bicep shape can't
serve all three without either forcing ALZ complexity on the SMB or
leaving the enterprise partner to rewrite the infra.

This pattern defines **three landing-zone tiers** the partner picks in
`accelerator.yaml` (`landing_zone.mode`). The framework ships reference
artifacts for each tier; Copilot helps the partner move between tiers
via the `/configure-landing-zone` chatmode.

## Tier decision tree

```
Customer has an existing Azure AI Landing Zone (hub vNet, private DNS
zones, policy assignments, MG hierarchy)?
├── YES  ──→  mode: alz-integrated        (Tier 3)
│
└── NO
     ├── Customer has any platform/CCoE team and wants AVM alignment,
     │   private endpoints, and CAF-shaped guardrails from day one?
     │   ├── YES ──→  mode: avm              (Tier 2)
     │   └── NO
     │        └── Pilot / sandbox / SMB greenfield?
     │            └── YES ──→  mode: standalone   (Tier 1)
```

## Tier 1 — `standalone` (default)

**What it is.** A single resource group, hand-rolled Bicep modules in
`infra/modules/`, public endpoints on Foundry and AI Search (with
Entra-only auth + Microsoft-managed content safety filter), all the
WAF/RAI baseline from Commit D1. `azd up` stands it up in ~15 minutes.

**When to use.** Self-host pilot in the partner's own subscription;
SMB customer with no existing Azure governance; hackathon / demo
environments. Also the correct starting point for any partner who
doesn't yet know the customer's answer to the decision tree.

**What the partner owns.** Network exposure (currently public endpoints
with RBAC), diagnostics, backup, quotas — nothing to inherit from a
hub. Works but is **not** the shape you put in front of a regulated
enterprise.

**Files involved.**
- `infra/main.bicep` + `infra/modules/*.bicep` (shipped)
- `infra/main.parameters.json` (shipped)
- No overlay, no AVM references required.

## Tier 2 — `avm` (AVM-aligned standalone)

**What it is.** Same topology as Tier 1 (no hub), but the Bicep is
migrated to **Azure Verified Modules** (`br/public:avm/res/<...>`)
wherever AVM is GA, and private endpoints + private DNS zones are
added inline. The accelerator ships **reference exemplars** in
`infra/avm-reference/` — study-only Bicep snippets that partners copy
into `infra/modules/` during vibecoding. Lint rule
`landing_zone_mode_consistent` asserts at least one AVM module
reference exists when `mode: avm`.

**When to use.** Mid-market customer with a platform team who wants
CAF-shaped guardrails, private networking, and AVM maintenance cadence
— but doesn't yet have a hub or ALZ to plug into.

**What the partner owns.** The network (new vNet in the same
subscription), private DNS zones, quota requests. Everything else
inherits from AVM's opinions.

**Files involved.**
- `infra/avm-reference/README.md` — how to swap a hand-rolled module
  for its AVM equivalent (study-only exemplars).
- `infra/modules/*.bicep` — partner replaces selected modules with AVM
  references during vibecoding via `/configure-landing-zone`.
- `accelerator.yaml` → `landing_zone.mode: avm`.

## Tier 3 — `alz-integrated` (Azure AI Landing Zone)

**What it is.** The accelerator lands in a **spoke subscription** that
is already part of the customer's AI ALZ. Resources expose **private
endpoints only**; PE IPs register into the **hub's** private DNS
zones (not new ones); Foundry network isolation is enabled; egress
goes through the hub firewall; subscription-scope policy assignments
inherited from the management group enforce the `AI ALZ` initiative
(diagnostics, customer-managed keys, content safety, allowed
locations, etc).

The accelerator ships `infra/alz-overlay/` — a **subscription-scope**
Bicep deployment that is separate from `infra/main.bicep` and wires
the spoke into the hub. Partner still runs `infra/main.bicep` for the
workload itself, but with `publicNetworkAccess: Disabled`, PE
resource IDs pointing at the hub's DNS zones, and the resource group
placed under the AI ALZ MG.

**When to use.** Regulated enterprise; any customer with an existing
Azure Landing Zone or AI-specific ALZ; Financial Services / Health /
Public Sector engagements; anywhere "connect to our hub" is a hard
requirement.

**What the partner owns.** Coordinating with the customer's CCoE for
subscription vending, hub peering, DNS zone identity access, and MG
placement. The accelerator gives them the Bicep scaffold and the
checklist in `docs/customer-runbook.md`.

**Files involved.**
- `infra/alz-overlay/main.bicep` — subscription-scope deploy that
  wires the spoke into the hub. Ships as a skeleton; partner fills in
  the hub resource IDs via `/configure-landing-zone`.
- `infra/alz-overlay/README.md` — pre-reqs (hub IDs, DNS zone IDs,
  log analytics workspace ID, MG path) and the `az deployment sub create`
  command.
- `infra/main.parameters.alz.json` — partner-generated parameters
  flipping `publicNetworkAccess: Disabled`, binding PE subnets, etc.

## What's consistent across all three tiers

Regardless of mode, **every** tier ships with:

- Entra-only auth, no shared keys.
- Microsoft-managed content safety filter on all Foundry deployments.
- App Insights + Log Analytics diagnostics (workspace-based).
- Key Vault with soft-delete + purge protection, RBAC-only.
- Managed Identity end-to-end (no SPN secrets).
- `scripts/accelerator-lint.py` GA-only SDK pins with GA exceptions in
  `infra/.ga-exceptions.yaml`.

These are WAF/RAI baseline, not landing-zone-specific — they are
always on.

## Further reading

- **Azure Well-Architected Framework for AI workloads** — <https://learn.microsoft.com/azure/well-architected/ai/>
- **Cloud Adoption Framework: Scenario — AI** — <https://learn.microsoft.com/azure/cloud-adoption-framework/scenarios/ai/>
- **Azure Landing Zones (ALZ) accelerator** — <https://aka.ms/alz>
- **AI Landing Zone (AI ALZ) reference** — <https://aka.ms/ai-landing-zone>
- **Azure Verified Modules (AVM)** — <https://azure.github.io/Azure-Verified-Modules/>
- This repo: `docs/patterns/waf-alignment/README.md`, `docs/patterns/rai/README.md`.
