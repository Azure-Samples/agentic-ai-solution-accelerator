# Supplier Risk Triage — primary reference scenario

> **Customer:** Acme Manufacturing (fictitious)
> **Bundle:** `retrieval-prod`
> **Path B qualification:** example `.qualification.yaml` under `specs/examples/acme-supplier-risk.yaml`.

## Business problem
Supplier risk team triages 100+ supplier disclosures per week. Each requires: pulling relevant policy excerpts, cross-referencing prior LoB decisions, scoring risk, drafting a triage memo.

## Agent topology (2 agents, a2a)
- `triage` — orchestrator; receives supplier disclosure; calls retriever; produces scored memo.
- `retriever` — pulls policies (SharePoint) + prior decisions (AI Search index).
- HITL point: `triage.before_action` — high-risk memos require reviewer approval before filing.

## Grounding
- SharePoint: `/sites/supplier-policies/.*` — ACL-inherited.
- AI Search: `supplier-risk-v3` — customer-RBAC gated.

## Tools
All retrieval-only (no side effects).

## What to study in this pack (Phase D)
- Spec authoring pattern (`specs/examples/acme-supplier-risk.yaml`).
- Agent module layout (`src/agents/triage/`, `src/agents/retriever/`).
- Eval suite + red-team probes (`evals/`).
- Materialized alerts + dashboards (DO-NOT-EDIT headers, override companions).

## Phase A placeholder
Full runnable implementation ships in Phase D (per authoring plan §13).
