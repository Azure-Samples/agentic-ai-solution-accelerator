# Getting Started — Partner Journey

> **Audience:** a Microsoft delivery partner engineer/architect who just landed on this repo and wants to understand what it is, what they can do with it today, and how a customer engagement flows through it.

---

## 1. What this accelerator actually is

A curated set of **content, examples, and tooling** that helps you vibe-code an agentic AI solution on Azure for a specific customer, following Microsoft's WAF + RAI + Foundry patterns. It is **not** a SaaS product, not a hosted platform, and not source code you ship as-is to a customer. Think of it as:

- A **pattern library** you read before designing.
- A **Copilot IDE kit** you drop into your customer repo so Copilot generates in-pattern code.
- **Reference scenarios** you copy and adapt.
- A **validator** that runs in your CI and catches drift from the patterns.
- **azd templates** as starting points for Azure infra.

You keep the customer relationship, the production code, the pager, and the commercial ownership.

---

## 2. What's usable today vs what's coming

This accelerator is shipping incrementally. Be honest with yourself about phase.

| Phase | What's in it | What you can do |
|---|---|---|
| **Phase A (today)** | Patterns content + Copilot IDE kit + Spec schema + reference scenario READMEs + stub CLI + stub azd templates + partner playbook + templates | **Read and give feedback.** Use the IDE kit in an experimental customer repo — it already improves Copilot output. Use the patterns to shape your proposal. Use the Spec schema + `validate-spec` to sanity-check a Spec you hand-write. |
| **Phase B** | `baseline` pip pkg implemented (T1 core). `baseline new-customer-repo` scaffolder. Validator covers Spec + pattern rules. | Scaffold a real customer repo with one command. Get CI validation that actually catches drift. |
| **Phase C** | Bicep modules + azd templates fully implemented. | `azd up` from one of the 5 bundles for real. |
| **Phase D** | Reference scenarios ship as runnable code (not just READMEs). Runbooks fleshed out. | Copy a working scenario as your starting code. |

**If you're reading this in Phase A**, your productive moves are: study the patterns, wire the Copilot IDE kit into a test repo, and give us feedback via GitHub issues.

---

## 3. The three-layer consistency model (why this works)

```
Scaffolding   →   Copilot IDE kit   →   CI validator
(repo shape)      (authoring time)      (merge time)
```

- **Scaffolding** gets you a correct repo from day zero — pinned baseline, CI wired, IDE kit in `.github/`, a reference scenario copied in.
- **Copilot IDE kit** shapes every Copilot suggestion so it lands in-pattern (uses baseline primitives, declares in Spec, wires HITL, emits telemetry).
- **Validator** fails the build on drift — Spec-schema violations, bundle↔profile mismatch, HITL missing for side-effect tools, grounding source missing classification.

A good-faith partner who follows the scaffold + lets Copilot do its job + keeps CI green will land in-pattern. That's the goal.

---

## 4. Customer engagement flow (phases, not gates)

Not a rigid process. These are phases most engagements pass through. Read [`docs/partner-playbook.md`](partner-playbook.md) for more detail on each.

### Phase 1 — Scope the engagement
- Use [`docs/templates/SoW.md`](templates/SoW.md) to align with the customer.
- Pick a bundle (see the matrix in [README.md](../README.md#bundles-at-a-glance)).
- Pick a profile (sandbox / prod-standard / prod-privatelink).
- Document key decisions in [`docs/templates/decisions-template.md`](templates/decisions-template.md).

### Phase 2 — Design the solution
- Read [`content/patterns/architecture/`](../content/patterns/architecture) to choose topology.
- Read [`content/patterns/waf-alignment/`](../content/patterns/waf-alignment) for per-pillar decisions.
- Read [`content/patterns/rai/`](../content/patterns/rai) for RAI posture.
- Hold RAI scoping with the customer using [`docs/templates/rai-scoping-minutes-template.md`](templates/rai-scoping-minutes-template.md).
- Pick the reference scenario closest to your customer's case: [`examples/scenarios/`](../examples/scenarios).
- Draft a Spec based on [`examples/specs/`](../examples/specs).

### Phase 3 — Scaffold the customer repo
- **Phase A today:** copy [`examples/scenarios/<scenario>/`](../examples/scenarios) into a new customer repo by hand, drop the IDE kit into `.github/`, add a CI workflow that runs `validate-spec`.
- **Phase B+:** run `baseline new-customer-repo --bundle <bundle> --scenario <name>` — one command.

### Phase 4 — Vibecode with Copilot
- Work inside the scaffolded customer repo in VS Code.
- The Copilot IDE kit sitting in `.github/` shapes every Copilot suggestion.
- Use the `@delivery-guide` chat mode for orchestration questions ("what's next?", "where does this fit?").
- Let Copilot generate agent modules, tool wrappers, grounding glue, transforms, evals — following the patterns the kit enforces.
- Commit frequently. CI runs the validator on every PR.

### Phase 5 — Deploy
- **Phase A today:** use the customer's existing Azure deployment flow; the accelerator doesn't deploy for you yet.
- **Phase C+:** `azd up` from the chosen bundle's template.

### Phase 6 — Day-2 ownership
- Runbooks live under [`docs/runbooks/`](runbooks). Walk the customer-ops team through them.
- Partner is on the pager. Microsoft is not.
- Upgrade baseline on your own cadence — stay within 2 minor versions of current.

---

## 5. Pre-flight checklist for your first engagement

Before scoping a customer engagement on this accelerator, confirm:

- [ ] You've read [`docs/customization-guide.md`](customization-guide.md).
- [ ] You've scored yourself on [`docs/enablement/self-assessment.md`](enablement/self-assessment.md) and landed 13+.
- [ ] You've worked through [`docs/enablement/partner-onboarding-checklist.md`](enablement/partner-onboarding-checklist.md).
- [ ] You have a GitHub org with Copilot Business/Enterprise seats.
- [ ] You have Azure AI Foundry project access in the target region.
- [ ] You have a customer sponsor who can approve RAI scoping decisions.
- [ ] You understand that this accelerator is community-supported, best-effort — you own the production pager.

---

## 6. Good failure modes to expect

Things that will happen. Plan for them.

- **Copilot generates code that violates the Spec.** The validator will catch it in CI. Fix by updating the Spec (if the capability is new) or reverting (if it was an error).
- **The customer wants a bundle variant we don't have.** See `docs/customization-guide.md` §5. Usually solved via parameters, not a new bundle.
- **The customer wants Terraform / in-house IaC.** Fine — our azd templates are reference examples, not the only deploy path. Follow the patterns content regardless.
- **The customer wants a 3-agent graph.** We cap at 2 through v1. Rescope or split the problem.
- **A pattern doc is wrong or outdated.** File an issue + a PR. This is a living content pack.

---

## 7. What NOT to do

- **Don't delete the Copilot IDE kit from `.github/`** because "Copilot is slowing you down." It's the only thing keeping your generated code in-pattern.
- **Don't relax the validator in CI** to merge faster. Fix the underlying Spec drift.
- **Don't fork the baseline packages** to add features. Open an issue; we iterate on the upstream.
- **Don't ship customer code with inline secrets, stubbed kill switch, or disabled cost tracker.** These are non-negotiable patterns even without a cryptographic gate.
- **Don't skip RAI scoping** because the customer is in a rush. A 60-minute scoping session pays for itself.

---

## 8. Feedback welcome

This accelerator is early. The most useful contribution you can make is tell us where it falls short for a real customer engagement. GitHub issues + PRs are open.
