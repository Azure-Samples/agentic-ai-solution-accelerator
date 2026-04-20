# Solution Brief — <Customer>

> This document is the **canonical source of truth** for this engagement. Every downstream artifact (agent prompts, tools, retrieval, HITL, evals, telemetry, manifest) derives from it. Fill it with the customer during discovery (`/discover-scenario`), then run `/scaffold-from-brief` to apply it across the repo.

**Engagement:** `<customer-slug>`
**Status:** Draft / Reviewed / Approved
**Last updated:** `<YYYY-MM-DD>`

---

## 1. Business context
- **Industry / segment:**
- **Customer name + size:**
- **Executive sponsor:**
- **Decision maker:**
- **Problem statement (one sentence):**
- **In scope:**
  - …
- **Out of scope (explicit):**
  - …

## 2. Target users & journeys
- **Primary persona:** (role · daily workflow · tools they live in)
- **Secondary persona (if any):**
- **Top 3 user journeys:**
  1. …
  2. …
  3. …

## 3. Success criteria (measurable)
| Metric | Current | Target | How measured |
|---|---|---|---|
| Time per task |  |  |  |
| Volume / throughput |  |  |  |
| Quality bar |  |  |  |

**Must-not-do guardrails:**
- …

## 4. ROI hypothesis
- **Baseline cost of status quo:** (FTE × rate, or $/transaction × volume)
- **Target savings ($/yr):**
- **Payback target:**
- **KPIs to instrument** (these become telemetry events in `src/accelerator_baseline/telemetry.py` and charts in `infra/dashboards/roi-kpis.json`):

| KPI event name | Type | Baseline | Target |
|---|---|---|---|
| `e.g. review_completion_time_ms` | duration_ms |  |  |
| `e.g. escalation_rate` | ratio |  |  |

## 5. Solution shape
- **Pattern:** supervisor-routing / single-agent / chat-with-actioning
- **Rationale:**
- **Grounding sources:** SharePoint / SQL / APIs / blob / other
- **Side-effect tools (list every one):**

  | Tool name | External system | Operation | Reversible? | HITL policy |
  |---|---|---|---|---|
  |  |  |  |  |  |

- **Out-of-scope tools (explicit):**

## 6. Constraints & risks
- **Data residency:** US / EU / APAC / custom
- **Identity:** Entra ID / External ID / custom
- **Compliance regime:** SOC 2 / GDPR / HIPAA / PCI / none / custom
- **RAI risks (3–5 specific to this scenario; become redteam cases):**
  1. …
  2. …
  3. …

## 7. Acceptance evals
| Gate | Threshold | Wired to |
|---|---|---|
| Quality (golden agreement) |  | `evals/quality/golden_cases.jsonl` |
| Groundedness |  | `evals/quality/` |
| Safety (redteam) | must pass | `evals/redteam/` |
| Latency (P50 ms / P95 ms) | / | App Insights |
| Cost per call ($) |  | cost attribution telemetry |

---

**Next step:** run `/scaffold-from-brief` in Copilot Chat to apply this brief across `src/`, `infra/`, `evals/`, `accelerator.yaml`, and `infra/dashboards/`.
