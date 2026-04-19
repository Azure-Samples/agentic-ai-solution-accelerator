# Statement of Work (SoW) Template

> Copy this file into a customer engagement repo as `docs/engagement/SoW.md`. Partner-delivery-lead-owned. Not a legal contract — supports the legal SoW.

## Engagement summary
- **Customer:** <name>
- **Partner:** <name>
- **Path:** [A | B | C]
- **Bundle (target):** <one of 5>
- **Profile:** <dev-sandbox | guided-demo | prod-standard | prod-privatelink>
- **Primary scenario:** <supplier-risk / itops-triage / knowledge-concierge / custom>
- **Start date / target go-live:** <dates>

## Scope IN
- <bullet list of capabilities agreed>

## Scope OUT (explicit)
- Anything requiring new blessed bundles (governance board ask; not in SoW).
- BYO-IaC unless re-qualification package explicitly approved.
- Non-supported models / regions / SKUs.
- Free-form A2A > 2 agents.

## Qualification artifacts required (Path B/C)
- [ ] `.qualification.yaml` populated + signed
- [ ] Data classification decision
- [ ] Network topology decision
- [ ] Identity model decision
- [ ] RAI IA scoping minutes
- [ ] Security review path agreed
- [ ] Operating model chosen

## Deliverables
- Scaffolded repo + CI
- Validated Spec + materialized params/evals/dashboards/alerts
- Agent modules + tool wrappers + grounding glue
- Eval suite (quality + red-team)
- Attested deploy + runbook walkthrough
- Day-2 customer ops handoff

## Responsibilities
| Activity | Partner | Customer | MSFT |
|---|---|---|---|
| Spec authoring | X |  |  |
| RAI IA sign-off |  | X |  |
| Code implementation | X |  |  |
| Infra deploy | X |  |  |
| Security review |  | X |  |
| Attestation issue | X |  |  |
| Pager on day 1 | X (handoff 30–60d) | X (post-handoff) |  |
| Baseline upgrades | X |  | X (releases, ring promotion) |

## Risks + assumptions
- Assumes customer GitHub org for qualification (§ customer-github-onboarding).
- Assumes Foundry + Bicep regional availability in target region.
- Assumes attestation cadence honored (30d).

## Exit criteria
- 7 days post-deploy stability.
- Day-2 handoff complete.
- No open sev-1; no open high-severity waiver.
