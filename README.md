# Azure Agentic AI Solution Accelerator

> **Status:** v1 draft (private) — **controlled-lighthouse** release.
> **License:** MIT + CLA.
> **Support:** see [SUPPORT.md](SUPPORT.md). No SLA outside blessed bundles + valid attestation.

## What this is

A partner-deployable kit for building production-grade **agentic AI solutions** on Azure AI Foundry, aligned to the Microsoft Well-Architected Framework (WAF) including the AI workload and Responsible AI (RAI) pillars.

Partners vibecode the **business layer** per customer using **GitHub Copilot in VS Code**, guided by this accelerator's:

- **Tiered platform baseline** (T1 core + T2 profile-required sub-packages) — hardened, versioned, supported
- **5 blessed bundles** (sandbox-only, retrieval-prod, retrieval-prod-pl, actioning-prod, actioning-prod-pl) with matching **azd templates**
- **Spec-driven materializers** (params, evals, dashboards, alerts) — config from a single `spec.yaml`
- **Copilot IDE kit** — custom instructions, chat modes, prompts, MCP tool configs
- **Attestation + supportability gates** — make support + RAI posture verifiable per deploy

## What this is NOT

- Not a shipped runtime you extend.
- Not a deterministic codegen.
- Not a SaaS.
- Not "the Azure agentic standard" — an **opinionated v1 path**. Broader ecosystem is v1.5+.

## Who should use it

Microsoft-aligned partners delivering agentic AI solutions to customers on Azure who want:

- A repeatable path to a supportable production deploy
- A clear WAF + RAI story for customer reviews
- Compatibility with Foundry + Copilot-based delivery

## 3 paths (choose one)

| Path | Goal | Typical duration | Output |
|---|---|---|---|
| **A — Sandbox / Fast** | POC or demo | hours (certified partners) | Running sandbox deploy; no attestation |
| **B — Production / Enterprise** | Customer production solution | weeks | Attested deploy, full WAF + RAI + support |
| **C — Expansion** | Add scenarios on top of an existing attested deploy | days | Incremental attested scope |

See [`docs/partner-playbook.md`](docs/partner-playbook.md).

## Quickstart (partner engineers)

```bash
# 1. Fork/clone this repo as the template for a new customer engagement
# 2. Scaffold a customer repo
python tools/new-customer-repo.py --name "acme-supplier-risk" --bundle "retrieval-prod"
# 3. Open the scaffolded repo in VS Code; Copilot is pre-configured
# 4. Follow docs/partner-playbook.md (phase-gated; ~7 phases)
# 5. Deploy
azd up  # uses bundle-specific azd template
# 6. Attest
baseline attest --capture && baseline attest --issue
# 7. Deploy-gate verification
baseline deploy --verify <attestation-id>
```

## Repository layout (top level)

```
baseline/              # T1 core pkg (pip: azure-agentic-baseline)
baseline-drift/        # T2 profile-required (prod-standard+)
baseline-feedback/     # T2 profile-required (prod-standard+)
baseline-hitl/         # T2 profile-required (side-effect tools)
baseline-actions/      # T2 profile-required (side-effect tools)
baseline-cache/        # T3 reference only (not attestation-covered)
baseline-cli/          # CLI: doctor, upgrade, materialize, attest, reconcile, waive, sbom
delivery-assets/       # Bicep modules, workflows, schema, scaffolding (synced via upgrade)
azd-templates/         # One per blessed bundle (supported fast path)
compatibility/         # Release manifests, drift classification, upgrade transaction model
.github/               # copilot-instructions.md, chatmodes, prompts, agents, MCP
patterns/              # Architecture, WAF, RAI patterns
examples/              # STUDY-ONLY annotated code references
specs/                 # Spec schema + reference + example specs
packs/                 # Scenario packs (supplier-risk, IT ops, knowledge concierge)
discovery/             # Qualification matrix, use-case canvas, RAI IA, WAF checklist
tools/                 # Validators, scaffolders
docs/                  # Playbook, runbooks, governance, RAI, enablement, templates
```

## Key references

- [Partner playbook](docs/partner-playbook.md) — the main phase-gated guide
- [Supported customization boundary](docs/supported-customization-boundary.md) — what you MAY and MAY NOT change
- [Spec schema](delivery-assets/schema/spec.schema.json) — the single source of truth for a solution
- [Upgrade transaction model](compatibility/upgrade-transaction-model.md) — how you stay current + supported
- [Attestation scope](docs/rai/attestation-scope.md) — what attestation covers + what it doesn't
- [Governance board charter](docs/governance/governance-board-charter.md) — who approves waivers
- [Copilot instructions](.github/copilot-instructions.md) — normative rules for vibecoding

## Status: private preview

This repo is currently **private / internal**. Partners receive a fork + engagement-specific access. Public release is v1.5+.

## Contact

See [CODEOWNERS](.github/CODEOWNERS).
