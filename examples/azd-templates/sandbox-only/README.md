# sandbox-only — azd template

> ⚠️ **NOT FOR PRODUCTION.** Demos, POCs, internal reference only.

## When to use
- 60-minute quickstart for a customer demo.
- Partner engineers learning the accelerator.
- Internal reference implementation for Microsoft teams.

## Prerequisites
- A dedicated dev/sandbox Azure subscription (or resource group with hard cost cap + auto-teardown tagging).
- No customer production data.
- Foundry access in the subscription.

## Quickstart

```bash
azd init --template <accelerator-feed>/sandbox-only@0.1.0
azd env set profile dev-sandbox
azd up
```

## What you get
- Foundry project in the sandbox subscription
- Container Apps host
- App Insights + Key Vault
- Synthetic-data connector allow-list

## What you don't get
- Production SKUs.
- Production data access.
- Private-link isolation.

## Next step
When ready for production, copy from `retrieval-prod/` or `actioning-prod/` (or their `-pl` variants) and work the partner playbook Phase 1–6.
