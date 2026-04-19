# azd Templates — Blessed Bundles

Five azd templates, one per blessed bundle. These are reference deployment starting points; partners copy them into a customer repo (or use BYO-IaC that satisfies the same contracts).

| Bundle | Directory | Profile | Side-effect tools | Network |
|---|---|---|---|---|
| `sandbox-only` | [`sandbox-only/`](sandbox-only/) | dev-sandbox · guided-demo | not allowed | public |
| `retrieval-prod` | [`retrieval-prod/`](retrieval-prod/) | prod-standard | not allowed | public |
| `retrieval-prod-pl` | [`retrieval-prod-pl/`](retrieval-prod-pl/) | prod-privatelink | not allowed | private link |
| `actioning-prod` | [`actioning-prod/`](actioning-prod/) | prod-standard | required + HITL | public |
| `actioning-prod-pl` | [`actioning-prod-pl/`](actioning-prod-pl/) | prod-privatelink | required + HITL | private link |

## Why 5 only

See [`../../docs/customization-guide.md`](../../docs/customization-guide.md) §5. Variants are expressed via Spec + profile + params, NOT new bundle rows. Bundle count is capped at 5 through v1 + v1.5.

## What these templates ship

- Bicep modules wired + parameterized.
- `main.parameters.json` + `main.parameters.override.json` pattern.
- Workflow stubs for CI deploy.
- README per bundle with quickstart + expected outputs.

## What these templates do NOT ship

- Agent prompts / instructions (Foundry portal owns these).
- Business logic code (partner vibe-codes it).
- Customer-specific grounding configs (declared in Spec; materialized at deploy time).

## Phase A placeholder

These templates are stubbed for Phase A. Full Bicep module set lands in Phase C with baseline v1.0.
