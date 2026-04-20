# Architecture Patterns

Topology + orchestration patterns supported in v1. Partners pick one; the Spec's `topology` + `bundle` declare which.

## Hard constraints
- **Max 2 agents** in a2a topology (Spec `topology.a2a_cap <= 2`). Raising is not in v1.
- **HITL required** for every side-effect tool (bundle `actioning-*`).
- **Grounding sources** declared in Spec with id + type + acl_model + classification. No implicit sources.

---

## Pattern A — Single-agent retrieval
**When:** doc Q&A, policy lookup, customer-support triage, knowledge concierge. No side-effect tools.
**Bundle:** `retrieval-prod` or `retrieval-prod-pl`.

```
 user → [ agent: retriever/triage ]  → response
                 │
                 └── grounds on: AI Search index, SharePoint, REST
```

Simple to operate. Smallest blast radius. Start here if in doubt.

---

## Pattern B — 2-agent a2a retrieval
**When:** one agent orchestrates (understanding intent, routing, summarizing); one agent specializes (retrieving, reasoning over domain data). Keeps prompts focused + evals tractable.
**Bundle:** `retrieval-prod` or `retrieval-prod-pl`.

```
 user → [ orchestrator ] ──call──▶ [ specialist retriever ]
              ▲                             │
              └──────── response ◀──────────┘
                              grounds on: ...
```

Adds one a2a edge. Splits eval surface per agent. Use when a single agent's prompt becomes unmanageable.

---

## Pattern C — Single-agent actioning with HITL
**When:** the agent executes a side-effect (create ticket, send email, write to system of record). Must be human-approved at a defined point.
**Bundle:** `actioning-prod` or `actioning-prod-pl`.

```
 user → [ agent ]
            │
            ├── grounds on: ...
            │
            └── proposes action ──▶ [ HITL queue ] ──approved──▶ [ baseline-actions wrapper ] ──▶ target system
                                                     rejected
                                                         └──▶ audit + feedback
```

HITL point declared in Spec as `agent_id.before_action` (default) or `.after_action` / `.on_uncertainty`.

---

## Pattern D — 2-agent a2a with HITL
**When:** orchestrator + specialist + actioning. E.g., triage agent classifies incident → action agent proposes remediation → HITL approves → executor runs it.
**Bundle:** `actioning-prod` or `actioning-prod-pl`.

```
 user → [ orchestrator ] ──call──▶ [ action specialist ]
              ▲                             │
              │                             └── proposes ──▶ [ HITL ] ──▶ baseline-actions ──▶ target
              └─────── response ◀──────────────────────────┘
```

---

## HITL placement guidance
- **`before_action` (default, safest):** every side-effect is human-reviewed before execution. Use for high-impact actions, regulated domains, or when eval confidence is new.
- **`after_action`:** action executes; human reviews within SLA (e.g., reversible actions only, telemetry-first rollout).
- **`on_uncertainty`:** action executes below confidence threshold goes to HITL; above threshold goes direct. Requires mature confidence scoring + eval validation. Don't start here.

---

## Anti-patterns (validator rejects or strongly discourages)

| Anti-pattern | Why |
|---|---|
| > 2 agents in v1 | Explodes eval surface + HITL coordination. Split into separate engagements. |
| Side-effect tool in `retrieval-*` bundle | Validator fails: missing `baseline-actions` + `baseline-hitl`. |
| Agent instructions in Python | Instructions live in Foundry portal. Code references by ID. |
| Grounding source without `acl_model` | Validator fails. Customer must decide ACL model up-front. |
| Custom direct model SDK calls | Bypass cost/kill/telemetry primitives. Always go via `baseline.foundry_client`. |
| Inline credentials in tool `source` | Use `connection_name` → Foundry connection → KV-backed secret. |

---

## Choosing a pattern — decision flow

1. Any side-effect tool required? → **Pattern C or D** (actioning bundle).
2. Is one agent's prompt + tool set getting large or ambiguous? → **Pattern B or D** (2-agent).
3. Everything else → **Pattern A** (single-agent retrieval).

## Mapping patterns to reference scenarios

| Pattern | Reference scenario |
|---|---|
| A | [knowledge-concierge](../../../examples/scenarios/knowledge-concierge) |
| B | [supplier-risk-triage](../../../examples/scenarios/supplier-risk-triage) |
| C | (add in Phase D) |
| D | [itops-incident-triage](../../../examples/scenarios/itops-incident-triage) |
