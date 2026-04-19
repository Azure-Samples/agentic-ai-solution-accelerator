# Statement of Work (SoW) Template

> Copy this file into a customer engagement repo as `docs/engagement/SoW.md`. Partner-delivery-lead-owned. Not a legal contract — supports the legal SoW.

## Engagement summary
- **Customer:** <name>
- **Partner:** <name>
- **Bundle:** <one of 5>
- **Profile:** <dev-sandbox | guided-demo | prod-standard | prod-privatelink>
- **Primary scenario:** <supplier-risk / itops-triage / knowledge-concierge / custom>
- **Start date / target go-live:** <dates>

## Scope IN
- <bullet list of capabilities agreed>

## Scope OUT (explicit)
- Anything requiring a new bundle (not in v1). Bundle variants must be Spec parameters.
- \> 2-agent orchestration.
- Non-supported models / regions / SKUs.
- Customer infrastructure outside the agentic solution boundary (customer's existing networks, identity, data platform).

## Key decisions required before build
- [ ] Data classification (customer-signed)
- [ ] Network topology (public vs private link)
- [ ] Identity model (customer Entra tenant; MI vs B2B)
- [ ] RAI scoping minutes held + logged in `rai/scoping-minutes.md`
- [ ] Security review path agreed with customer (internal customer review? MSFT field-assisted?)
- [ ] Day-2 ownership model agreed (partner window → customer ownership)

## Deliverables
- Scaffolded customer repo + CI (validator on every PR)
- Validated `spec.agent.yaml` + materialized params / evals / dashboards / alerts
- Agent modules + tool wrappers + grounding glue
- Eval suite (quality + red-team)
- Production deploy + runbook walkthrough
- Day-2 customer ops handoff

## Responsibilities
| Activity | Partner | Customer | Microsoft |
|---|---|---|---|
| Spec authoring | X |  |  |
| RAI scoping sign-off |  | X |  |
| Code implementation (business layer) | X |  |  |
| Infrastructure deploy | X |  |  |
| Security review |  | X |  |
| Pager day-1 | X (handoff window) | X (post-handoff) |  |
| Baseline upgrades in customer repo | X |  | X (publishes releases) |

## Risks + assumptions
- Assumes Foundry + Bicep regional availability in target region.
- Assumes customer can provide an identity/tenant for MI-backed access to their data sources.
- Assumes partner + customer align on the accelerator's hard invariants (see `docs/customization-guide.md`).

## Exit criteria
- 7–14 days post-deploy stability.
- Day-2 handoff complete; runbook walkthrough held.
- No open sev-1.
