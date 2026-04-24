# Agentic AI Solution Accelerator

> **A GitHub template partners clone to get a customer-specific agentic AI deployment live in days, not months.** Full engagement motion (discovery → UAT → handover → measure) is weeks, and documented honestly below.

**Flagship scenario:** Sales Research & Personalized Outreach — a supervisor agent routes a research request across specialist workers (Account Researcher, ICP/Fit Analyst, Competitive Context, Outreach Personalizer) and returns a grounded, citeable sales brief with a CRM-ready outreach draft. Human-in-the-loop gates every CRM write and every email send.

**Stack:** Microsoft Agent Framework · Azure AI Foundry · Azure AI Search · Managed Identity · Key Vault · Container Apps · Application Insights · `azd` for infra.

**Adoption model:** `gh repo create --template` → Copilot-guided discovery → `azd up` → iterate in VS Code → merge through CI gates.

---

## Start here — pick your goal

- 🧭 **Scope an engagement / run discovery with the customer**
  → [`docs/partner-playbook.md`](docs/partner-playbook.md) — end-to-end delivery motion (7 stages, SOW scoping)
  → Run `/delivery-guide` in Copilot Chat for a live walk-through
  → Discovery kit: [`docs/discovery/how-to-use.md`](docs/discovery/how-to-use.md) (read first; sequences the 5 artifacts)
  → *Customer already gave you a PRD/BRD/spec?* Run `/ingest-prd` first to pre-draft the brief — see [`docs/discovery/how-to-use.md`](docs/discovery/how-to-use.md) §"If the customer already provided a PRD / BRD / functional spec"

- 🛠️ **Do a first sandbox deploy (rehearsal)**
  → [`docs/enablement/hands-on-lab.md`](docs/enablement/hands-on-lab.md) — 7-lab walkthrough in your own sandbox subscription
  → *Strongly recommended before your first customer-facing deployment.*

- ⚡ **Skim the partner motion in 15 min**
  → [`QUICKSTART.md`](QUICKSTART.md) — the 5-step happy path

- 🔧 **Troubleshoot setup, prereqs, secrets, `azd up` issues**
  → [`docs/getting-started.md`](docs/getting-started.md) — authoritative setup + troubleshooting reference

- 🏛️ **Handover to the customer ops team**
  → [`docs/customer-runbook.md`](docs/customer-runbook.md) + your engagement-specific handover packet (endpoint URLs, HITL approver wiring, alert rules, SLAs, rollback, customer-specific deviations). Template: [`docs/handover/handover-packet-template.md`](docs/handover/handover-packet-template.md). Partner packet wins on conflict.

> **Wearing both hats at a small partner?** Start with `docs/partner-playbook.md` to understand the motion, then do `docs/enablement/hands-on-lab.md` for the mechanics.

**Precedence when guidance disagrees:** chatmodes in `.github/chatmodes/` → `docs/partner-playbook.md` (motion) + `docs/getting-started.md` (setup) → this README.

---

## How partners use this

```bash
gh repo create <customer>-agents \
  --template Azure/agentic-ai-solution-accelerator --private
cd <customer>-agents && code .
```

Then in VS Code:

1. `/discover-scenario` — Copilot interviews you (or the customer) and writes `docs/discovery/solution-brief.md`: business context, success criteria, ROI hypothesis, constraints, acceptance evals. **Follow [`docs/discovery/how-to-use.md`](docs/discovery/how-to-use.md) for the full sequence before running the chatmode.**
2. `/scaffold-from-brief` — Copilot adapts the repo to the brief (prompts, tools, retrieval, HITL, evals, telemetry, manifest).
3. `azd up` — provisions Foundry + Search + KV + ACA + App Insights in customer Azure and deploys the agents.
4. Iterate in Copilot Chat; every PR is gated by `scripts/accelerator-lint.py`, `evals/quality/`, and `evals/redteam/`.

Full walkthrough: **[QUICKSTART.md](QUICKSTART.md)**.

---

## What's in the box

