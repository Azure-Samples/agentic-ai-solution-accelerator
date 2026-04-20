# Architecture — flagship (sales research & outreach)

> Supervisor-routing topology on Microsoft Agent Framework + Azure AI Foundry. This is what `src/` implements out of the box.

## Agent graph

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

## Azure topology

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

## Data + control flow
1. Partner or customer invokes the API (`src/main.py`).
2. `sales_research_workflow` executes the supervisor with the request.
3. Supervisor classifies intent and dispatches to workers (parallel).
4. Workers ground via `retrieval/ai_search.py` and tools; return structured outputs.
5. Aggregator composes the final brief + outreach draft.
6. Any side-effect tool (CRM write, email send) passes `accelerator_baseline/hitl.checkpoint` first.
7. Telemetry events emitted to App Insights; KPI events drive ROI dashboards.

## Why this shape
- **Parallel specialists** reduce latency vs serial single-agent prompting.
- **Aggregator as executor** keeps composition logic out of worker prompts (easier to eval).
- **HITL at the edge** (not inside workers) means we can audit and change policy without retraining prompts.
- **Foundry-managed instructions** let non-engineers refine agent behavior via portal.
