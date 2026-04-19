# Supplier Risk Triage — primary reference scenario

> **Customer:** Acme Manufacturing (fictitious)
> **Bundle:** `retrieval-prod`
> **Pattern:** B (2-agent a2a retrieval)
> **Example Spec:** [`examples/specs/acme-supplier-risk.agent.yaml`](../../specs/acme-supplier-risk.agent.yaml)

## Business problem
Supplier risk team triages 100+ supplier disclosures per week. Each requires: pulling relevant policy excerpts, cross-referencing prior LoB decisions, scoring risk, drafting a triage memo.

## Agent topology (2 agents, a2a)
- `triage` — orchestrator; receives supplier disclosure; calls retriever; produces scored memo.
- `retriever` — pulls policies (SharePoint) + prior decisions (AI Search index) + Dun & Bradstreet extracts.
- No side-effect tools; all retrieval. No HITL required (no actions being taken).

## Grounding
- SharePoint: `/sites/procurement/Shared Documents/suppliers/.*` — ACL-inherited (customer Entra).
- AI Search: `supplier-news-v2` — customer-RBAC gated.
- REST: Dun & Bradstreet internal extract API — partner-managed connection.

## Tools
All retrieval-only:
- `supplier-dossier-lookup` (SharePoint)
- `supplier-news-search` (AI Search)
- `dnb-extract-fetch` (REST)

## What to study in this reference (when Phase D ships the full implementation)
- Spec authoring pattern → see the companion Spec at `examples/specs/acme-supplier-risk.agent.yaml`.
- Agent module layout: `src/agents/triage/`, `src/agents/retriever/`.
- Eval suite + red-team probes: `evals/`.
- Materialized alerts + dashboards (DO-NOT-EDIT headers, override companions).
- ACL-respecting retrieval glue (caller identity, not app MI).

## Phase A status
This scenario ships as a README + Spec only. Full runnable implementation lands in Phase D.