### 🧭 For the partner delivery lead
- [`docs/partner-playbook.md`](docs/partner-playbook.md) — end-to-end delivery motion: discover → scaffold → provision → iterate → UAT → handover → measure
- [`docs/discovery/`](docs/discovery/) — discovery kit
  - [`how-to-use.md`](docs/discovery/how-to-use.md) — **read first**; sequences the 5 artifacts
  - [`use-case-canvas.md`](docs/discovery/use-case-canvas.md) — 1-page exec alignment (pre-workshop; workshop-readiness gate)
  - [`SOLUTION-BRIEF-GUIDE.md`](docs/discovery/SOLUTION-BRIEF-GUIDE.md) — how to facilitate the discovery workshop
  - [`discovery-workbook.csv`](docs/discovery/discovery-workbook.csv) — live capture template for the workshop
  - [`solution-brief.md`](docs/discovery/solution-brief.md) — canonical engagement doc (output of `/discover-scenario`)
  - [`roi-calculator.xlsx`](docs/discovery/roi-calculator.xlsx) — ROI hypothesis workbook (filled **after** the brief)

### 🛠️ For the partner engineer
- [`QUICKSTART.md`](QUICKSTART.md) — the 5-step happy path
- [`docs/enablement/hands-on-lab.md`](docs/enablement/hands-on-lab.md) — 7-lab sandbox rehearsal (strongly recommended before first customer)
- [`docs/getting-started.md`](docs/getting-started.md) — prereqs, secrets, sandbox smoke-test, troubleshooting
- [`docs/foundry-tool-catalog.md`](docs/foundry-tool-catalog.md) — when to use each Foundry Agent Service tool
- [`docs/agent-specs/`](docs/agent-specs/) — per-agent Foundry bootstrap specs
- [`docs/version-matrix.md`](docs/version-matrix.md) — known-good SDK pins (weekly CI validates against latest)

### 🏛️ For handover to customer ops
- [`docs/customer-runbook.md`](docs/customer-runbook.md) — day-2 operations (monitoring, killswitch, evals re-run, model swap, secret rotation, incident, scaling). **Plus** your engagement-specific handover packet; partner packet wins on conflict.
- [`docs/handover/handover-packet-template.md`](docs/handover/handover-packet-template.md) — template for the engagement-specific packet (environments, HITL wiring, alerts, killswitch, rollback, customer-specific deviations, SLAs, contacts).

### 📐 Reference patterns & variants
- Architecture & compliance: [Architecture](docs/patterns/architecture/README.md) · [WAF alignment](docs/patterns/waf-alignment/README.md) · [Responsible AI](docs/patterns/rai/README.md) · [Azure AI Landing Zone](docs/patterns/azure-ai-landing-zone/README.md)
- Scenario variants (candidate patterns, not drop-ins): [single-agent](patterns/single-agent/README.md) · [chat-with-actioning](patterns/chat-with-actioning/README.md)
- Reference scenarios (walkthroughs): [customer-service-actioning](docs/references/customer-service-actioning/README.md) · [rfp-response](docs/references/rfp-response/README.md)

### ⚙️ Under the hood

<details>
<summary>Full code + infra directory tree (click to expand)</summary>

