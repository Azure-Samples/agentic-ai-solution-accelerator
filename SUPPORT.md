# Support

## Scope

Microsoft and partner support is honored **only** for engagements meeting **all** of:

1. **Current valid attestation** — issued < 30 days ago from a signed snapshot (< 24h live-state capture window at deploy).
2. **Deployed state matches attested lockfile** — verified by `baseline reconcile`.
3. **Active waivers approved and unexpired** — max 5 per repo, 90-day SLA.
4. **Bundle listed in blessed matrix** — see `docs/supported-customization-boundary.md` §2.

Tickets without a valid attestation ID are **rejected at intake**.

## Support tiers

| Tier | Components | Support posture |
|---|---|---|
| **T1** | `azure-agentic-baseline` core pkg, delivery assets, azd templates for blessed bundles | Full MSFT + partner support |
| **T2** | `baseline-drift`, `baseline-feedback`, `baseline-hitl`, `baseline-actions` (within bundle where required) | Full support when bundle is blessed |
| **T3** | `baseline-cache`, `examples/`, community patterns | Best-effort, community-tier, **not** covered by attestation |

## Degraded mode

If MSFT validation backend (attestation verifier, reconcile API) OR external dependencies (GitHub API, sigstore Rekor) are unreachable > 5 minutes, tickets are **queued**, not rejected. Validation runs on recovery.

Degraded-mode tickets > 72h auto-escalate to the Accelerator Governance Board for manual review (24h SLA).

## Sev-1 security emergency lane

Tickets flagged `sev-1-security` bypass attestation freshness and reconcile checks. Signature still verified if available. Manual-review queue, 4h SLA. Post-incident reconciliation required within 7 days or attestation lapses.

## What support does NOT cover

- Business logic written by the partner (vibecoded per customer).
- Non-blessed bundle combinations.
- Forks of T1/T2 packages.
- Partner-authored azd templates outside the shipped five.
- Grounding content quality or drift (use `baseline-drift` telemetry; see `docs/rai/attestation-scope.md`).
- Customer's own Azure subscription policies / landing zone (partner + customer responsibility).

## Opening a ticket

Every ticket must include:

- **Attestation ID** (required; else rejected)
- **Bundle** and **profile**
- **Baseline release** (from `baseline.lock.yaml`)
- **Reproduction steps**
- **Last successful reconcile timestamp**

See `docs/runbooks/support-intake-workflow.md`.

## SLA

**None outside attested engagements.** This is a controlled-lighthouse v1; broad-partner commercial SLA is v1.5+.
