# RAI Patterns — Content Filter, Groundedness, HITL, Red-Team

Posture for Responsible AI in v1. These are the defaults + patterns the accelerator encodes. Customization within these rails is fine; divergence needs a documented rationale.

---

## Principle 1 — Safety at the model boundary

- **Content filter locked at strict default** on every deployment. Bicep profile sets this; validator flags any relaxation.
- **Prompt injection / XPIA sanitization** on every tool output routed back to the model. `baseline.content_sanitization` handles this; bypassing it is a validator-blocking offense.
- **Jailbreak-resistant system instructions.** Snapshot from Foundry portal into `rai/snapshots/` on every change; attach hash to release notes.

---

## Principle 2 — Grounded responses with attribution

- **Every retrieval source declared in Spec** (`grounding.sources[]`) with `acl_model` + `classification`.
- **Grounding metadata surfaced to the user** where appropriate — source id, link, timestamp — so they can check the claim.
- **Groundedness threshold default = 0.7.** Measured by eval; below threshold is a regression that blocks deploy.
- **ACL model honored at query time.** The retrieval glue uses the caller's identity (customer Entra) when `acl_model: inherit-customer-entra` — NOT the app's MI. Pattern code in `examples/scenarios/` demonstrates.

---

## Principle 3 — Human in the loop for side-effects

Non-negotiable for `actioning-*` bundles:

- Every side-effect tool (`side_effect: true`) has a HITL approval point declared in Spec.
- HITL queue ships via `baseline-hitl` — approve / reject / escalate / annotate.
- Default placement is `before_action` (strongest). Weaker placements (`after_action`, `on_uncertainty`) need explicit partner + customer agreement + heightened telemetry.
- Approver identity is logged; rejected-but-forced actions are flagged.

---

## Principle 4 — Red-team evals in CI

- **Default red-team suite ships with baseline.** Covers:
  - Prompt injection (direct + indirect via tools + via grounding)
  - Jailbreak attempts
  - Tool abuse (calling tools in unintended orders / arguments)
  - Data exfiltration via response shaping
  - Bias + fairness probes
- Partners extend with domain-specific probes (e.g., "trick the banking agent into approving a bad loan").
- Pass threshold in Spec (`evals.redteam.pass_threshold`). Regression fails CI.
- Re-run on every Spec change, model change, tool-catalog change, instruction change.

---

## Principle 5 — Data classification discipline

| Classification | Examples | Profile |
|---|---|---|
| `public` | Marketing site Q&A | any |
| `internal` | Employee handbook bot | prod-standard OK |
| `confidential` | Customer records, supplier contracts | prod-privatelink strongly recommended |
| `highly-confidential` | Regulated data, PII at scale, medical | `prod-privatelink` + customer-internal security review required |

- **Tool catalog restricts** by `data_classification_max` + `allowed_in_profiles`.
- **Grounding source** must declare classification ≤ solution classification.
- **Customer signs off on classification** — partner can't decide unilaterally.

---

## Principle 6 — RAI Impact Assessment

- Required for any `prod-*` profile (Spec `rai.impact_assessment_ref`).
- Stored in customer repo under `rai/impact-assessment.md` (or equivalent) with:
  - Use case + users + stakeholders
  - Harms inventory + mitigations
  - Data flows + classification map
  - Residual risk acknowledgement signed by a named customer role
- **Expires in 180 days.** Material changes (model swap, tool add, topology change) expire it sooner.
- Approved via PR review with CODEOWNERS mapping to the customer + partner RAI roles.
- `content/patterns/rai/ia-template.md` provides a starting template (Phase B).

---

## Principle 7 — Transparency

- **Users know they're interacting with AI.** UI patterns in `examples/scenarios/` show the banner + guard rails.
- **Uncertainty is communicated.** "I'm not sure" beats confident-wrong; eval suites probe this.
- **Source attribution visible** on grounded responses.

---

## Anti-patterns

| Anti-pattern | Why it's bad |
|---|---|
| "We disabled the content filter to reduce false positives" | Makes the system unsafe + exits support scope. Use allow-lists at the app layer instead. |
| "We skipped HITL for a low-risk side-effect" | "Low-risk" is a design claim until evals + production data prove it. HITL stays. |
| "Groundedness threshold = 0.5 because eval is too strict" | Lower threshold means more hallucination shipped. Fix the eval; don't mask the risk. |
| "Red-team evals are too flaky; we skip them in CI" | Flakiness is a signal of real vulnerabilities. Fix the flake. |
| "IA expired mid-engagement; we'll renew after go-live" | Deploy gates on fresh IA. Renew first. |
| Agent instructions containing customer PII or secrets | Snapshot + log trail exposes them. Instructions reference, don't embed. |

---

## Where this lives in the repo

- Patterns + defaults: `content/patterns/rai/`
- IA template: `content/patterns/rai/ia-template.md` (Phase B)
- Red-team suite: ships with `azure-agentic-baseline` (`baseline.redteam_evals`)
- Enforcement: Spec schema + validator + CI eval gates
