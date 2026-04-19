# Customer GitHub Onboarding — Qualification Path Prerequisite

> **Scope:** v1 of the accelerator requires customer-side GitHub for Path B/C qualification.
> **Audience:** partner delivery lead + customer IT + customer security reviewer.

## 1. Why GitHub is required for qualification (v1)

Qualification evidence for Path B (Enterprise) and Path C (Expansion) binds sign-offs to a cryptographic chain (see `docs/rai/attestation-scope.md`):

- PR review submitted by a specific GitHub numeric user ID (immutable across handle renames)
- CODEOWNERS enforcement with role-to-team mapping
- Org membership verified at attestation time
- OIDC-signed GitHub Actions workflow producing in-toto attestation
- Published to sigstore Rekor with entry UUID in `.qualification.yaml`

This is materially stronger than typed-name-plus-timestamp evidence. It is also tied to GitHub's identity + event log. **For v1 there is no alternative identity path.**

---

## 2. What "customer-side GitHub" means

- **A GitHub Enterprise Cloud or EMU organization owned by the customer** (not the partner).
- **At least one customer-owned team** within that org containing the customer-sponsor identity.
- **Branch protection + required-reviews + CODEOWNERS** enabled on the customer's engagement repo.

The customer may optionally use a partner's org for the main engagement repo, provided the `customer-sponsor` CODEOWNERS role maps to a team in a **customer-owned** org and review approvals come from that team. But in practice, most engagements end up with a customer-owned repo.

---

## 3. If the customer has no GitHub org

Options in priority order:

### Option 1 — Customer onboards GitHub for qualification purposes only
- Minimal: 1 EMU or GHEC org with 2–5 seats for the customer-sponsor + their delegates.
- The customer's broader estate does NOT need to move to GitHub.
- Cost is modest ($21/seat/mo EMU at list; often absorbable by MSFT for lighthouse engagements).
- Partner delivery lead helps provision + configures CODEOWNERS.

### Option 2 — Engagement remains Path A (sandbox / guided-demo) only
- No production attestation.
- No "prod-standard" or "prod-privatelink" bundle.
- Valid for demos, POCs, certification dry-runs.
- Not a path to production for this customer in v1.

### Option 3 — Wait for v1.5 Entra-based identity path
- Candidate only; not committed.
- Would bind qualification to Entra signed attestations instead of GitHub reviews.
- No promised date.

**There is no fourth option in v1.** Typed-name-plus-date evidence is insufficient and will be rejected by the validator.

---

## 4. Onboarding checklist for customer GitHub

- [ ] Customer procures GitHub Enterprise Cloud **or** GitHub EMU org (customer-billed preferred; MSFT-assisted on lighthouse basis).
- [ ] Customer-sponsor + 1–2 delegates invited to org.
- [ ] Team created for customer-sponsor role (e.g., `@<customer>/agentic-solution-sponsors`).
- [ ] Partner delivery lead invited with appropriate scope.
- [ ] Engagement repo created in customer org (or in partner org with CODEOWNERS pointing to customer team).
- [ ] Branch protection on `main`: require PR reviews, require CODEOWNERS approval, require status checks, no force push, no deletion.
- [ ] CODEOWNERS configured with at minimum:
  - `/.qualification.yaml` → customer-sponsor team + partner-lead team (both required)
  - `/rai/**` → customer-sponsor team + partner-lead team
  - `/docs/decisions/**` → customer-sponsor team
- [ ] Customer-sponsor's GitHub numeric user ID captured in `.qualification.yaml` (not just handle).
- [ ] Customer security reviewer briefed on `docs/rai/attestation-scope.md`.

---

## 5. What the customer does NOT need to do

- Move any existing source code to GitHub.
- Use GitHub Copilot (partner uses it; customer doesn't have to).
- Use GitHub Actions for customer-owned CI elsewhere.
- Grant GitHub access to production Azure subscriptions at an identity level beyond the scoped OIDC federated credential for the attestation workflow.

---

## 6. Security review talking points (for the customer's reviewer)

- All access to customer systems remains through the customer-owned Azure tenant + managed identity. GitHub does not gain data-plane access.
- The GitHub OIDC federated credential is scoped to a specific repo + workflow + branch; it mints short-lived Azure tokens.
- The Rekor entry contains no customer data — it is a signed manifest of approval metadata (actor IDs, commit SHAs, workflow run IDs, hashes).
- The sigstore public transparency log publishes entry UUIDs but not secret content.
- `docs/rai/attestation-scope.md` enumerates what IS and IS NOT covered.

---

## 7. Future: Entra-based qualification (v1.5 candidate)

Tracked in backlog. The goal is to offer an Entra-signed equivalent of the GitHub-review-backed attestation, for customers whose IT policies materially preclude GitHub. The target is **equivalence** (cryptographic chain, identity binding, tamper-evidence) not a weaker "typed-name" fallback. No date commitment.
