# Architecture patterns

What the accelerator ships today, and the shapes a partner can reasonably customise into.

---

## Flagship topology (what `azd up` deploys)

**Pattern — supervisor routing, 4 specialists (grouped in 2 workstreams), retrieval-backed, HITL for side-effects.**

```
  user → POST /research/stream
            │
            ▼
   ┌─────────────────────┐
   │ Supervisor agent    │  (accel-sales-research-supervisor)
   └─────────────────────┘
            │   plans + routes
            ├───────────────────────────────────────────┐
            ▼                                           ▼
   ┌─────────────────────┐                 ┌───────────────────────┐
   │ Account Researcher  │                 │ ICP Fit Analyst       │
   │ Competitive Context │                 │ Outreach Personaliser │
   └─────────────────────┘                 └───────────────────────┘
            │                                           │
            └──────────────── grounded via ─────────────┘
                                 │
                                 ▼
                   ┌────────────────────────────┐
                   │ Azure AI Search (accounts) │   <-- seeded at postprovision
                   │ Web search (allow-listed)  │
                   └────────────────────────────┘
```

Code pointers:

- Workflow: `src/scenarios/sales_research/workflow.py`
- Agents (prompt / transform / validate trio): `src/scenarios/sales_research/agents/<agent>/`
- Retrieval: `src/retrieval/ai_search.py` + scenario index schema in `src/scenarios/sales_research/retrieval.py`
- Endpoint binding: `src/main.py` reads `accelerator.yaml` and mounts `/research/stream` via `src.workflow.registry.load_scenario`
- Tools (side-effect, HITL-gated): `src/tools/`

