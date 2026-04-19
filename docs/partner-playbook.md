# Partner Playbook — Azure Agentic AI Solution Accelerator

> **Audience:** partner delivery lead, partner engineers, partner architects.
> **Companion docs:** [`supported-customization-boundary.md`](supported-customization-boundary.md), [`rai/attestation-scope.md`](rai/attestation-scope.md), [`../compatibility/upgrade-transaction-model.md`](../compatibility/upgrade-transaction-model.md), [`governance/governance-board-charter.md`](governance/governance-board-charter.md).
> **Companion chat mode:** `.github/chatmodes/delivery-guide.chatmode.md` — use it in VS Code; it reads this playbook's phase front-matter.

This is a **single-track, phase-gated playbook**. One workflow for all engagements. Different customers move through it at different velocities, but the phases and gates are identical. No role-split "SA track vs engineer track" — different skills show up in different phases.

The playbook sits beside — not inside — [reference docs](supported-customization-boundary.md). When a phase needs deep reference, it links out.

---

## 0. Paths at a glance

| Path | Bundle(s) | What it gets you | Qualification bar |
|---|---|---|---|
| **Path A — Sandbox / guided-demo** | `sandbox-only` | Demos, POCs, certification dry-run | Ack of limits + sandbox isolation (see §6) |
| **Path B — Enterprise (first production)** | `retrieval-prod`, `retrieval-prod-pl`, `actioning-prod`, `actioning-prod-pl` | Attested production deployment | Full `.qualification.yaml` + GitHub review + Rekor entry |
| **Path C — Expansion** | As Path B, for existing customer | Additional agents / tools / grounding on top of prior Path B | Prior valid attestation + new qualification for expansion scope |

---

## 1. Phase 1 — Exec intro

**Entry criteria:** a customer sponsor has agreed to a 30-minute intro.

**Decisions:**
- Is this a real agentic AI opportunity or a traditional workflow?
- Is the customer willing to commit to either Path A (sandbox) or the qualification bar of Path B?

**Outputs:**
- 1-page engagement brief in `docs/engagement-brief.md`
- Bundle shortlist (1–2 candidates)
- Proposed path (A / B)

**Sign-off:** customer sponsor + partner delivery lead email ack. Not a legal document.

**Aids:** `docs/templates/exec-intro-deck.md` (skeleton), `discovery/use-case-canvas.md`.

---

## 2. Phase 2 — 60-minute quickstart (sandbox-only, guarded)

> ⚠️ **LOUD LABEL.** The 60-minute quickstart runs in the `sandbox-only` bundle **only**. It is NOT a replacement for qualification. It does NOT produce an attestation. Nothing built here may move to production without completing Phase 3 (Qualify) and later phases.

**Entry criteria:**
- Phase 1 exec intro complete.
- Partner has a dedicated sandbox Azure subscription **or** MG-scoped policy assignment (per `supported-customization-boundary.md` §2, referencing plan §6).
- Guided-demo fallback accepted in writing if dedicated isolation not available.

**Decisions:**
- Which reference scenario to demonstrate (supplier-risk / itops-triage / knowledge-concierge)?
- Which customer-facing failure mode to show (HITL rejecting a bad tool call, cost ceiling hit, red-team eval trigger)?

**Outputs:**
- Running demo in sandbox subscription.
- Customer-witnessed run of at least one supportability gate (eval regression, cost ceiling, kill switch, or HITL rejection).
- Post-demo memo: customer interest level, bundle candidate, estimated Path B qualification effort.

**Sign-off:** partner delivery lead signs that quickstart was completed AND that customer received the loud-label disclaimer in writing.

**Aids:** `packs/starter/`, azd templates under `azd-templates/sandbox-only/`.

**Explicit non-goals:**
- Not a reference implementation of the customer's production use case.
- Not a basis for "we'll just harden this later."
- No attestation issued. No support coverage beyond sandbox.

---

## 3. Phase 3 — Qualify (Path A ack OR Path B/C qualification)

### 3a. Path A ack (Sandbox/guided-demo only)

**Entry criteria:** Phase 2 complete.

**Decisions:**
- Continue on Path A indefinitely? (Valid, e.g., ongoing partner certification work.)

**Outputs:**
- `.qualification.yaml` with `path: A` + sandbox ack fields (no customer data, no "hours" claim unless partner-certified + assisted-first).

