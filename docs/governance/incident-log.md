# Governance Board — Incident Log

> Canonical record of security incidents, approver-compromise reports, attestation invalidations, and ratification of disaster-fallback decisions.

**Visibility:** RESTRICTED. Governance Board + affected parties + MSRC only.
**Companion:** `board-decision-log.md` (public to onboarded partners).

---

## Incident record template

```
## INC-YYYY-NN — <short title>

**Reported:** YYYY-MM-DD by <reporter>
**Category:** [approver-compromise | attestation-forgery-suspected | rekor-outage-deploy | drift-rule-bypass | data-exposure | waiver-violation | other]
**Severity:** [low | medium | high | critical]
**Status:** [open | investigating | contained | closed]
**Affected:**
  - Repo(s): <list>
  - Attestation ID(s): <list>
  - Waiver(s): <list>

**Timeline:**
- YYYY-MM-DD HH:MM — <event>
- ...

**Root cause (when known):**
<description>

**Resolution:**
- [ ] Attestation(s) invalidated
- [ ] Re-qualification required
- [ ] Governance board decision linked: YYYY-MM-DD-NN
- [ ] Partner notified
- [ ] Customer notified
- [ ] MSRC case opened (if applicable)

**Lessons / follow-ups:**
<bullet list>
```

---

## Incidents

<!-- Reverse-chronological -->

_(none — accelerator pre-launch)_
