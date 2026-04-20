# Reference: RFP / Proposal Response

> **Shape:** supervisor-routing with parallel specialists. **Primary ROI lever:** response time and win rate. **Variant of:** the flagship. Scaffolding reference — adapt the flagship `src/` to this scenario via `/scaffold-from-brief`.

## When to use this
Customer responds to complex RFPs / RFIs / security questionnaires. Today: a cross-functional scramble (sales, pricing, legal, security, technical) that takes days per response and recycles inconsistent boilerplate.

A chatbot can't help meaningfully here — the work is composing a multi-section document grounded in customer-specific policy, past-proposal content, and current product capability. An agentic solution with specialist workers aggregates correctly-grounded sections in parallel, with HITL on legal and pricing sections.

## Chatbot baseline vs agentic lift
| Capability | Chatbot | Agent + HITL |
|---|---|---|
| Surface past Q&A | ✓ (poorly) | ✓ (grounded retrieval over past proposals) |
| Draft a pricing response | ✗ | ✓ specialist worker w/ HITL |
| Draft a legal/contractual response | ✗ | ✓ specialist worker w/ HITL |
| Draft a technical/security response | ✗ | ✓ specialist worker |
| Assemble multi-section proposal | ✗ | ✓ aggregator |
| Write to proposal DMS | ✗ | ✓ with HITL |

**ROI lever:** response time (days → hours), win rate lift, deal-team hours saved per RFP.

## Proposed agent graph
```
  Supervisor (RFP intake + section routing)
  ├── PricingWorker     — prices against rate card + approved discounts
  ├── LegalWorker       — answers from policy + past contracts, flags deviations
  ├── TechnicalWorker   — answers technical/architecture Qs w/ citations
  ├── SecurityQWorker   — answers security questionnaires from policy corpus
  └── ReferenceWorker   — pulls case studies + references
  Aggregator            — assembles full proposal draft + coverage report
```

## Side-effect tools
- `dms_upload_draft` — proposal DMS (SharePoint / custom) — **HITL: always** before writing final
- `flag_deviation` — creates a review task when Legal/Pricing detects deviation from policy
- `request_sme_input` — pages a human SME for a gap the agents can't fill

## Grounding
- Past-proposal corpus (AI Search index)
- Policy corpus: pricing guidelines, legal positions, approved boilerplate (AI Search index)
- Product docs (AI Search index)
- Security controls library (AI Search index; source of truth for `SecurityQWorker`)

## HITL policy
- **always:** `dms_upload_draft` (nothing auto-published)
- **always:** pricing sections' approval before aggregator includes them
- **always:** legal/contractual deviations flagged for legal review before inclusion
- **threshold:** technical/security sections with confidence < 0.85 trigger SME review

## Success criteria to fill in
- Time to first complete draft (current → target, in hours)
- Coverage: % of RFP questions answered on first pass (target ≥ 95%)
- Consistency: % of responses that match approved boilerplate (target ≥ 90%)
- Win-rate lift on RFPs scored above quality threshold (leading indicator)

## RAI risks specific to this scenario
1. Agent makes up a technical capability the product doesn't have → mitigated by grounded retrieval + `validate.py` rejecting unsupported claims.
2. Agent quotes pricing outside approved rate card → mitigated by PricingWorker HITL + schema-validated rate card input.
3. Agent answers a legal question that commits the company → mitigated by LegalWorker HITL-always.
4. Agent leaks sensitive past-proposal content between customers → mitigated by tenancy-scoped index + redteam case.
5. Agent over-claims security controls not in effect → mitigated by SecurityQWorker sourcing from controls library only.

## KPIs to instrument (events)
- `rfp.received`
- `rfp.section.drafted` (per section type)
- `rfp.section.coverage_met`
- `rfp.hitl_pricing_approved` / `rfp.hitl_pricing_revised`
- `rfp.hitl_legal_approved` / `rfp.hitl_legal_revised`
- `rfp.draft_uploaded`
- `rfp.time_to_first_draft_ms`

## How to scaffold from this reference
1. Paste relevant sections into `docs/discovery/solution-brief.md`.
2. `/scaffold-from-brief`.
3. `/add-worker-agent` for each of Pricing, Legal, Technical, SecurityQ, Reference (or rename existing workers).
4. `/add-tool` for `dms_upload_draft`, `flag_deviation`, `request_sme_input`.
5. Build the past-proposal index in `infra/modules/ai-search.bicep` with proper row-level security.
6. Write 20+ golden cases = real past RFPs with expert-reviewed answers.