**Sign-off:** partner delivery lead.

### 3b. Path B/C qualification

**Entry criteria:** customer has agreed to engage on production.

**Decisions** (all required, each a decision record in `docs/decisions/`):
1. **Data classification** — customer-internal / confidential / restricted. Customer-CISO-delegate signs off.
2. **Network topology** — `prod-standard` or `prod-privatelink`. Drives bundle.
3. **Identity model** — customer-entra / customer-entra-b2b / partner-federated.
4. **RAI IA scoping** — scope of use cases, HITL points, groundedness thresholds, side-effect tools. Minutes in `rai/scoping-minutes.md`.
5. **Security review path** — customer-internal / joint / msft-assisted.
6. **Operating model** — partner-managed / customer-managed / joint.

**Outputs:**
- `.qualification.yaml` fully populated + validator-clean.
- GitHub PR with required CODEOWNERS reviews approved.
- OIDC-signed `qualify.yml` workflow run with Rekor UUID captured.
- Governance board notified for any high-severity waiver requests.

**Sign-off:**
- `prerequisites_signed_by` = partner-lead + customer-sponsor (both; validator enforces).
- Approval SHAs + numeric actor IDs recorded.

**Aids:** `discovery/qualification-matrix.md`, `discovery/rai-impact-assessment.md`, `docs/templates/decisions-template.md`, `docs/enablement/customer-github-onboarding.md` (if customer lacks GitHub org).

**Exit gate:** validator passes on `.qualification.yaml`; Rekor entry live; attestation-issue prerequisite met.

---

## 4. Phase 4 — Spec

**Entry criteria:** Phase 3 qualification complete (or Path A ack).

**Decisions:**
- Agent count (cap 2 for v1 a2a).
- Tool set (which are `side_effect: true`).
- Grounding sources (IDs, types, URL patterns, ACL models, classifications).
- KPIs + quality thresholds + cost ceiling + red-team eval set.

**Outputs:**
- `spec.agent.yaml` validated against `spec.schema.json`.
- RAI IA document with immutable UUID + 180d expiry.
- Materialized params + evals + dashboards + alerts files (DO-NOT-EDIT headers in place).
- Override companion files (`.override.yaml|json`) where the partner needs to extend.

**Sign-off:** partner delivery lead + customer-sponsor (CODEOWNERS on `spec.agent.yaml`).

**Aids:** `specs/examples/` (3 reference specs), `.github/chatmodes/delivery-guide.chatmode.md`.

**Exit gate:** `baseline validate-spec` green; materializers run clean; bundle↔profile pairing valid; side-effect tools paired with `actioning-*` bundle.

---

## 5. Phase 5 — Scaffold

**Entry criteria:** Phase 4 Spec validated.

**Decisions:**
- Customer repo location (customer org / partner org with customer CODEOWNERS team).
- azd template bundle path (`azd-templates/<bundle>/`).

**Outputs:**
- Customer repo created via `baseline new-customer-repo` (scaffolds structure + CODEOWNERS + workflows + azd template overlay).
- `baseline.lock.yaml` initialized.
- First CI run green (validator + pip-audit + cost-tag + preflight).
- Sandbox environment deployed via `azd up` in a non-prod subscription for local iteration.

**Sign-off:** partner engineer lead.

**Exit gate:** PR merged to `main` with initial scaffold; CI green; sandbox deploy reachable.

---

## 6. Phase 6 — Implement (vibecoding with Copilot)

**Entry criteria:** Phase 5 scaffold complete.

**Decisions:**
- Per-agent: prompt design (in Foundry portal), tool wrappers, grounding glue, transform/validate logic.
- Eval dataset content + red-team eval set.

**Outputs:**
- Agent modules under `src/agents/<agent>/` following the 4-file pattern (`prompt.py`, `tools.py`, `transform.py`, `validate.py`).
- Grounding pipelines wired to declared sources.
- Evaluation datasets under `evals/`.
- Unit + integration tests green.
- CI green including eval-regression-gate and red-team-evals.

**Sign-off:** partner engineer lead + partner delivery lead.

**Aids:** `.github/copilot-instructions.md`, `packs/<scenario>/` reference implementations, `patterns/architecture/`.

**Exit gate:** CI green on all supportability gates; `baseline reconcile` clean against sandbox deploy; RAI IA matches implementation.

---

