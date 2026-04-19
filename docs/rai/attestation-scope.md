# Attestation Scope

> **Purpose:** define exactly what attestation DOES and DOES NOT cover, and the cryptographic sequencing that closes TOCTOU gaps.
> **Audience:** partner engineers, customer security reviewers, support intake, RAI council.

Attestation is the accelerator's mechanism for binding a deployed solution to a supportable, reviewable state. This doc is the authoritative scope statement.

---

## 1. What attestation binds

A valid attestation at deploy time asserts:

1. **The lockfile matches** a supported baseline release (`baseline.lock.yaml`).
2. **The RAI tuple** (§3) matches the captured live state.
3. **The bundle + profile** are a blessed combination.
4. **Supportability gates** have passed at capture time.
5. **Qualification** (Path B/C) is Rekor-verified + GitHub-review-backed.
6. **Deployed Azure state** matches the captured fingerprint at deploy-gate time.

The attestation subject is `SHA256(lockfile + snapshot)`. Attestations are OIDC-signed via GitHub Actions and published to sigstore Rekor.

---

## 2. What attestation does NOT cover

**Explicit scope exclusions:**

- **Grounding content quality or drift.** We hash source identity (IDs, types, URL patterns, ACL models, classifications), not content. A policy doc updated in SharePoint does not invalidate attestation. Content changes are detected by `baseline-drift` telemetry, not attestation.
- **Prompt quality or effectiveness.** `instruction_hash` tracks identity + shape, not "goodness."
- **Business logic correctness.** The partner's vibecoded code is their ownership.
- **Customer's own Azure subscription policies** outside the Bicep modules the accelerator ships.
- **Data classification decisions.** We record who signed them off (qualification); we do not validate their correctness.
- **External dependencies' availability.** GitHub, Rekor, Foundry outages do not invalidate historical attestations.

---

## 3. The RAI tuple (v0.1)

Tracked by attestation + reconcile:

```yaml
rai_tuple:
  model_id: "gpt-5.2"
  model_alias: "gpt-5.2-2026-03"
  instruction_hash: "sha256:..."        # per-agent instructions + templates, sorted + concat
  instruction_sources:                   # provenance for reviewers
    - agent: "triage"
      source: "foundry-portal:agent-id-abc"
      fetched_at: "2026-04-18T..."
  tool_set_hash: "sha256:..."           # sorted tool names + configs + connection names
  side_effect_tool_names: ["sap-po-mcp", "servicenow-create-ticket"]
  grounding_manifest_hash: "sha256:..."  # hash of structured manifest (see §3.1)
  grounding_manifest: [...]              # full manifest (see §3.1)
  topology_hash: "sha256:..."            # hash of agents + edges + HITL + a2a_cap
  topology:
    agents: ["triage", "retriever"]
    edges: [["triage","retriever"]]
    human_in_loop_points: ["triage.before_action"]
    a2a_cap: 2
  data_classification: "confidential"
  profile: "prod-privatelink"
  bundle: "actioning-prod-pl"
```

### 3.1 Hash semantics

- **`instruction_hash`**: deterministic hash of each agent's instructions + prompt templates, fetched from Foundry portal at capture time and snapshotted in-repo at `rai/snapshots/<timestamp>/`. Template variables are hashed as `{{var}}` placeholders, NOT expanded values.
- **`tool_set_hash`**: sorted tool names + configs + connection names. Connection secrets excluded.
- **`grounding_manifest_hash`**: hash of the structured manifest (source IDs + types + URL patterns + ACL models + classifications). **Does NOT hash content.** Content drift is out of scope (see §2).
- **`topology_hash`**: agents list + edges + HITL points + a2a cap. Code-side topology must round-trip through Spec.

---

## 4. Capture → Attest → Deploy-gate sequence

**This sequence is NORMATIVE.** Any accelerator or intake implementation MUST follow it. It closes TOCTOU gaps between live-state capture and deploy.

