# Partner Playbook — Customer Engagement Flow

> **Audience:** partner delivery lead, partner engineers, partner architects.
> **Format:** phase-by-phase guidance. No formal sign-off gates. Partners own the engagement end-to-end.

> **Note:** earlier drafts gated engagements on Microsoft-signed qualification + attestation. In the current model, Microsoft does not gate your engagement. These phases are *recommendations* based on what reliably works. Use them as a checklist, adapt to your customer.

---

## Phase 1 — Scope

**Goal:** align customer + partner on what we're building + how we'll judge success.

**Activities**
- Run a 30–60 minute exec intro with the customer sponsor.
- Use [`docs/templates/SoW.md`](templates/SoW.md) to document scope + responsibilities.
- Pick a **bundle** (`sandbox-only`, `retrieval-prod`, `retrieval-prod-pl`, `actioning-prod`, `actioning-prod-pl`).
- Pick a **profile** (`dev-sandbox`, `guided-demo`, `prod-standard`, `prod-privatelink`).
- Pick a **reference scenario** closest to your customer's case.
- Document key decisions using [`docs/templates/decisions-template.md`](templates/decisions-template.md).

**Outputs**
- `docs/engagement-brief.md` in your customer repo (1 page)
- Bundle + profile chosen
- Key decisions recorded

**Common issues**
- Customer wants features that require a new bundle → rescope within existing 5 bundles + parameter flags.
- Customer classifies data as restricted + wants public network → steer to `*-pl` bundles.

---

## Phase 2 — Design

**Goal:** land architecture + RAI posture + Spec before writing code.

**Activities**
- Read [`content/patterns/architecture/`](../content/patterns/architecture) — topology patterns (single-agent vs 2-agent a2a, retrieval-only vs actioning, HITL placement).
- Read [`content/patterns/waf-alignment/`](../content/patterns/waf-alignment) — per-pillar decisions.
- Read [`content/patterns/rai/`](../content/patterns/rai) — content filter, groundedness, red-team evals, HITL.
- Hold RAI scoping meeting with customer using [`docs/templates/rai-scoping-minutes-template.md`](templates/rai-scoping-minutes-template.md).
- Draft `spec.agent.yaml` — start from the closest example in [`examples/specs/`](../examples/specs).
- Run `python tools/validate-spec.py path/to/spec.agent.yaml` until clean.

**Outputs**
- Architecture sketch (diagram + topology choice)
- RAI scoping minutes
- Validated `spec.agent.yaml`
- Decision records for material choices (network, identity, data classification)

**Common issues**
- Spec validator fails on `side_effect: true` tool + `retrieval-*` bundle → switch to `actioning-*` bundle or remove the tool.
- Grounding source missing `acl_model` or `classification` → ask the customer; these can't be guessed.
- Topology > 2 agents → split the problem or add the second capability as a second engagement later.

---

## Phase 3 — Scaffold

**Goal:** stand up a correct customer repo.

**Activities (Phase A — manual today)**
1. Create a new GitHub repo for the customer.
2. Copy the chosen reference scenario from [`examples/scenarios/<scenario>/`](../examples/scenarios).
3. Copy [`.github/copilot-instructions.md`](../.github/copilot-instructions.md) and [`.github/chatmodes/`](../.github/chatmodes) into the new repo's `.github/`.
4. Copy the chosen azd template from [`examples/azd-templates/<bundle>/`](../examples/azd-templates) into `infra/`.
5. Pin `azure-agentic-baseline` + required T2 packages in your `pyproject.toml`.
6. Wire a CI workflow that runs `validate-spec` on every PR.
7. Drop a CODEOWNERS file with branch protection expectations.
8. Place the Spec at repo root as `spec.agent.yaml`.
9. Commit initial scaffold to `main`.

**Activities (Phase B — once scaffolder lands)**
```bash
baseline new-customer-repo <customer-name> --bundle <bundle> --scenario <scenario>
```
One command produces all of the above.

**Outputs**
- Customer repo on `main` with CI green on first commit
- IDE kit in place for Copilot
- Spec validated

---

## Phase 4 — Vibecode

**Goal:** build the customer's business logic using Copilot in VS Code, within the Spec contract.