## 7. Phase 7 — Attest

**Entry criteria:** Phase 6 implement complete.

**Decisions:**
- Capture window chosen (need to deploy within 24h of capture).
- Any drift flagged in `baseline reconcile`: accept (auto-adopt), reconcile (warn), or re-attest (block).

**Outputs:**
- `baseline attest --capture` → signed snapshot under `.baseline/snapshots/<ts>/`.
- `baseline attest --issue` → OIDC-signed in-toto attestation + Rekor UUID.
- Attestation ID recorded in `.baseline/attestations/<ts>.json` + `baseline.lock.yaml`.

**Sign-off:** partner delivery lead (automated by OIDC-signed workflow; human trigger via PR merge).

**Exit gate:** attestation issued; capture-to-deploy window open (24h).

See `docs/rai/attestation-scope.md` §4 for the full sequence.

---

## 8. Phase 8 — Deploy

**Entry criteria:** Phase 7 attestation issued; < 24h since capture.

**Decisions:**
- Canary percentage (default 10%).
- Traffic-shift cadence.
- Go / no-go at each canary stage.

**Outputs:**
- `baseline deploy --verify <attestation-id>` green.
- Bicep whatIf reviewed + merged.
- Canary revision deployed; health + eval-in-prod gates green.
- Traffic shifted; post-deploy reconcile fingerprint matches.

**Sign-off:** partner delivery lead + customer-sponsor (prod go-live).

**Exit gate:** 100% traffic on new revision; no open sev-1/sev-2 incidents; 24h stability observed.

---

## 9. Phase 9 — Day-2 customer ops handoff

> This phase is non-optional. Skipping it is the single most common cause of downstream escalation.

**Entry criteria:** Phase 8 deploy stable for 7 calendar days.

**Decisions:**
- Who holds the pager? (partner / customer / joint).
- Sev-1 drill schedule.
- Waiver register transfer (customer receives copy + active expiry dates).
- Baseline upgrade cadence ownership.

**Outputs:**
- Completed runbook walkthrough using `docs/runbooks/` (first-failure-modes, cost-excursion, eval-regression, portal-drift, HITL-backlog, kill-switch-trigger).
- Sev-1 tabletop exercise conducted + documented.
- Customer acknowledges `SUPPORT.md` intake workflow (attestation ID required).
- Customer-facing Day-2 ownership matrix in `docs/day2-ownership.md`.

**Sign-off:** partner delivery lead + customer-sponsor + customer-ops-lead.

**Exit gate:** customer-ops-lead acknowledges readiness to receive a sev-1 page.

---

## 10. Phase 10 — Shared deep reference (ongoing)

**Not a gated phase.** Pointers the engagement returns to throughout delivery + post-go-live:

- `docs/supported-customization-boundary.md` — invariants.
- `docs/rai/attestation-scope.md` — attestation lifecycle.
- `compatibility/upgrade-transaction-model.md` — upgrade semantics + emergency patch lane.
- `compatibility/drift-classification.yaml` — drift rules.
- `docs/governance/*` — waiver + board + logs.
- `patterns/waf-alignment/` — WAF pillar mapping.

---

## Cross-phase policies

### Waivers
Tracked in `.baseline/waivers.yaml`. Max 5 active. 90d expiry. Severity per rubric. See `governance/waiver-severity-rubric.md`.

### RAI IA refresh
180-day expiry. Refresh must happen BEFORE expiry; expired IA blocks any re-attestation.

### Security patches
Emergency lane: 7 calendar days partner adoption window. `baseline doctor` surfaces patch urgency.

### Support intake
Every ticket requires attestation ID. See `SUPPORT.md` + `docs/support-intake-workflow.md`.

### Bundle variants
Not field-approvable. Route through governance board per `supported-customization-boundary.md` §5.

---

## Velocity expectations (NOT SLAs)

Velocity varies materially by customer maturity. These are reference points, not commitments.

- **Path A sandbox** — hours IF partner-certified + dedicated isolation + assisted-first-deployment. Otherwise: days, no "hours" claim.
- **Path B first deploy** — weeks to months, dominated by qualification + security review cadence, not by accelerator velocity.
- **Path C expansion** — hours to days per expansion once qualified (validator-enforced prereqs).

The accelerator compresses the engineering phases, not the governance phases. If qualification takes 8 weeks, the accelerator cannot make it 8 days.