```
agentic-ai-solution-accelerator/
├── accelerator.yaml              engagement manifest — scenario contract + acceptance + controls + KPIs
├── src/
│   ├── main.py                   scenario-agnostic FastAPI; mounts the scenario endpoint from manifest
│   ├── workflow/                 framework: BaseWorkflow Protocol + scenario registry (load_scenario)
│   ├── retrieval/                generic SearchRetriever(index_name) against Azure AI Search
│   ├── tools/                    HITL-gated side-effect tools (CRM write, email send)
│   ├── accelerator_baseline/     partner-owned primitives: telemetry, HITL, killswitch, evals, cost
│   └── scenarios/                scenario instances loaded via manifest
│       └── sales_research/       flagship: schema, workflow factory, retrieval schema
│           └── agents/           supervisor + 4 workers (three-layer: prompt, transform, validate)
├── infra/                        Bicep + azd (Foundry GA + content filter, Search, KV, ACA, App Insights)
├── evals/
│   ├── quality/                  golden cases + CI gates from accelerator.yaml.acceptance
│   └── redteam/                  XPIA + jailbreak + brief-specific RAI cases
├── patterns/
│   ├── single-agent/             variant: when orchestration isn't needed
│   └── chat-with-actioning/      variant: conversational front-end with tools
├── docs/
│   ├── getting-started.md        setup, prereqs, sandbox smoke-test, troubleshooting
│   ├── partner-playbook.md       end-to-end partner motion (7 stages)
│   ├── discovery/                discovery kit (5 artifacts + how-to-use sequencing guide)
│   ├── references/               reference scenarios (customer service, RFP response)
│   ├── agent-specs/              per-agent Foundry bootstrap specs (flagship + candidates)
│   ├── foundry-tool-catalog.md   when-to-use matrix for Foundry Agent Service tools
│   ├── customer-runbook.md       day-2 ops for the customer team
│   ├── enablement/
│   │   └── hands-on-lab.md       partner-team self-paced first-deployment walkthrough (7 labs)
│   ├── patterns/                 architecture · WAF · RAI · Azure AI Landing Zone
│   └── version-matrix.md         known-good SDK pins (weekly CI validates against latest)
├── .github/
│   ├── copilot-instructions.md   hard rules: Agent Framework, MI, HITL, evals, RAI
│   ├── chatmodes/                discover-scenario, scaffold-from-brief, delivery-guide, add-*, switch-to-variant
│   └── workflows/                lint, evals, deploy, version-matrix (weekly pinned-latest)
├── AGENTS.md                     IDE-agnostic mirror of copilot-instructions (Cursor/Claude/Codex)
└── scripts/
    ├── accelerator-lint.py       ~30 deterministic policy checks (local + CI), AST-only
    ├── scaffold-scenario.py      materialize a new scenario skeleton (CLI behind /scaffold-from-brief)
    ├── foundry-bootstrap.py      reads agents from manifest; creates/updates Foundry agents
    └── seed-search.py            reads indexes from manifest; creates + seeds each
```

</details>

---

## Why this instead of starting from scratch

| Without the accelerator | With the accelerator |
|---|---|
| Partner re-invents auth, telemetry, HITL, evals, RAI posture every engagement | Ships as partner-owned source in `src/accelerator_baseline/`; used from day one |
| Discovery notes disconnected from code | Solution Brief drives scaffolding, evals, manifest, dashboards |
| "Should we use single-agent or supervisor?" → guesswork | Flagship + two variants + four reference scenarios; pick-and-scaffold |
| Compliance & WAF done at the end (if at all) | Enforced from commit 1 via `copilot-instructions.md` + CI lint + IaC content filters |
| ROI promises are slides | KPIs declared in `accelerator.yaml.kpis[]`; partners wire a telemetry event per KPI in the scenario code, then monitor in App Insights + the shipped workbook template (`infra/dashboards/roi-kpis.json`) |

---

## Reference scenarios (in `docs/references/`)

- **customer-service-actioning/** — multi-agent service assistant that looks up orders, issues refunds/credits via HITL, updates CRM. Deflection + AHT ROI.
- **rfp-response/** — multi-specialist (pricing · legal · tech · security) aggregator that drafts proposal responses. Response time days → hours; win rate lift.

Flagship itself (sales research & outreach) is fully runnable under `src/scenarios/sales_research/` — loaded at startup via the top-level `scenario:` block in `accelerator.yaml`. Add a sibling scenario with `python scripts/scaffold-scenario.py <id>`; the framework mounts it the same way the flagship is mounted.

### Candidate pattern variants (not shipped runnable yet)

- **Zero Trust posture analysis** — chat-based, file-upload (CSV/Excel) assessment with multi-turn iteration. Fits a different solution shape than the flagship (conversational + artifact ingest). Tracked in `docs/agent-specs/README.md`; promote to `docs/references/zero-trust/` when a customer engagement motivates it.

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