> See **[Flagship implementation detail](#flagship-implementation-detail)** at the bottom for the full agent graph (including the aggregator + HITL gate), Azure topology, and step-by-step control flow.

---

## Invariants the lint enforces

`scripts/accelerator-lint.py` is the authoritative contract. Partners must not violate:

| Invariant | Rule |
|---|---|
| Agent instructions live in Foundry portal, not code | `agent_specs_no_hardcoded_model`, spec + prompt modules reference by Foundry agent name |
| `accelerator.yaml` resolves to importable modules | `manifest_imports_resolve` |
| Every side-effect tool has a HITL checkpoint | `tool_registers_hitl` |
| Retrieval index schema matches Bicep | `search_index_schema_matches_bicep` |
| Content filter in Bicep (not portal) | `content_filter_iac_only` |
| No key-based secrets in code | `no_inline_credentials`, `kv_references_only` |
| SDK matrix cannot drift from GA | `sdks_pinned_to_ga`, `dockerfile_matches_ga_pins` |
| Container image ships the manifest | `dockerfile_copies_manifest` |

Run `python scripts/accelerator-lint.py` locally; CI runs the same thing.

---

## Variations a partner can choose

These are **candidate patterns**, documented — not drop-in packages. Switching requires re-authoring the scenario under `src/scenarios/<new-id>/`. See `.github/chatmodes/switch-to-variant.chatmode.md` for guidance.

| Variant | Where it lives today | When to reach for it |
|---|---|---|
| **Supervisor routing** | Flagship (`src/scenarios/sales_research/`) | Research / multi-facet briefing. Default. |
| **Single-agent retrieval** | Candidate: `patterns/single-agent/README.md` | Doc Q&A, policy lookup — one agent + retrieval, no side-effects. |
| **Chat-with-actioning** | Candidate: `patterns/chat-with-actioning/README.md` | Conversational UX over multi-turn tool use; HITL still gates every side-effect. |

Raising past 3–5 coordinated workers is out of scope for v1 — evaluation surface and HITL coordination get unmanageable. Split into separate engagements.

---

## Anti-patterns the lint or reviewers reject

| Anti-pattern | Why |
|---|---|
| Agent instructions in Python source | Instructions live in Foundry portal — code references by ID only. |
| Side-effect tool without HITL checkpoint | HITL is a hard invariant for every `side_effect_tools` entry in `accelerator.yaml`. |
| Inline SDK pins in `src/Dockerfile` | Source of truth is `pyproject.toml` + `ga-versions.yaml`; lint blocks. |
| Direct model SDK calls bypassing telemetry | Go through `agent_framework` clients so OTel + cost tracking stay live. |
| Grounding source without declared ACL posture | Declare it in `accelerator.yaml` or the scenario retrieval schema. |

---

## Out of scope for v1

- Sovereign cloud deployments
- Multi-tenant control plane
- Cryptographic attestation of partner-customised repos (community support model)
- Terraform first-class (BYO-IaC is fine; match the Bicep contracts)
- .NET / Java runtime parity (roadmap item)
- More than 5 coordinated agents

---

## Flagship implementation detail

Deeper walk of how the flagship scenario actually runs end-to-end in the customer's subscription. This is how the supervisor-routing pattern materialises in `src/scenarios/sales_research/` and the Bicep under `infra/`.

### Agent graph (flagship, as shipped)

```
            ┌───────────────────────────────────┐
            │         Supervisor agent          │
            │  (intent + parallel routing)      │
            └───────────────────────────────────┘
              │        │          │          │
     ┌────────┘   ┌────┘     ┌────┘     ┌────┘
     ▼            ▼           ▼           ▼
┌──────────┐ ┌───────────┐ ┌────────────┐ ┌─────────────────┐
│ Account  │ │ ICP / Fit │ │Competitive │ │     Outreach    │
│Researcher│ │  Analyst  │ │  Context   │ │   Personalizer  │
└──────────┘ └───────────┘ └────────────┘ └─────────────────┘
     │            │           │                   │
     └────────────┴───────────┴───────────────────┘
                          ▼
                  ┌───────────────┐
                  │  Aggregator   │  assembles sales brief + outreach draft
                  └───────────────┘
                          ▼
             ┌──────────────────────────┐
             │ HITL gate: CRM write /   │
             │           email send     │
             └──────────────────────────┘
                          ▼
            (crm_write_contact, send_email)
```

### Azure topology (deployed by `azd up`)

```
┌─────────────────────── Customer subscription ──────────────────────┐
│                                                                    │
│   Container Apps (API + worker)                                    │
│     ├── Managed Identity ─────────────────────────┐                │
│     ├── uses DefaultAzureCredential               │                │
│     └── emits OpenTelemetry → App Insights        │                │
│                                                   │                │
│   Azure AI Foundry project ◀──────────────────────┤                │
│     agents retrieved by name; instructions in portal               │
│     content filters applied via IaC                                │
│                                                   │                │
│   Azure AI Search ◀───────────────────────────────┤                │
│     index: accounts, past-touches, competitive                     │
│                                                   │                │
│   Azure Key Vault ◀───────────────────────────────┤                │
│     secrets for CRM, SMTP, misc external systems                   │
│                                                   │                │
│   Application Insights + Log Analytics                             │
│     dashboards: roi-kpis, hitl-activity, cost-attribution          │
│                                                                    │
│   (optional) Private Endpoints — required for regulated workloads  │
└────────────────────────────────────────────────────────────────────┘
```

### Data + control flow

1. Partner or customer invokes the API (`src/main.py`).
2. `src/scenarios/sales_research/workflow.py` executes the supervisor with the request.
3. Supervisor classifies intent and dispatches to workers (parallel).
4. Workers ground via `retrieval/ai_search.py` and tools; return structured outputs.
5. Aggregator composes the final brief + outreach draft.
6. Any side-effect tool (CRM write, email send) passes `accelerator_baseline/hitl.checkpoint` first.
7. Telemetry events emitted to App Insights; KPI events drive ROI dashboards.

### Why this shape

- **Parallel specialists** reduce latency vs serial single-agent prompting.
- **Aggregator as executor** keeps composition logic out of worker prompts (easier to eval).
- **HITL at the edge** (not inside workers) means we can audit and change policy without retraining prompts.
- **Foundry-managed instructions** let non-engineers refine agent behavior via portal.
