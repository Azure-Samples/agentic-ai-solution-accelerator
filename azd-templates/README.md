# azd Templates — Blessed Bundles

Five azd templates, one per blessed bundle. These are the **only** deployment fast paths supported by attestation.

| Bundle | Directory | Profile | Side-effect tools | Network |
|---|---|---|---|---|
| `sandbox-only` | [`sandbox-only/`](sandbox-only/) | dev-sandbox OR guided-demo | not allowed | public |
| `retrieval-prod` | [`retrieval-prod/`](retrieval-prod/) | prod-standard | not allowed | public |
| `retrieval-prod-pl` | [`retrieval-prod-pl/`](retrieval-prod-pl/) | prod-privatelink | not allowed | private link |
| `actioning-prod` | [`actioning-prod/`](actioning-prod/) | prod-standard | required + HITL | public |
| `actioning-prod-pl` | [`actioning-prod-pl/`](actioning-prod-pl/) | prod-privatelink | required + HITL | private link |

All templates share Bicep modules from `delivery-assets/bicep/modules/`.

## Why 5 only

See [`../docs/supported-customization-boundary.md`](../docs/supported-customization-boundary.md) §5. Variants are expressed via Spec + profile + params, NOT new bundle rows. Bundle count is capped at 5 through v1 + v1.5.

## What these templates ship (scope)

- Bicep modules wired + parameterized.
- `main.parameters.json` + `main.parameters.override.json` pattern.
- Workflow stubs for CI deploy + attestation issuance.
- README per bundle with quickstart + expected outputs.

## What these templates do NOT ship

- Agent prompts / instructions (Foundry portal).
- Business logic code (partner vibecodes).
- Customer-specific grounding configs (declared in Spec; materialized at deploy time).

## Phase B placeholder

These templates are stubbed for Phase A. Full Bicep module set + hardened parameters ship with baseline v1.0 (Phase C + E in authoring plan).
