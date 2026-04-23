# Agent guidance — works across Copilot, Cursor, Claude Code, Codex CLI
#
# This file mirrors `.github/copilot-instructions.md` for IDE-agnostic tools
# that read AGENTS.md (OpenAI Codex, Cursor, Claude Code). Keep them in sync.
# The authoritative copy is `.github/copilot-instructions.md`; this file
# redirects with the hard rules partners must always enforce.

## Template intent
This repo is an Azure Agentic AI Solution Accelerator. A partner clones it
as a template, fills `docs/discovery/solution-brief.md` with a customer,
runs `/scaffold-from-brief`, then customizes with your help. Every change
you help with MUST preserve the accelerator's guardrails.

## Non-negotiable rules (MUST / NEVER)

### Identity & secrets
- **MUST** use `DefaultAzureCredential` or `ManagedIdentityCredential`. Never embed keys or connection strings in code.
- **MUST** resolve secrets via Azure Key Vault references (Bicep) or `DefaultAzureCredential` (runtime). Never hardcode.
- **NEVER** commit `.env` files or secrets. `.gitignore` covers the common ones; don't weaken it.

### SDK & platform
- **MUST** use Microsoft Agent Framework (`agent_framework`) with Azure AI Foundry as the model backend. Do not introduce other orchestration frameworks.
- **MUST** retrieve Foundry agents via `AzureAIClient(agent_name=..., use_latest_version=True)`; never construct agent instructions in code. Instructions live in the Foundry portal.
- **MUST** pin SDK versions per `pyproject.toml`. See `docs/version-matrix.md`; a weekly CI job validates against latest.

### Agent architecture (3-layer pattern per agent)
Every agent lives under `src/scenarios/<scenario>/agents/<agent_name>/` with three files:
- `prompt.py`   — `build_prompt(request_data) -> str`
- `transform.py` — `transform_response(response) -> dict`
- `validate.py`  — `validate_response(response) -> (bool, str)`
Add a new agent by running `python scripts/scaffold-agent.py <agent_id> --scenario <scenario-id> --capability "<one-sentence capability>" [--depends-on a,b] [--optional]`; do not scaffold by hand. The scaffolder edits the declarative `WORKERS: dict[str, WorkerSpec]` registry in `src/scenarios/<scenario>/workflow.py` — that single dict is the supervisor DAG's only attachment point — and patches `agents/__init__.py`, creates the three-layer files, and writes a Foundry agent spec stub. It is transactional (rolls back on any failure) and re-run safe. You must still paste the printed YAML snippet into `accelerator.yaml -> scenario.agents[]` and add the new agent id to at least one golden case's `exercises` array (the `agent_has_golden_case` lint blocks otherwise). See the `/add-worker-agent` chat mode for the full flow. Scaffold a new *scenario* (sibling to `sales_research/`) with `python scripts/scaffold-scenario.py <id>`.

### HITL (Human-in-the-Loop)
- **MUST** gate every side-effect tool (writes, sends, destructive actions) through `src/accelerator_baseline/hitl.py`.
- **MUST** declare HITL policy in `accelerator.yaml -> solution.hitl` and per-tool in the tool module.
- **NEVER** let an agent execute a side-effect without an approved HITL checkpoint unless `accelerator.yaml -> solution.hitl = none` AND the action is reversible.

### Telemetry
- **MUST** emit typed events via `src/accelerator_baseline/telemetry.py`. Custom KPI events declared in `accelerator.yaml -> kpis` must appear in code.
- **MUST** wire Application Insights via `azure-monitor-opentelemetry` in `src/main.py` startup. Never disable.

### Grounding / RAG
- **MUST** cite retrieved sources in responses. `validate.py` must reject ungrounded responses when the agent claims facts.
- **MUST** use `src/retrieval/ai_search.py` (Azure AI Search) rather than direct HTTP to content sources.

### Responsible AI
- **MUST** have content filters applied via IaC (`infra/`), not portal. `controls.content_filters = iac` in `accelerator.yaml`.
- **MUST** keep `evals/redteam/` XPIA + jailbreak cases green in CI before deploy.
- **MUST** flag PII handling in the solution brief; RAI risks mapped to eval cases.
- See `docs/patterns/rai/README.md` for full RAI checklist.

### Well-Architected Framework (WAF) + Azure Landing Zone alignment
- **MUST** follow `docs/patterns/waf-alignment/README.md` for reliability, security, cost, op-ex, performance.
- **MUST** follow `docs/patterns/architecture/README.md` for topology, hub-spoke, private endpoints when required.
- Private endpoints: `controls.private_endpoints = required` for any regulated workload.

### CI & lint
- **MUST** keep `scripts/accelerator-lint.py` passing. Reads `accelerator.yaml` + repo state; enforces the rules above.
- **MUST** keep `evals/quality/` acceptance gates green before merge. Thresholds live in `accelerator.yaml -> acceptance`.

## Forbidden patterns (will fail lint / review)
- Constructing `openai.OpenAI()` or `AzureOpenAI()` directly. Use Agent Framework.
- `requests.post(...)` to an LLM endpoint. Use the SDK.
- Hardcoded resource names/IDs. Use env + Bicep params.
- `print()` for observability. Use structured telemetry.
- Editing `src/accelerator_baseline/` to wrap Azure SDKs (it is for primitives only).
- Moving agent instructions into code. They live in Foundry portal.

## When adding things
- **New tool** → `/add-tool` chat mode → creates `src/tools/<tool>.py` with HITL scaffolding + unit test.
- **New worker agent** → `/add-worker-agent` chat mode → creates the 3-layer module + wires into supervisor.
- **New Azure environment** (partner dev/staging/customer sub) → `/deploy-to-env` chat mode → adds entry to `deploy/environments.yaml`, creates the GitHub Environment, wires OIDC, dispatches a deploy. Never hand-edit `deploy.yml` to add envs; the manifest + `resolve-env` job is the contract. The azd env name is **always** derived from `deploy/environments.yaml` — never set `vars.AZURE_ENV_NAME`.
- **Switching pattern** → `/switch-to-variant` chat mode → walks through re-authoring the scenario under `src/scenarios/<new-id>/` toward a `single-agent` or `chat-with-actioning` shape (candidate patterns in `patterns/<variant>/README.md`; not drop-in packages).
- **Starting a new customer engagement** → `/discover-scenario` then `/scaffold-from-brief`.

## References
- Onboarding: `docs/getting-started.md`
- Discovery guide: `docs/discovery/SOLUTION-BRIEF-GUIDE.md`
- Agent specs (Foundry bootstrap + Agent Hub references): `docs/agent-specs/README.md`
- Patterns: `docs/patterns/{architecture,rai,waf-alignment}/README.md`
- Version matrix: `docs/version-matrix.md`
- Scenario catalog: `docs/references/`
