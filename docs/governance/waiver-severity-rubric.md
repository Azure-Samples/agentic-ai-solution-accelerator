# Waiver Severity Rubric

> How we classify waiver requests. Example-based, not abstract.
> Used by validator + intake automation + Governance Board.

A **waiver** is a time-bounded, approved exception to an accelerator invariant (supportability gate, bundle rule, control-set requirement). Waivers appear in `baseline.lock.yaml`, are attestation-visible, and have a hard 90-day expiry SLA.

**Cap:** 5 active waivers per customer repo (provisional for v1). Above 5 → engagement flagged + auto-escalates to Governance Board.

---

## Severity classes

### LOW — CODEOWNERS approval sufficient
| Example | Why low |
|---|---|
| Alert threshold temporarily more permissive than baseline default (e.g., cost-alert threshold raised during a load test) | Config-level, reversible, no RAI/security impact |
| T3 reference-only dependency pinned to older version than current accelerator recommendation | T3 is out-of-scope for support; no attestation impact |
| Eval regression threshold relaxed by < 5% with explicit plan to close | Measurable, time-bound, no RAI tuple change |
| Cost tag compliance check skipped for a short-lived experimental resource group | Narrow scope, CI check only |

### MEDIUM — CODEOWNERS + partner delivery lead approval
| Example | Why medium |
|---|---|
| `baseline-feedback` telemetry disabled for a specific agent during investigation | Affects observability + posture signal, reversible |
| Portal-drift detection suspended for 7 days during a known migration | Narrow window; posture signal lost during window |
| RAI IA valid-until extended by < 30 days pending scheduled review | Time-bound; must not compound with other waivers |
| Non-PL profile used in a region where PL SKUs not yet GA | External constraint; requires documented remediation date |

### HIGH — Governance Board required
| Example | Why high |
|---|---|
| Side-effect tool deployed without full `baseline-hitl` wiring | Changes RAI tuple; material risk to customer data |
| `actioning-*` bundle downgraded to `retrieval-*` while side-effect tools still present | Bundle↔capability mismatch; attestation invariant |
| New grounding source onboarded with ACL model not in standard set | Identity + data-classification implications |
| Cost ceiling removed or set above customer-approved max | Customer trust; blast-radius risk |
| Kill-switch removed on a specific tool path | Material safety regression |
| `forward_fix_only: true` accepted on an emergency patch release | Normally prohibited for emergency lane |
| Customer subscription lacks dedicated sandbox isolation AND guided-demo labeling missed | §6 sandbox isolation violation |
| Qualification approver substitution via non-GitHub-review means | Breaks evidence binding in §7 |
| Rekor entry not produced due to sigstore outage + deploy proceeds | Breaks §7 cryptographic chain; degraded-mode only |

---

## What a waiver request MUST contain

1. **Invariant being waived** — exact citation (doc + section).
2. **Scope** — which repo, which bundle, which agent/tool/resource.
3. **Business reason** — why the engagement can't meet the invariant right now.
4. **Compensating control** — what's in place instead.
5. **Remediation plan + date** — how and by when the waiver will close.
6. **Severity assessment** — proposed class (low / medium / high) + rationale.
7. **Approver(s)** — per rubric above.
8. **Expiry** — max 90 days from issue.

---

## Auto-escalation triggers

The intake + validator automatically escalates to Governance Board when ANY of:

- Waiver is proposed LOW/MEDIUM but impacts RAI tuple, kill-switch, cost ceiling, HITL, or bundle-capability invariants (these are always HIGH).
- Active waiver count on repo ≥ 5.
- Any waiver older than 60 days AND not yet in renewal review.
- Repo has had ≥ 3 HIGH waivers in trailing 12 months (pattern).

---

## What waivers do NOT do

- Waivers do NOT extend RAI IA validity. IA expiry is independent.
- Waivers do NOT extend attestation freshness. 30-day attestation clock continues.
- Waivers do NOT backdate. Waiver coverage is from approval date forward.
- Waivers do NOT transfer across repos. A waiver for customer X does not apply to customer Y.
- Waivers do NOT survive baseline major version upgrades without re-approval.
