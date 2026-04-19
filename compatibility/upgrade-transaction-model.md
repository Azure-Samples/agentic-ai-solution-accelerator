# Upgrade Transaction Model

> Normative specification of how baseline releases propagate into customer repos and deployed Azure state.
> **Audience:** accelerator engineers, partner leads, support intake automation.

---

## 1. Three transaction layers

Every upgrade touches up to three layers. Each has its own semantics.

| Layer | What changes | Transaction | Rollback |
|---|---|---|---|
| **Repo** | files, pinned versions, lockfile, CI workflows, schema files | **Atomic** (single PR; never mutates `main`) | Git revert of PR |
| **Deploy** | Azure resources via Bicep/azd (Container Apps revisions, KV access policies, Foundry tool bindings, App Config keys, alert rules, Action Groups) | **Best-effort staged:** Bicep whatIf → canary revision → traffic shift → promote | Prior revision pointer + Bicep replay of last good lockfile; automated within 24h grace |
| **Data / external state** | AI Search index schema, eval dataset versions, Foundry-portal-owned state, SharePoint ACL changes, connector configs, secrets rotation | **NOT transactional.** Expand-contract required (§4). | Forward-fix-only; no data-level rollback. |

The accelerator does **not** pretend data migrations are transactional.

---

## 2. Lockfile

Every customer repo carries `baseline.lock.yaml` — the source of truth for "what release am I on, across all components":

```yaml
baseline_release: "1.2.0"
components:
  core_pkg: "1.2.0"
  bicep_modules: "1.2.0"
  workflows: "1.2.0"
  schema: "0.2.0"
  profile_required:
    baseline-drift: "1.2.0"
    baseline-feedback: "1.2.0"
  reference:
    baseline-cache: "1.1.0"
bundle: "retrieval-prod"
sbom_hash: "sha256:..."
signed_by: "sigstore:github.com/Azure/agentic-ai-solution-accelerator"
migration_state:
  last_applied: "1.2.0"
  pending_migrations: []        # non-empty blocks re-attestation
  expand_phase_complete: true
  contract_phase_complete: true
```

Lockfile history is preserved under `.baseline/history/<release>.yaml` for rollback.

---

## 3. CLI commands

### 3.1 Visibility
- `baseline doctor` — drift visibility only; reports current vs latest supported; flags security patches.
- `baseline reconcile` — compares deployed Azure state vs attested lockfile; emits classified drift report.
- `baseline reconcile --pre-upgrade` — same but focused on an upgrade target.

### 3.2 Upgrade
- `baseline doctor --preflight <target>` — compatibility check for a specific target release: schema diff, breaking changes, waiver validity, RAI IA expiry, data-migration requirements.
- `baseline upgrade --plan <target>` — dry-run. Emits a plan artifact with exact changes + warnings. **No file changes.**
- `baseline upgrade --apply <plan-artifact>` — stages all changes in a single PR branch; runs validator + preflight gates; opens PR. **Never mutates `main`.**
- `baseline upgrade --rollback` — repo rollback + deploy rollback to prior revision. **Refuses** if any migration's contract phase has run.

### 3.3 Migration
`baseline migrate` is an **orchestrator + ledger, NOT an executor.**

- `baseline migrate --plan <target>` — lists documented partner runbooks required.
- `baseline migrate --apply` — prompts partner interactively per step; records each step's completion (actor, timestamp, evidence ref, run URL) in `.baseline/migrations/<release>.ledger.yaml`; refuses to proceed until prior steps are ledgered.
- `baseline migrate --status` — shows ledger state.

Baseline NEVER invokes destructive migration operations itself. Partner runs documented runbooks; baseline enforces ledger completeness before `upgrade --apply` proceeds.

---

## 4. Expand-contract migration policy

Any schema or data change ships across **two releases**:

- **Release N (expand):** new shape added, old shape preserved; code tolerant of both.
- **Release N+1 (contract):** old shape removed; gated by telemetry proof that traffic has migrated (`min_traffic_age_before_contract_days` in release manifest, default 14).

### Consequences
- Rollback permitted **one** release (within expand window).
- Rollback **refused** across contract boundary — `baseline upgrade --rollback` detects + rejects.
- Non-migratable changes (rare, e.g., Foundry SDK hard break) ship with `forward_fix_only: true` + explicit runbook.
- Emergency security patches **disallowed** from containing contract-phase or `forward_fix_only` changes. If an emergency fix requires those, it ships as an expand-only patch release followed by a regular contract release.

---

## 5. Drift classification at upgrade time

`reconcile --pre-upgrade` classifies each drift finding:

| Class | Meaning | Upgrade behavior |
|---|---|---|
| `block` | Breaks attested RAI tuple, security posture, or supported-bundle invariants (e.g., side-effect tool added via portal, network profile changed, model swapped) | **Blocks upgrade** until reconciled (re-attested with updated Spec or reverted in Azure) |
| `warn` | Non-security drift, config-level only (e.g., App Config scale setting changed via portal) | Upgrade proceeds; warning logged; attestation records drift adopted |
| `auto-adopt` | Baseline-expected reconciliation (e.g., Foundry auto-upgrade of connector minor version) | Silent; lockfile records new state |