```
┌──────────────────────────────────────────────────────────────────┐
│ [1] CAPTURE — `baseline attest --capture`                        │
│                                                                  │
│   Live fetches (all required):                                   │
│   • Foundry: agents, instructions, tools, connections            │
│   • Azure (via reconcile): deployed resource state               │
│   • GitHub: PR reviews, CODEOWNERS, org memberships, merge SHA   │
│   • Rekor: qualification entry (Path B/C)                        │
│                                                                  │
│   Compute: all hashes + deployed-state fingerprint + RAI tuple   │
│   Write: signed snapshot → .baseline/snapshots/<timestamp>/      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ [2] ATTEST — `baseline attest --issue <snapshot>`                │
│                                                                  │
│   OIDC-backed GH Actions workflow signs snapshot                 │
│   Publishes in-toto attestation to sigstore Rekor                │
│   Attestation subject = SHA256(lockfile + snapshot)              │
│   Writes attestation ID → .baseline/attestations/<ts>.json       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ [3] DEPLOY-GATE — `baseline deploy --verify <attestation-id>`    │
│                                                                  │
│   Re-fetches live deployed Azure state                           │
│   Compares against attestation's deployed-state fingerprint      │
│   → must be bit-identical OR diff is `auto-adopt` class ONLY     │
│   `block` / `warn` diffs fail deploy-gate                        │
│                                                                  │
│   Freshness gates (BOTH must pass):                              │
│   • capture-to-this-deploy elapsed ≤ 24h, OR                     │
│   • attestation age ≤ 30d AND re-capture in last 24h             │
│                                                                  │
│   On pass: deploy proceeds, attestation ID carries forward       │
│   Post-deploy reconcile confirms materialized state matches      │
└──────────────────────────────────────────────────────────────────┘
```

### 4.1 TOCTOU boundaries explicitly closed

| Boundary | Closure |
|---|---|
| Foundry portal state capture-to-deploy | [3] re-verifies nothing drifted vs snapshot; any `block`/`warn` fails |
| GitHub / Rekor state capture-to-deploy | Cached in signed snapshot at [1]; deploy-gate [3] does NOT require fresh GH/Rekor fetch (external-dep outage doesn't block deploy) |
| Azure deployed state capture-to-deploy | [3] re-fetches live + diffs |
| Max capture-to-deploy window | **24h** — deploy-gate refuses even if fingerprints match, forces fresh capture |

### 4.2 Why these specific windows

- **24h max capture-to-deploy:** tight enough that live-state drift is unlikely; loose enough to absorb a normal partner workflow (plan, review, approve, deploy).
- **30d attestation age:** outer support-scope window. Re-entering requires a fresh 24h re-capture. An attestation never authorizes a deploy from a live-state snapshot older than 24h.

---

## 5. Cached-vs-live verification policy

| Check | Capture [1] | Deploy-gate [3] | Support intake (§ [SUPPORT.md](../../SUPPORT.md)) |
|---|---|---|---|
| Foundry live state | Live fetch required | Re-fetch + diff against snapshot | Cached-verified from snapshot (< 30d) |
| Azure deployed state | Live fetch required | Re-fetch + diff (fingerprint) | Live reconcile against lockfile |
| GitHub review state | Live fetch required | Cached in snapshot | Cached-verified (< 30d); re-fetch on dispute |
| Sigstore Rekor entry | Live fetch required | Cached in snapshot | Cached-verified (< 30d); re-fetch on dispute |

**Implications:**
- Deploy is insulated from transient GitHub / Rekor outages.
- Support intake tolerates external outages via degraded-mode (see `SUPPORT.md`).
- Azure state is the only layer where every phase does a live fetch.

---

## 6. RAI Impact Assessment (IA) binding

The attestation references the RAI IA via `rai.impact_assessment_ref` in Spec:

- **Immutable UUID** identifies the IA document (can't be swapped with a relaxed IA under same name).
- **180-day expiry** — IA expires 180d after issue; attestation refuses if IA is expired.
- **CODEOWNERS-approved PR** required to modify IA — tracked in `codeowners_approval_pr`.
- **RAI tuple drift** — any diff in the tuple flags IA for `requires_review`; blocks re-attestation until CODEOWNERS approves an IA update.

---

## 7. Approver-compromise policy

### Before-approval compromise
If a qualification approver's GitHub account is proven compromised BEFORE the approval timestamp:
- All attestations derived from that approval are invalidated.
- Re-qualification required.
- Incident logged in `docs/governance/incident-log.md`.

### After-approval compromise
If compromise is detected AFTER approval:
- Attestation is NOT auto-invalidated — Rekor + GitHub event log prove approval was valid at time-of-action.
- Attestation refresh required within 30 days before next deploy.
- Governance board reviews whether in-flight work needs re-approval.

Partner + customer must report known compromise within **5 business days**; late reporting is a high-severity waiver requiring governance board sign-off.

---

## 8. What to tell your customer security reviewer

> This solution is attested via a signed in-toto manifest published to sigstore Rekor. The attestation binds:
> - the platform baseline version and its signed SBOM
> - the deployed Azure resource fingerprint
> - the Foundry model, tool set, agent instructions, grounding source manifest, and topology
> - qualification sign-offs bound to specific GitHub identities + Rekor-logged reviews
> - an immutable RAI Impact Assessment reference with 180-day expiry
>
> Attestation is re-verified at every deploy and every support ticket. Drift is classified and either auto-reconciled, warned, or blocking per a signed, versioned rule set.
>
> Not covered: business-logic code correctness, grounding *content* changes (detected via separate drift telemetry), customer's own Azure subscription policies.
