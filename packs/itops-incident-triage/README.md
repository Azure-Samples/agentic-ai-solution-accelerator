# IT Ops Incident Triage — secondary reference scenario

> **Customer:** Contoso (fictitious)
> **Bundle:** `actioning-prod`
> **Side-effect tools:** ServiceNow create-ticket, ServiceNow update-assignment-group.

## Business problem
Contoso IT Ops receives alerts from multiple monitoring tools. Agent triages incoming alert, correlates with active incidents, and either drafts a new ServiceNow ticket or updates an existing one — with HITL approval before mutation.

## Agent topology (2 agents, a2a)
- `classifier` — parses alert; identifies likely service + severity.
- `actioner` — correlates + drafts ticket; queues for HITL; executes on approval.
- HITL points: `actioner.before_create`, `actioner.before_update`.

## Grounding
- AI Search: `incident-history-90d`.
- ServiceNow read API: `incidents?active=true`.

## Tools
- `servicenow-create-ticket` (`side_effect: true`)
- `servicenow-update-assignment-group` (`side_effect: true`)
- `incident-history-search` (read)

## What to study
Everything in supplier-risk-triage, plus:
- `baseline-hitl` integration (approval queue, SLA, fallback behavior).
- `baseline-actions` wrappers (idempotency keys, audit trail, kill-switch wiring).
- Spec `tool.side_effect: true` patterns and validator enforcement.

## Phase A placeholder
Full runnable implementation ships in Phase D.
