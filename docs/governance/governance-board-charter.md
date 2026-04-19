# Governance Board Charter

> Authority body for the Azure Agentic AI Solution Accelerator.
> Supersedes informal waiver / exception discussions.

---

## 1. Purpose

The Governance Board is the single authority for:

- Approving **high-severity waivers** (per `waiver-severity-rubric.md`).
- Approving **new blessed bundles** (§3.1 of plan; changes to the 5-bundle matrix).
- Approving **T3 → T2 promotion** requests (e.g., cache).
- Approving **BYO-IaC re-qualification packages** (§4 of `supported-customization-boundary.md`).
- Approving **emergency security patch lane** ring 0 → ring 2 promotion.
- Adjudicating **degraded-mode escalations** (support tickets > 72h in degraded queue).
- Ratifying decisions taken under **disaster fallback** (§5 below).

---

## 2. Composition

| Seat | Org | Term |
|---|---|---|
| Accelerator engineering lead | MSFT (smb-agentic-ai-champs / accelerator-eng) | 12 months, renewable |
| Partner delivery lead | MSFT (partner-delivery) | 12 months, renewable |
| MSFT field CTO representative | MSFT (field CTO org) | 12 months, renewable |

Each seat has a **named backup** who may sign in lieu of the primary. Decisions require 2-of-3 (any combination of primary + backup).

---

## 3. Quorum + decision rules

- **Quorum:** any 2 of 3 seats (primary or backup).
- **Decisions:** majority of quorum. Tie impossible with quorum=2 or 3.
- **High-severity waivers:** unanimous within quorum required.
- **New blessed bundle:** unanimous across all 3 seats required (no quorum shortcut).

Decisions logged in `board-decision-log.md` within 2 business days of decision.

---

## 4. SLAs

| Request type | Decision SLA |
|---|---|
| High-severity waiver | 5 business days |
| Emergency security patch promotion | 24 hours |
| Degraded-mode escalation | 24 hours |
| New blessed bundle request | 30 calendar days |
| BYO-IaC re-qualification | 5 business days for active lighthouse; 30 days otherwise |
| T3 → T2 promotion | Quarterly review cycle |

---

## 5. Disaster fallback

If all primaries AND all backups are unavailable simultaneously (org holiday, reorg, outage, etc.):

- Acting authority passes to the **MSFT accelerator engineering VP (or designated delegate)** for up to **10 business days**.
- All decisions taken under disaster fallback MUST be logged in `board-decision-log.md` with `fallback_authority: VP` flag.
- On reconstitution, the board **ratifies or overturns** each fallback decision in its next meeting. Overturned decisions trigger incident-log entries.

---

## 6. Operating cadence

- **Standing meeting:** bi-weekly, 60 minutes.
- **Standing agenda:** open waiver queue · pending escalations · drift-rule promotion candidates · adoption metrics review.
- **Ad-hoc:** convened within 5 BD for any high-severity waiver; within 24h for emergency patch.
- **Quarterly review:** T2/T3 scope, bundle matrix health, waiver sprawl metrics, intake SLO adherence.

---

## 7. Recusal

A board member recuses when the request under review is from their own partner engagement or team. A recusal does not break quorum if backup is available.

---

## 8. Publishing decisions

All decisions published in `docs/governance/board-decision-log.md`:
- Decision ID (YYYY-MM-DD-NN)
- Request type + requester
- Decision (approved / denied / deferred)
- Vote tally + recusals
- Effective date + expiry (for waivers)
- Link to supporting artifacts

**Visibility:** board-decision-log.md is visible to all partners onboarded to the accelerator. Incident-log.md is restricted to board + affected parties + MSRC.
