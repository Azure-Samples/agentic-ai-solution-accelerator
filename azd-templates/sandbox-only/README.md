# sandbox-only — azd template

> ⚠️ **NOT FOR PRODUCTION.** Demos, POCs, certification dry-runs only. No attestation issued.

## When to use
- 60-minute quickstart (Phase 2 of partner playbook).
- Partner certification engagement.
- Internal reference implementation for MSFT teams.

## Prerequisites
- **Dedicated sandbox subscription** with Azure Policy deny-assignments, sandbox RBAC role, auto-teardown tag — OR —
- **MG-scoped policy assignment** with equivalent denies in partner tenant.
- If neither, fall back to `guided-demo` profile (loud label, no "hours" claim, no attestation).

See `docs/supported-customization-boundary.md` §2 and plan §6.

## Quickstart

```bash
azd init --template agentic-ai-accelerator/sandbox-only@0.1.0
azd env set profile dev-sandbox
azd env set autoTeardownAt 2026-05-01T00:00Z
azd up
```

## What you get
- Foundry project in a sandbox subscription
- Container Apps host
- App Insights + KV
- Auto-teardown tag enforced
- Connector allow-list (sandbox connectors only)

## What you don't get
- Attestation.
- Production SKUs.
- Production data access.
- "Hours" claim unless partner is certified + assisted-first-deployment (see §6).

## Next phase
Move to `retrieval-prod` / `actioning-prod` via Phase 3 qualification → `baseline new-customer-repo` scaffolding.
