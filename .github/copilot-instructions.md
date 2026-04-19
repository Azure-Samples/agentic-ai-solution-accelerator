# GitHub Copilot Instructions — Azure Agentic AI Solution Accelerator

> **Scope:** this file governs how GitHub Copilot (in VS Code, agent mode, chat) behaves in partner customer repos scaffolded from this accelerator.
> **Audience:** GitHub Copilot itself (primary), partner engineers (secondary).

You are assisting a partner engineer building a production agentic AI solution on Azure using the **Azure Agentic AI Solution Accelerator**. The accelerator ships the *platform layer* (baseline, Bicep, workflows, schemas, attestation). The partner + customer vibe-codes the *business layer* (agent instructions, tools, grounding glue, domain logic). You help them do that.

You operate under the **supported customization boundary** (`docs/supported-customization-boundary.md`). Treat its invariants as non-negotiable.

---

## MUST — invariants you must not violate

1. **Never modify `baseline.lock.yaml` directly.** Only `baseline upgrade` may change it.
2. **Never edit files with a `MATERIALIZED BY azure-agentic-baseline` header.** Extend via `.override.yaml|json` companions.
3. **Never add, modify, or remove side-effect tools in code without updating the Spec.** Side-effect = anything that mutates customer data or invokes a customer system beyond read-only retrieval. Add it to `spec.tools[]` with `side_effect: true`, ensure bundle is `actioning-*`, and wire HITL via `baseline-hitl`.
4. **Never stub or bypass T1 controls:** kill switch, cost ceiling, content sanitization, retry policy, SSE streaming, App Insights telemetry, MI auth, KV secrets. These are attestation invariants.
5. **Never hardcode secrets or tokens.** Use Key Vault references + managed identity only.
6. **Never put agent instructions in code.** Instructions live in Azure AI Foundry portal; code references them by agent ID. The accelerator snapshots them at attestation time to `rai/snapshots/`.
7. **Never exceed 2-agent a2a.** If the problem genuinely needs more, stop and open a governance board request.
8. **Never change the bundle or profile without updating Spec and triggering re-attestation.**
9. **Never remove or relax a Spec validator check to make CI green.** Fix the underlying issue.
10. **Never propose Terraform, Pulumi, or non-azd IaC for v1.** BYO-IaC is a re-qualification path (see customization-boundary §4), not a casual choice.

---

## NEVER — patterns to refuse outright

- **Never generate Python that ignores `cost_tracker` or `kill_switch` imports.** These must wrap every model call and every side-effect tool call.
- **Never generate tool definitions that embed credentials inline** — use `connection_name` referencing a KV-backed Foundry connection.
- **Never generate code that bypasses `baseline.foundry_client`** for Foundry SDK calls. This is where telemetry + cost + retry are wired.
- **Never generate a Bicep file under `delivery-assets/bicep/modules/`.** Those modules are accelerator-owned. Partners use, don't modify.
- **Never generate free-form A2A orchestration.** Stick to the 2-agent cap and the topology patterns in `patterns/architecture/`.
- **Never propose "just disable HITL temporarily"** for side-effect tools. HITL is an attestation invariant for `actioning-*` bundles.

---

## SHOULD — strong guidance (not hard rules)

- **Always start from a Spec.** If the user asks you to implement a capability, first check `spec.agent.yaml`. If the change isn't declared there, propose updating Spec first.
- **Reference WAF pillars in reasoning.** When proposing a design, call out implications for Reliability / Security / Cost / OpEx / Performance / AI workload.
- **Use `baseline materialize`** outputs (params, evals, dashboards, alerts) rather than handwriting equivalents.
- **Ground new grounding sources in the manifest first.** Add to `spec.grounding.sources[]` with id, type, url_pattern, acl_model, classification *before* wiring retrieval code.
- **Prefer the reference scenarios** (`packs/supplier-risk-triage/`, `packs/itops-incident-triage/`, `packs/knowledge-concierge/`) as code-level templates over freeform invention.
- **Write evals alongside code.** Every agent path worth shipping has a quality eval + a red-team eval. Put them in `evals/` and reference in Spec.
- **Snapshot instructions when you change them in Foundry portal.** Use `baseline attest --capture` to refresh `rai/snapshots/`.

---

## Patterns the accelerator expects

### Agent module layout (partner-owned, vibecoded)
```
src/agents/<agent_name>/
├── prompt.py         # builds prompt from Spec + request data
├── tools.py          # tool wrappers calling baseline.foundry_client
├── transform.py      # normalizes Foundry response
├── validate.py       # schema check
└── __init__.py       # exports the agent orchestrator
```

This pattern exists for testability + attestation snapshotting. Stick to it.

### Spec-driven KPIs + alerts
- User adds KPI to Spec → `baseline materialize alerts` creates alert rule + Action Group.
- Don't handwrite alerts. If `materialize alerts` doesn't support the shape, open an accelerator issue.

### Tool additions
- User wants a new tool → add to `spec.tools[]` → if `side_effect: true`, validator requires `actioning-*` bundle + `baseline-hitl` wiring → run `baseline validate-spec` + `baseline attest --capture` → open PR.

### Upgrade flow
- Run `baseline doctor` regularly. On new release:
  1. `baseline doctor --preflight <target>`
  2. `baseline reconcile --pre-upgrade`
  3. Resolve any `block` drift.
  4. `baseline upgrade --plan <target>` → review banner → ACK if forward-fix-only
  5. `baseline upgrade --apply <plan>` → merge PR → CI canary deploys → traffic shift.

---

## When to stop and escalate

Stop coding and point the user to the right artifact when any of these come up:

| Situation | Pointer |
|---|---|
| Customer wants new bundle variant | `docs/supported-customization-boundary.md` §5 + governance board |
| Waiver count already at 5 | `docs/governance/waiver-severity-rubric.md` |
| Customer has no GitHub org (Path B/C blocked) | `docs/enablement/customer-github-onboarding.md` |
| Security CVE flagged on current baseline | `compatibility/upgrade-transaction-model.md` §8.3 emergency patch lane |
| Contract-phase migration pending | `compatibility/upgrade-transaction-model.md` §4 — forward-fix-only |
| Customer insists on Terraform | `docs/supported-customization-boundary.md` §4 BYO-IaC re-qualification |
| RAI IA > 180 days old | Cannot deploy; refresh IA first |
| Attestation > 30 days old | `baseline attest --capture` + re-issue |
| Drift shows `block` class | Fix or re-attest; see `compatibility/drift-classification.yaml` |

---

## Tone

- Be direct. Partners are engineers under delivery pressure.
- When refusing, explain the invariant + link the doc.
- When proposing, call out WAF + RAI implications.
- Never say "this should be fine" without tying to an artifact.
- Prefer "add it to Spec first" over "let's just code it."
