# Azure Agentic AI Solution Accelerator

> **What this is:** a content pack + Copilot IDE kit + validator that helps Microsoft delivery partners ship agentic AI solutions on Azure for their customers, following WAF best practices, RAI guidance, and the latest Azure AI Foundry patterns.
>
> **Audience:** Microsoft delivery partners (engineers, architects, delivery leads) who have a customer + a use case + want to vibe-code the solution with GitHub Copilot in VS Code.
>
> **Status:** Phase A draft — **internal preview**. Not all tooling is implemented yet. See [docs/getting-started.md](docs/getting-started.md) for what's usable today.

---

## What you get

| # | Asset | Purpose |
|---|---|---|
| 1 | **Patterns + guidance** ([`content/patterns/`](content/patterns)) | Architecture patterns, WAF-by-pillar decisions, RAI posture — the intellectual payload. |
| 2 | **Copilot IDE kit** ([`.github/copilot-instructions.md`](.github/copilot-instructions.md), [`.github/chatmodes/`](.github/chatmodes)) | Drops into your customer repo's `.github/`. Shapes every Copilot code suggestion so it lands in-pattern. |
| 3 | **Spec schema + validator** ([`delivery-assets/schema/spec.schema.json`](delivery-assets/schema/spec.schema.json), [`tools/validate-spec.py`](tools/validate-spec.py)) | Declarative solution description. Validator runs in your CI and fails the build on drift. |
| 4 | **Reference scenarios** ([`examples/scenarios/`](examples/scenarios)) | Three worked scenarios (supplier risk, IT Ops triage, knowledge concierge) to study + copy from. |
| 5 | **azd templates** ([`examples/azd-templates/`](examples/azd-templates)) | Five Azure-deployable starting points, one per bundle. |
| 6 | **Baseline pip packages** ([`baseline/`](baseline), [`baseline-*/`](.)) | T1 core + T2 profile-required primitives (auth, telemetry, cost ceiling, kill switch, HITL, actions). Pin in your customer repo. |
| 7 | **Partner playbook + templates** ([`docs/`](docs)) | Phase-by-phase guidance, SoW template, decision-record template, RAI scoping minutes template. |

---

## How partners use this — three-layer consistency model

Partners don't clone this repo wholesale. They **scaffold a new customer repo from this accelerator**, which drops the three consistency layers into their customer engagement:

```
 ┌────────────────────────────────────────────────────────────────────┐
 │  Layer 1 — Scaffolding (repo creation)                             │
 │  `baseline new-customer-repo --bundle <bundle> --scenario <name>`  │
 │  drops IDE kit, CI, validator, pinned baseline, a reference        │
 │  scenario as starting code, Spec skeleton. Partner starts from a   │
 │  correct repo, not a blank one.                                    │
 └────────────────────────────────────────────────────────────────────┘
                                ↓
 ┌────────────────────────────────────────────────────────────────────┐
 │  Layer 2 — Copilot IDE kit (authoring time)                        │
 │  copilot-instructions.md + chatmode + prompts sit in .github/.     │
 │  Every Copilot prompt is shaped by our patterns. Copilot writes    │
 │  code that uses baseline primitives, declares tools in Spec, wires │
 │  HITL for side-effects, emits required telemetry.                  │
 └────────────────────────────────────────────────────────────────────┘
                                ↓
 ┌────────────────────────────────────────────────────────────────────┐
 │  Layer 3 — Validator (CI time)                                     │
 │  On every PR, validator checks Spec conformance, bundle↔profile,   │
 │  HITL wiring, grounding classification, WAF patterns. Fails build  │
 │  on drift.                                                         │
 └────────────────────────────────────────────────────────────────────┘
```

Good-faith partners following the guidance land in-pattern by default. Validator catches drift before merge.

> **Important:** this accelerator is **community-supported, best-effort**. It is NOT a Microsoft-supported managed product. Partners own their customer deployments end-to-end. See [SUPPORT.md](SUPPORT.md).

---

## First steps

- **New here?** Read [docs/getting-started.md](docs/getting-started.md) — the partner journey in plain English.
- **Evaluating fit?** Run [`docs/enablement/self-assessment.md`](docs/enablement/self-assessment.md) against your org.
- **Onboarding your partner org?** Work through [`docs/enablement/partner-onboarding-checklist.md`](docs/enablement/partner-onboarding-checklist.md).
- **Ready to scope a customer engagement?** Use [`docs/partner-playbook.md`](docs/partner-playbook.md).
- **Designing the solution?** Read [`content/patterns/`](content/patterns) and study [`examples/scenarios/`](examples/scenarios).
- **Need to know what you may / may not change?** See [`docs/customization-guide.md`](docs/customization-guide.md).

---

## Repo layout

```
.
├── .github/
│   ├── CODEOWNERS
│   ├── copilot-instructions.md          # ships INTO every scaffolded customer repo
│   └── chatmodes/delivery-guide.chatmode.md
├── content/
│   └── patterns/
│       ├── architecture/                # topology, orchestration, HITL placement
│       ├── waf-alignment/               # per-pillar Azure-agentic-AI decisions
│       └── rai/                         # content filter, groundedness, red-team
├── docs/
│   ├── getting-started.md               # ← start here
│   ├── partner-playbook.md              # phase-by-phase engagement guidance
│   ├── customization-guide.md           # patterns to follow + where to diverge
│   ├── enablement/                      # onboarding + self-assessment
│   ├── templates/                       # SoW, decisions, RAI scoping minutes
│   └── runbooks/                        # operational playbooks (Phase C)
├── examples/
│   ├── specs/                           # concrete Spec examples
│   ├── scenarios/                       # 3 reference scenarios (+ starter)
│   └── azd-templates/                   # 5 blessed bundles as azd templates
├── delivery-assets/
│   └── schema/spec.schema.json          # Spec schema
├── baseline/                            # T1 core pip pkg
├── baseline-cli/                        # `baseline` CLI pip pkg
├── baseline-drift/                      # T2 portal-drift telemetry
├── baseline-feedback/                   # T2 feedback + eval telemetry
├── baseline-hitl/                       # T2 human-in-the-loop queue
├── baseline-actions/                    # T2 side-effect tool wrappers
├── baseline-cache/                      # T3 reference-only
├── tools/                               # validators + scaffolder
├── SUPPORT.md                           # community best-effort
├── CONTRIBUTING.md, SECURITY.md, LICENSE
```

---

## Bundles at a glance

| Bundle | Side-effect tools | Network | Profile(s) |
|---|---|---|---|
| `sandbox-only` | ❌ | public | dev-sandbox · guided-demo |
| `retrieval-prod` | ❌ | public | prod-standard |
| `retrieval-prod-pl` | ❌ | private-link | prod-privatelink |
| `actioning-prod` | ✅ (HITL required) | public | prod-standard |
| `actioning-prod-pl` | ✅ (HITL required) | private-link | prod-privatelink |

Bundle variants are expressed via Spec parameters + profiles, NOT new bundles. See [`docs/customization-guide.md`](docs/customization-guide.md) for the rationale.

---

## Contributing

Internal accelerator engineering team owns the patterns + baseline + validator. Partners contribute reference scenarios, runbooks, and field feedback via PRs + issues. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License + support

MIT license on the content + code. See [LICENSE](LICENSE) and [SUPPORT.md](SUPPORT.md).
