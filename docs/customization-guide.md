# Customization Guide

> **Audience:** partner engineers + architects.
> **Purpose:** make clear what the accelerator asks you to keep consistent, what's free for the customer business layer, and how to request exceptions.
>
> This is guidance, not cryptographic gating. The validator will fail CI on the hard items. The soft items rely on you following the pattern because it's the reason the accelerator works.

---

## 1. Core posture

The accelerator works because partners agree to a **small set of invariants** that keep customer solutions: supportable, WAF-aligned, RAI-aligned, and reusable across engagements. Inside the invariants, you have full freedom to vibecode customer-specific business logic.

Think of it as a contract between partner + accelerator:
- **Partner keeps the platform layer consistent.**
- **Partner + customer own the business layer.**

---

## 2. Hard invariants — validator-enforced (will fail your CI)

These are checked on every PR. Violations block merge.

### 2.1 Spec conformance
- `spec.agent.yaml` validates against `spec.schema.json`.
- Bundle ∈ {`sandbox-only`, `retrieval-prod`, `retrieval-prod-pl`, `actioning-prod`, `actioning-prod-pl`}.
- Profile matches bundle per the matrix in the schema.
- Agent count ≤ 2 (a2a cap through v1).

### 2.2 Side-effect tools
- Any tool with `side_effect: true` requires:
  - Bundle is `actioning-*`.
  - `baseline-hitl` pinned in the customer repo.
  - `baseline-actions` pinned in the customer repo.
  - A declared HITL point in Spec's topology.

### 2.3 Grounding sources
- Every entry in `spec.grounding.sources[]` has `id`, `type`, `url_pattern`, `acl_model`, `classification`.
- Classifications are drawn from the declared enum.

### 2.4 Baseline wiring
- `azure-agentic-baseline` is pinned in `pyproject.toml`.
- For `prod-*` profiles: `baseline-drift` + `baseline-feedback` also pinned.
- For `actioning-*` bundles: `baseline-hitl` + `baseline-actions` also pinned.

### 2.5 Forbidden code patterns
- No inline secrets (hardcoded tokens, connection strings).
- No `cost_tracker.disable()` or equivalent.
- No `kill_switch` bypass around model or side-effect tool calls.
- No direct model SDK calls that bypass `baseline.foundry_client`.
- No tool calls with credentials embedded (must go through Foundry connections + KV).

### 2.6 Materialized files
- Files with `MATERIALIZED BY azure-agentic-baseline` header must match their hash — **don't edit in place**. Override via `.override.yaml|json` companion files.

---

## 3. Soft invariants — strongly recommended (not CI-blocking)

These aren't enforced by the validator but they're the reason the pattern works. Violating them is technical debt against your future self.

- **Agent instructions live in Foundry portal**, not in code. Code references by agent ID. Snapshot to `rai/snapshots/` when they change.
- **Evaluations exist and are run in CI.** Quality suite + red-team suite. Eval regression fails CI (can be waived; don't make it habit).
- **Telemetry follows baseline schema.** Custom events emitted via `baseline.telemetry`.
- **Cost ceiling set + alerting wired.** Baseline default acceptable; lower is fine; higher than customer-approved is not.
- **Identity model = managed identity** for data-plane access; no user-secret patterns.
- **Secrets in Key Vault** referenced from App Config / Foundry connections.
- **Content filter locked at strict defaults** for production profiles unless customer RAI waiver covers it.
- **Groundedness threshold ≥ 0.7** for grounded-retrieval scenarios (tune based on domain).

---

## 4. Free-for-all — customer business layer

Everything below is yours + the customer's. Copilot helps; validator doesn't enforce specifics.

### 4.1 Content
- Agent prompts + templates (in Foundry portal).
- Tool implementations (Python wrappers, MCP servers, function calls).
- Grounding pipelines (indexing, chunking, retrieval glue).
- Domain transforms + business validation.
- Evaluation datasets.
- Dashboards (over baseline defaults).
- Runbooks.

### 4.2 Parameterization (via `.override.yaml|json` companions)
- SKU sizes within profile allow-list.
- Alert thresholds above baseline minimum.
- Scale rules.
- Cost ceiling (lower than profile default).
- Dashboard additions.

### 4.3 Appendable
- Additional KPIs in Spec.
- Additional grounding sources (add to Spec with classification).
- Additional eval metrics (don't relax the baseline set).

---

## 5. Bundle variants — the most common ask

Customers want bundles we don't have. Resolve by parameters + profiles + T3 extensions, NOT new bundles.

| Customer ask | Resolution |
|---|---|
| "retrieval-prod but with cache" | Add `baseline-cache` (T3). Document perf caveats. |
| "actioning-prod with narrower HITL" | Configure HITL per-tool in Spec. `baseline-hitl` still pinned. |
| "3-agent workflow" | Not in v1. Split into two engagements or rescope. |
| "retrieval-prod in a region without PL SKUs" | Use `prod-standard` profile. |
| "cost-ceiling-only bundle" | Adjust Spec `cost_ceiling`. No new bundle. |
| "BYO Terraform instead of azd" | Fine — azd templates are reference examples, not required. Patterns + Spec still apply. |

**New blessed bundles** (would need a 6th entry in the matrix) require accelerator engineering discussion. Open a GitHub issue with: customer need, why existing bundles can't cover it, expected re-use across engagements.

---

## 6. BYO-IaC (Terraform, in-house landing zone, etc.)

Some customers mandate non-azd IaC. Fine.

**You must still match the Bicep module contracts:**
- Foundry project identity model + KV-referenced secrets
- Container Apps with MI + App Config wired
- Private endpoints for `*-pl` profiles
- App Insights telemetry wired
- Diagnostic settings enabled
- Network posture matching profile

Read the `MODULE_CONTRACT.md` file that ships per Bicep module (Phase C) to understand the semantic contract. Match it in whatever IaC you use. Validator does not check IaC; it checks Spec + code. But pattern-conformant IaC is what makes the solution supportable.

---

## 7. When to diverge from patterns

Divergence is fine when it's reasoned. Document it as a decision record in `docs/decisions/`:

- **Context** — what the customer needs.
- **Pattern we're diverging from** — cite the doc.
- **Why** — specific constraint (regulatory, technical, timing).
- **Compensating control** — what we're doing instead.
- **Review cadence** — when we'd reconsider.

Then move on. No board to ask. This is your engagement.

---

## 8. When to file an issue against the accelerator

- Validator fires on something that's actually correct.
- Pattern doc is out of date or wrong.
- You repeatedly have to write the same override for a customer requirement — probably a missing pattern.
- A customer ask recurs across engagements and doesn't fit the existing bundles.
- You discover a WAF / RAI gap in the guidance.

Good feedback closes the loop + strengthens the accelerator. Bad feedback ("we disabled the validator because it was slowing us down") gets closed with a pointer here.
