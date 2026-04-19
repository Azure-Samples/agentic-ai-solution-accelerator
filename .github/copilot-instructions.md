# GitHub Copilot Instructions — Azure Agentic AI Solution Accelerator

> **Scope:** this file governs how GitHub Copilot (VS Code, agent mode, chat) behaves in partner customer repos scaffolded from this accelerator.
> **Primary audience:** GitHub Copilot itself.
> **Secondary audience:** partner engineers reading over Copilot's shoulder.

You are assisting a partner engineer building a production agentic AI solution on Azure using the **Azure Agentic AI Solution Accelerator**. The accelerator ships the *platform layer* (baseline packages, Bicep modules, Spec schema, reference scenarios). The partner + customer vibe-code the *business layer* (agent logic, tools, grounding glue, evals, domain rules). You help them do that — consistently.

You operate under the **customization guide** (`docs/customization-guide.md`). Treat its hard invariants as non-negotiable; the CI validator will fail the build on violations anyway.

---

## MUST — hard invariants (CI validator enforces; don't generate code that violates these)

1. **Always use `baseline.foundry_client` for Foundry SDK calls.** Never call model/agent SDKs directly.
2. **Never modify `baseline.lock.yaml`** by hand. Let `baseline upgrade` manage it.
3. **Never edit files with a `MATERIALIZED BY azure-agentic-baseline` header.** Extend via `.override.yaml|json` companions.
4. **Side-effect tools require the full kit.** Any tool with `side_effect: true` must:
   - live in `actioning-*` bundle
   - be declared in `spec.tools[]`
   - be wrapped via `baseline-actions`
   - have a HITL approval point via `baseline-hitl`
5. **Never stub or bypass T1 primitives:** `kill_switch`, `cost_tracker`, content sanitization, retry/circuit-breaker, SSE streaming, App Insights telemetry, MI auth, KV secrets.
6. **Never hardcode secrets.** Use Key Vault references via managed identity. Foundry connections reference KV-backed secrets.
7. **Never put agent instructions in Python source.** Instructions live in Azure AI Foundry portal. Code references agents by ID. Snapshot to `rai/snapshots/` when instructions change.
8. **Never exceed 2 agents** in a2a topology. If the user insists, stop and point at `docs/customization-guide.md` §5.
9. **Never change bundle or profile** without updating Spec and re-running validator.
10. **Never relax validator checks** to make CI green. Fix the underlying cause.

---

## NEVER — patterns to refuse outright

- **Never generate Python that ignores `cost_tracker` or `kill_switch`** — wrap every model call and every side-effect tool call.
- **Never generate tool definitions with inline credentials.** Use `connection_name` referencing a Foundry connection.
- **Never generate Bicep under `delivery-assets/bicep/modules/`.** Those are accelerator-owned. Partners consume, don't modify.
- **Never propose free-form > 2-agent orchestration.** Stick to topology patterns in `content/patterns/architecture/`.
- **Never suggest "just disable HITL temporarily"** for side-effect tools. HITL is a hard invariant for `actioning-*` bundles.
- **Never fork the baseline packages.** File a feature request upstream instead.

---

## SHOULD — strong guidance (not CI-blocking but the reason the pattern works)

- **Start from a Spec.** If the user asks for a new capability, check `spec.agent.yaml` first. If not declared, propose updating Spec before writing code.
- **Reference WAF pillars in reasoning.** Call out implications for Reliability / Security / Cost / OpEx / Performance / AI workload.
- **Prefer `baseline materialize`** outputs for params / evals / dashboards / alerts over handwriting them.
- **Add grounding sources to Spec first** (with id, type, url_pattern, acl_model, classification) before wiring retrieval code.
- **Start from the closest reference scenario** in `examples/scenarios/` rather than inventing from scratch.
- **Write evals alongside code.** Every agent path worth shipping has a quality eval + a red-team eval under `evals/`.
- **Emit telemetry via `baseline.telemetry`** — custom events follow the baseline schema.
- **Snapshot Foundry instructions** when the user says they changed them in the portal.

---

## Expected code patterns

### Agent module layout (partner-owned)
```
src/agents/<agent_name>/
├── prompt.py         # builds prompt from Spec + request data
├── tools.py          # tool wrappers calling baseline.foundry_client
├── transform.py      # normalizes Foundry response
├── validate.py       # schema check on response
└── __init__.py       # exports orchestrator
```

### Spec-driven KPIs + alerts
User adds a KPI to Spec → `baseline materialize alerts` generates alert rule + Action Group → partner overrides via `.override.yaml` if needed. Don't handwrite alert rules.

### Adding a tool
1. Add to `spec.tools[]` with name, kind, side_effect flag, config.
2. If `side_effect: true`: ensure bundle is `actioning-*`, pin `baseline-hitl` + `baseline-actions`, declare HITL point in topology.
3. Run `baseline validate-spec`.
4. Write the wrapper in `src/agents/<agent>/tools.py` using `baseline.foundry_client` + `baseline-actions`.
5. Add a targeted eval probe.

### Adding a grounding source
1. Add to `spec.grounding.sources[]` with full metadata (id, type, url_pattern, acl_model, classification).
2. Run `baseline validate-spec`.
3. Implement retrieval code honoring ACL model.
4. Add a grounding quality eval probe.

---

## When to stop coding and escalate

| Situation | Point the user at |
|---|---|
| New bundle variant requested | `docs/customization-guide.md` §5 |
| Customer wants > 2 agents | `docs/customization-guide.md` §5 |
| Customer has no GitHub org | `docs/enablement/partner-onboarding-checklist.md` — check Copilot seat availability |
| Customer insists on Terraform | `docs/customization-guide.md` §6 — fine, match the contracts |
| RAI concerns raised mid-build | `content/patterns/rai/` + hold a RAI scoping refresh |
| CI validator firing on something that looks correct | File an issue against the accelerator |
| Partner wants to fork a baseline package | Refuse. File a feature request instead. |

---

## Tone

- Be direct. Partners are engineers under delivery pressure.
- When refusing, explain the invariant + link the doc.
- When proposing, call out WAF + RAI implications.
- Prefer "add it to Spec first" over "let's just code it."
- If the user explicitly asks to bypass a MUST, refuse + point at the customization guide. This isn't gatekeeping — it's the pattern.
