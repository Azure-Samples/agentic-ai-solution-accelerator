# Agentic AI Solution Accelerator

> **A GitHub template partners clone to ship production-grade multi-agent Azure solutions for customers in days, not months.**

**Flagship scenario:** Sales Research & Personalized Outreach — a supervisor agent routes a research request across specialist workers (Account Researcher, ICP/Fit Analyst, Competitive Context, Outreach Personalizer) and returns a grounded, citeable sales brief with a CRM-ready outreach draft. Human-in-the-loop gates every CRM write and every email send.

**Stack:** Microsoft Agent Framework · Azure AI Foundry · Azure AI Search · Managed Identity · Key Vault · Container Apps · Application Insights · `azd` for infra.

**Adoption model:** `gh repo create --template` → Copilot-guided discovery → `azd up` → iterate in VS Code → merge through CI gates.

---

## How partners use this

```bash
gh repo create <customer>-agents \
  --template Azure/agentic-ai-solution-accelerator --private
cd <customer>-agents && code .
```

Then in VS Code:

1. `/discover-scenario` — Copilot interviews you (or the customer) and writes `docs/discovery/solution-brief.md`: business context, success criteria, ROI hypothesis, constraints, acceptance evals.
2. `/scaffold-from-brief` — Copilot adapts the repo to the brief (prompts, tools, retrieval, HITL, evals, telemetry, manifest).
3. `azd up` — provisions Foundry + Search + KV + ACA + App Insights in customer Azure and deploys the agents.
4. Iterate in Copilot Chat; every PR is gated by `scripts/accelerator-lint.py`, `evals/quality/`, and `evals/redteam/`.

Full walkthrough: **[QUICKSTART.md](QUICKSTART.md)**.

---

## What's in the box

```
agentic-ai-solution-accelerator/
├── accelerator.yaml              engagement manifest (solution, acceptance, controls, KPIs)
├── src/                          flagship: sales research & outreach (supervisor + 4 workers)
│   ├── agents/                   three-layer pattern per agent (prompt, transform, validate)
│   ├── tools/                    HITL-gated side-effect tools (CRM write, email send)
│   ├── retrieval/                Azure AI Search grounding
│   ├── workflow/                 WorkflowBuilder supervisor + aggregator
│   └── accelerator_baseline/     partner-owned primitives: telemetry, HITL, killswitch, evals, cost
├── infra/                        Bicep + azd (Foundry, Search, KV, ACA, App Insights, dashboards)
├── evals/
│   ├── quality/                  golden cases + CI gates from accelerator.yaml.acceptance
│   └── redteam/                  XPIA + jailbreak + brief-specific RAI cases
├── patterns/
│   ├── single-agent/             variant: when orchestration isn't needed
│   └── chat-with-actioning/      variant: conversational front-end with tools
├── docs/
│   ├── discovery/                solution-brief.md + SOLUTION-BRIEF-GUIDE.md
│   ├── references/               scenario walkthroughs (customer service, RFP response)
│   ├── patterns/                 architecture · WAF · RAI
│   ├── partner-playbook.md       full engagement guide
│   ├── version-matrix.md         known-good SDK pins (weekly CI validates against latest)
│   └── customization-guide.md    what to change, what not to
├── .github/
│   ├── copilot-instructions.md   hard rules: Agent Framework, MI, HITL, evals, RAI
│   ├── AGENTS.md (top-level)     mirror for Cursor/Claude Code/Codex CLI
│   ├── chatmodes/                discover-scenario, scaffold-from-brief, add-*, switch-to-variant
│   └── workflows/                lint, evals, deploy, version-matrix (weekly pinned-latest)
└── scripts/accelerator-lint.py   ~30 deterministic policy checks (local + CI)
```

---

## Why this instead of starting from scratch

| Without the accelerator | With the accelerator |
|---|---|
| Partner re-invents auth, telemetry, HITL, evals, RAI posture every engagement | Ships as partner-owned source in `src/accelerator_baseline/`; used from day one |
| Discovery notes disconnected from code | Solution Brief drives scaffolding, evals, manifest, dashboards |
| "Should we use single-agent or supervisor?" → guesswork | Flagship + two variants + four reference scenarios; pick-and-scaffold |
| Compliance & WAF done at the end (if at all) | Enforced from commit 1 via `copilot-instructions.md` + CI lint + IaC content filters |
| ROI promises are slides | KPIs in `accelerator.yaml` → typed telemetry events → live dashboards in customer Azure |

---

## Reference scenarios (in `docs/references/`)

- **customer-service-actioning/** — multi-agent service assistant that looks up orders, issues refunds/credits via HITL, updates CRM. Deflection + AHT ROI.
- **rfp-response/** — multi-specialist (pricing · legal · tech · security) aggregator that drafts proposal responses. Response time days → hours; win rate lift.

Flagship itself (sales research & outreach) is fully runnable in `src/`.

---

## What this accelerator does NOT try to be

- Not a runtime platform. No services Microsoft operates for partners.
- Not a cryptographic attestation or governance gate. Consistency is enforced by CI lint + pinned SDK + starter defaults + Copilot shaping — not by Microsoft blocking partners at deploy time.
- Not a DSL. `accelerator.yaml` is ~12 fields of plain YAML. No `spec.agent.yaml`.
- Not IDE-locked. Copilot-first; AGENTS.md mirrors the rules for Cursor, Claude Code, Codex CLI.

---

## Contributing / feedback

- GitHub Issues are the intake for scenario requests, bug reports, pattern suggestions.
- Monthly triage; quarterly blessed-pattern promotions (criteria in `CONTRIBUTING.md`).
- Version matrix is maintained weekly; deprecation policy is N-1 minor.

See `SECURITY.md` for vulnerability reporting and `SUPPORT.md` for channels.