**Activities**
- Open the customer repo in VS Code with GitHub Copilot enabled.
- Use `@delivery-guide` chat mode for orchestration questions.
- Implement agent modules under `src/agents/<agent_name>/` following the 4-file pattern (`prompt.py`, `tools.py`, `transform.py`, `validate.py`).
- Implement tool wrappers — all tool calls go through `baseline.foundry_client`.
- Implement grounding glue against sources declared in Spec.
- Author evals under `evals/` — quality + red-team suites, both required.
- Snapshot agent instructions from Foundry portal into `rai/snapshots/` whenever they change.
- Run `validate-spec` + local CI on every push.

**What Copilot should do (because instructions tell it to)**
- Use `baseline.foundry_client` for every Foundry call.
- Wrap every side-effect tool through `baseline-actions` + `baseline-hitl`.
- Declare new tools in Spec before writing implementation.
- Add kill-switch + cost-tracker wiring on model calls.
- Generate evals alongside code.

**Common issues**
- Copilot tries to put agent instructions in Python. Stop it. Instructions live in Foundry portal; code references by agent ID.
- Copilot suggests inline secrets. Stop it. Use Key Vault references via managed identity.
- Copilot skips HITL for a side-effect tool to move fast. Validator catches; fix properly.

---

## Phase 5 — Deploy

**Goal:** get the solution running in the customer's Azure environment.

**Activities (Phase A — customer's existing flow)**
- Use whatever Azure deploy path the customer already has (azd, bicep, terraform, manual).
- Ensure MI-based identity + KV-backed secrets + App Insights wiring match Spec.
- Deploy to sandbox first; validate evals pass in-env; then prod.

**Activities (Phase C — once Bicep modules land)**
```bash
azd up
```

**Outputs**
- Running solution in target subscription
- Evals passing post-deploy
- Telemetry flowing to App Insights
- Runbooks staged for the ops team

**Common issues**
- SKU regional availability — especially private-link SKUs for `*-pl` bundles.
- Customer Entra tenant RBAC doesn't grant Foundry data-plane to the deploy SP — pre-flight this.

---

## Phase 6 — Day-2 ownership

**Goal:** hand off to customer ops. Partner stays on the pager for an agreed window; customer owns after that.

**Activities**
- Walk through each runbook in [`docs/runbooks/`](runbooks) with customer ops.
- Run a sev-1 tabletop.
- Document the ownership matrix (who pages whom, escalation path).
- Confirm upgrade cadence + who's responsible for tracking baseline releases.
- Confirm cost + RAI posture monitoring ownership.

**Outputs**
- Runbook walkthrough completed
- Sev-1 tabletop notes
- `docs/day2-ownership.md` in customer repo

---

## Cross-phase guidance

### Waivers (informal)
When you need to diverge from a pattern temporarily (e.g., alert threshold raised during a load test), document it:
- In the customer repo: `docs/waivers/<short-name>.md` with rationale + expiry.
- Review quarterly. Expired waivers without renewal signal technical debt.

### RAI scoping refresh
Material changes to topology / grounding / tools / model → hold a short scoping refresh + update the RAI minutes. Don't let drift accumulate.

### Baseline upgrades
- Watch the `baseline` release feed.
- Upgrade within 2 minor versions of current. Older than that, patterns + security expectations may have shifted.
- Run the validator + eval suite after every upgrade.

### Bundle variant requests from customer
- Variants are Spec parameters + profiles, NOT new bundles. See [`docs/customization-guide.md`](customization-guide.md) §5.
- "Give me retrieval-prod with cache" → add `baseline-cache` T3 dep; perf SLOs that depend on cache hit rate are on you.
- "3-agent graph" → not in v1. Split the problem.

---

## Velocity expectations (honest)

These are observations, not commitments.

- **Sandbox demo:** hours for a partner with scaffolding ready; days if starting from zero.
- **First prod deploy:** weeks to months. Dominated by customer RAI scoping, security review, and data classification — not by accelerator tooling.
- **Second prod deploy for the same customer:** much faster; patterns + scaffold + Copilot reuse compounds.

The accelerator compresses engineering phases. It does not compress governance phases. If your customer's security review takes 8 weeks, no accelerator changes that.
