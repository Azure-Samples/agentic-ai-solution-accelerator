# WAF Alignment — Per-Pillar Decisions for Azure Agentic AI

How each WAF pillar + the AI workload extension applies to solutions built on this accelerator. Decisions are opinionated for v1; partners customize within these rails.

Legend:
- 🟢 **In the box** — baseline / patterns / validator give you this.
- 🟡 **Partner customization** — pattern-guided; partner tunes per customer.
- 🔴 **Customer responsibility** — accelerator cannot own this.

---

## Reliability

| Decision | Posture | How |
|---|---|---|
| Circuit breaker on model + tool calls | 🟢 | `baseline.foundry_client` wraps with breaker + retry. |
| SSE streaming for long calls | 🟢 | `baseline.sse_streaming`. |
| Kill switch | 🟢 | `baseline.kill_switch` — trips on cost / error-rate / red-team regression. |
| Tool failure policy | 🟢 | Declared per tool in Spec; validator enforces retry-count bounds. |
| Eval regression gate in CI | 🟢 | Fails deploy if eval suite regresses > threshold. |
| Region pairing | 🟡 | Template stubs; partner picks customer-specific pair. |
| HA beyond single-region | 🟡 | Pattern-guided; partner configures per SLA. |
| DR RTO/RPO | 🔴 | Customer IR maturity. |

---

## Security

| Decision | Posture | How |
|---|---|---|
| Managed identity for all Azure access | 🟢 | Bicep profiles wire MI; no SAS, no SP secrets. |
| KV-backed secrets | 🟢 | Foundry connections reference KV; no inline creds allowed (validator). |
| Private link for confidential+ data | 🟢 | `*-pl` profiles. |
| Content filter locked at strict default | 🟢 | Bicep sets filter; validator detects relax attempts. |
| XPIA / prompt-injection sanitization | 🟢 | `baseline.content_sanitization` on tool outputs. |
| pip-audit in CI | 🟢 | Workflow template. |
| Portal-drift detection | 🟢 | `baseline-drift` T2, required in prod profiles. |
| Data classification enforcement | 🟡 | Spec declares; validator enforces tool catalog + profile coupling. |
| Egress restriction / customer DLP integration | 🔴 | Customer network team. |
| Customer Entra tenancy model | 🔴 | Customer identity team. |

---

## Cost Optimization

| Decision | Posture | How |
|---|---|---|
| Per-request + per-session cost tracking | 🟢 | `baseline.cost_tracker`; emits to App Insights. |
| Cost ceiling + kill switch | 🟢 | Spec `cost_ceiling.monthly_usd` + `kill_switch_threshold_pct`; materialized into alerts. |
| Mandatory cost tags | 🟢 | Bicep profiles; `cost-tag-compliance.yml` CI check. |
| Teardown for sandbox | 🟢 | `dev-sandbox` profile auto-tags for teardown. |
| Model tier selection | 🟡 | Pattern-guided; Spec declares; override by profile. |
| AI Search tier vs QPS | 🟡 | `docs/cost-sizing-workbook.xlsx` (Phase D). |
| FinOps maturity + chargeback | 🔴 | Customer finance. |

---

## Operational Excellence

| Decision | Posture | How |
|---|---|---|
| Spec-driven solution definition | 🟢 | Single source of truth. |
| Eval-as-deploy-gate | 🟢 | CI fails deploy if eval regresses. |
| Telemetry via baseline schema | 🟢 | `baseline.telemetry`; materialized dashboards. |
| Runbook templates for common incidents | 🟢 | `docs/runbooks/` (Phase D). |
| Foundry portal drift telemetry | 🟢 | `baseline-drift`. |
| Feedback capture + eval dataset refresh | 🟢 | `baseline-feedback` T2. |
| Customer ops handoff (day-2 ownership matrix) | 🟡 | Template; partner completes per engagement. |
| Customer IR process | 🔴 | Customer ops. |

---

## Performance Efficiency

| Decision | Posture | How |
|---|---|---|
| Streaming responses | 🟢 | SSE by default. |
| Cold-start mitigation | 🟢 | Container Apps min-replicas pattern in Bicep profiles. |
| APIM in front of agent endpoint | 🟢 | Optional module; pattern guidance in `content/patterns/`. |
| Cache for repeated retrievals | 🟡 | `baseline-cache` T3 **reference only**. KPI SLOs must NOT depend on cache hit rate. |
| Parallel tool-call orchestration | 🟡 | Pattern-guided; limited by 2-agent cap. |
| Customer capacity planning | 🔴 | Customer infra team + Azure support. |

---

## AI workload / RAI

| Decision | Posture | How |
|---|---|---|
| RAI Impact Assessment required | 🟢 | Spec `rai.impact_assessment_ref` with expiry; refresh cadence 180d. |
| Groundedness threshold (default 0.7) | 🟢 | Baseline wires eval + threshold gate. |
| HITL for every side-effect | 🟢 | Hard invariant: actioning bundle → `baseline-hitl` required. |
| Red-team eval suite in CI | 🟢 | Default suite ships; `evals.redteam.pass_threshold` in Spec. |
| Content filter locked strict | 🟢 | Bicep + validator. |
| Grounding source ACL respect | 🟢 | Spec `acl_model` declared per source. |
| Eval dataset refresh | 🟡 | Pattern-guided; partner owns cadence. |
| Residual prompt injection on novel attacks | 🔴 | Industry-wide unsolved. Mitigation: defense-in-depth (sanitization + HITL + kill switch + red-team). |
| Model choice / evaluation for the specific domain | 🟡 | Spec declares; partner validates via evals. |

---

## Explicitly out of scope for v1
- Sovereign cloud.
- Multi-tenant control plane.
- Signed bundles / cryptographic attestation of customer repo content (community support model — no runtime gating).
- Terraform first-class support (BYO-IaC is fine — match the contracts).
- .NET / Java baseline (v1.5).
- \> 2-agent orchestration.
- Free-form a2a (bring-your-own orchestration frameworks).