Classification rules are defined in `compatibility/drift-classification.yaml`, versioned per release, signed.

---

## 6. Apply order (fixed)

1. Schema version
2. `baseline` core pkg
3. Profile-required sub-pkgs (T2)
4. Delivery assets (Bicep modules, workflows)
5. Lockfile commit

Repo-atomic. All in one PR; either merges or doesn't.

---

## 7. Loud forward-fix-only UX

- `baseline upgrade --plan` output surfaces a banner at the top:

```
⚠ ⚠ ⚠  NO ROLLBACK PAST CONTRACT BOUNDARY  ⚠ ⚠ ⚠
This upgrade contains the contract phase of migration XYZ-001.
After apply, `baseline upgrade --rollback` will refuse.
Manual recovery procedure: docs/runbooks/XYZ-001-recovery.md
```

- Banner repeated in the generated upgrade PR description.
- PR template has a required acknowledgement checkbox signed by CODEOWNERS before merge.
- `baseline upgrade --apply` refuses unless the plan-artifact banner acknowledgement is present in PR metadata.

---

## 8. Release rings (two layers)

### Layer 1: MSFT-controlled release readiness rings
Owner: **accelerator release manager** (MSFT engineering).

- **Ring 0 — internal:** MSFT-owned reference repos (3 scenarios). 72h soak minimum.
- **Ring 1 — pilot:** MSFT + 2–3 certified lighthouse partners (opt-in). 1-week soak.
- **Ring 2 — general:** published to private feed as **Supported**.

Release manifest records current ring in `ring_status`.

### Layer 2: Partner-controlled adoption waves
Owner: **partner delivery lead** for each customer repo.

- Partners choose when to upgrade within support window = **current release ± 2 minor versions**.
- `baseline doctor` surfaces target ring_status.
- Partners MAY opt-in to ring 1 via `.baseline/adoption.yaml` — earns extra support engagement, carries canary risk.
- Running > 2 minor behind = attestation freshness lapses = support lapses.

MSFT does not dictate partner upgrade schedules; partners don't dictate MSFT promotion cadence.

### Layer 3: Emergency security patch lane (NORMATIVE)

Triggered when a release is flagged `security_patch: critical` (CVE w/ exploitability, cryptographic compromise, tenant-isolation bypass).

- **MSFT side:** ring 0 → ring 2 within **24h** with governance board sign-off recorded in release manifest.
- **Partner side:** adoption window compresses to **7 calendar days** from ring 2 publication. Partners who do not adopt lose attestation freshness and are notified by intake automation.
- Emergency patches may **not** contain contract-phase or `forward_fix_only` changes.
- Partner adoption of security patches is **mandatory within 7 days** regardless of current release position.

---

## 9. Attestation lifecycle across upgrades

- Attestation is tied to `SHA256(lockfile + snapshot)`.
- **On upgrade apply:** attestation enters **24h grace window** (old attestation valid); new attestation required from new lockfile + post-upgrade reconcile.
- **On rollback within grace:** prior attestation restored only if repo + deploy + migration state all match prior lockfile.
- **Past contract boundary:** no attestation rollback path; must re-attest forward.

Full sequencing in `docs/rai/attestation-scope.md`.

---

## 10. Release manifest schema

`compatibility/releases/<version>.yaml` per release, signed via sigstore/cosign:

```yaml
version: "1.3.0"
ring_status: "pilot"                          # internal | pilot | general
security_patch: null                          # critical | null
expand_release: "1.3.0"
contract_release: "1.4.0"
breaking_changes:
  - id: "SCHEMA-BR-001"
    summary: "..."
    migration_ref: "docs/migrations/SCHEMA-BR-001.md"
forward_fix_only: false
min_traffic_age_before_contract_days: 14
drift_classification_version: "2026-04-01"
min_compat_release: "1.1.0"
max_compat_release: "1.3.0"
component_versions:
  core_pkg: "1.3.0"
  bicep_modules: "1.3.0"
  workflows: "1.3.0"
  schema: "0.2.0"
  baseline-drift: "1.3.0"
  baseline-feedback: "1.3.0"
  baseline-hitl: "1.3.0"
  baseline-actions: "1.3.0"
sbom_ref: "sbom/1.3.0.spdx.json"
```

---

## 11. Failure-recovery matrix

| Failure | Recovery |
|---|---|
| `upgrade --plan` shows `block` drift | Reconcile first: re-attest with updated Spec, or revert portal changes |
| `upgrade --apply` PR fails validator | Fix + push to branch; apply refuses until green |
| Bicep whatIf shows destructive change | Review with partner lead; may require expand-contract sequencing |
| Canary deploy unhealthy | Revision-pointer rollback; re-plan |
| Post-deploy reconcile fingerprint mismatch | Re-attest from deployed state OR revert |
| 24h grace window elapsed without re-attest | Attestation lapses; next deploy-gate refuses until fresh attestation |
| Migration ledger step skipped | `upgrade --apply` refuses until ledgered |
| Contract-phase applied, rollback requested | Refused; execute forward-fix runbook |
| Emergency security patch with contract change | Bug in release process; patch rejected; must re-ship as expand-only patch + follow-on contract |
