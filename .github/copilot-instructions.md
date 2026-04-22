# Copilot instructions for this accelerator-based repo

> This file is read by GitHub Copilot (VS Code, Chat, code review) on every interaction in this repo. It encodes the **non-negotiable rules** that make a solution built from this template production-grade and compliant. Keep it in sync with the top-level `AGENTS.md`.

## What this repo is
A partner cloned the **Azure Agentic AI Solution Accelerator** template to build an agentic solution for a specific customer. The flagship shape is a **supervisor + specialist workers** orchestration on Microsoft Agent Framework + Azure AI Foundry. The customer-specific scope lives in `docs/discovery/solution-brief.md`. The accelerator's consistency contract lives in `accelerator.yaml`.

When you help the partner, you MUST preserve every rule below. When a request conflicts with a rule, refuse or propose a compliant alternative — do not "make it work" by weakening a guardrail.

---

## Hard rules — MUST / NEVER

### Identity & secrets
- MUST use `DefaultAzureCredential` or `ManagedIdentityCredential`. NEVER hardcode keys or connection strings.
- MUST resolve secrets from Azure Key Vault via references in Bicep or `DefaultAzureCredential` at runtime.
- NEVER commit `.env`, `*.pfx`, or any file with secrets. Don't weaken `.gitignore`.

### SDK & platform
- MUST use Microsoft Agent Framework (`agent_framework`) with Azure AI Foundry as the model backend.
- MUST retrieve Foundry agents with `AzureAIClient(agent_name=..., use_latest_version=True)`. NEVER construct agent instructions in code — instructions live in the Foundry portal.
- MUST pin SDK versions per `pyproject.toml` / `docs/version-matrix.md`.
- NEVER introduce LangChain, LlamaIndex, Haystack, or any other orchestration SDK. Microsoft Agent Framework only.
- NEVER instantiate `openai.OpenAI(...)` or `AzureOpenAI(...)` directly. Use Agent Framework.

### Agent structure (3-layer pattern)
Every agent lives under `src/scenarios/<scenario>/agents/<agent_name>/` with exactly three files:
- `prompt.py` — `build_prompt(request_data: dict) -> str`
- `transform.py` — `transform_response(response: str) -> dict`
- `validate.py` — `validate_response(response: dict) -> tuple[bool, str]`

Do not hand-scaffold. Use `/add-worker-agent` to create a new agent and wire it into the supervisor.

### Supervisor + workers wiring
- Workers are stateless. Supervisor routes based on intent classification in its prompt.
- Supervisor MUST emit a structured decision record (`src/accelerator_baseline/telemetry.py` event) naming which worker(s) it invoked and why.
- Aggregation (combining worker outputs) happens in an explicit executor, not inside a worker's transform.

### HITL (Human-in-the-Loop)
- MUST gate every side-effect tool through `src/accelerator_baseline/hitl.py.checkpoint(...)`.
- Side-effect = writes to external systems (CRM, ticketing, DB), sends (email, chat, webhook), destructive calls (restart, delete).
- HITL policy declared in `accelerator.yaml -> solution.hitl` AND per-tool in the tool module.
- NEVER bypass HITL "just for a demo." If `hitl = none`, the action MUST be reversible and MUST be logged.

### Grounding / RAG
- MUST use `src/retrieval/ai_search.py` (Azure AI Search) for retrieval. No direct HTTP to content sources.
- MUST return citations. `validate_response` rejects ungrounded factual claims.
- NEVER inject retrieved content into the system prompt without a size cap; chunk and select.

### Telemetry
- MUST emit typed events via `src/accelerator_baseline/telemetry.py`. Custom KPI events declared in `accelerator.yaml -> kpis` MUST appear in code.
- MUST wire Application Insights via `azure-monitor-opentelemetry` in `src/main.py` startup. NEVER disable.
- NEVER use `print()` or ad-hoc logging for observability.

### Responsible AI
- MUST apply Azure AI content filters via IaC (`infra/modules/foundry.bicep`). `controls.content_filters = iac` in `accelerator.yaml`.
- MUST keep `evals/redteam/` XPIA + jailbreak suites passing. New tools trigger new redteam cases.
- MUST flag PII handling in the solution brief; map RAI risks to eval cases.
- See `docs/patterns/rai/README.md` for the full RAI checklist.

### Well-Architected Framework + Azure Landing Zone
- Follow `docs/patterns/waf-alignment/README.md` (reliability · security · cost · op-ex · performance).
- Follow `docs/patterns/architecture/README.md` for topology, hub-spoke, private endpoints.
- Regulated workloads: `controls.private_endpoints = required` AND `controls.key_vault = true`.

### CI gates
- MUST keep `scripts/accelerator-lint.py` green. It reads `accelerator.yaml` + repo state.
- MUST keep `evals/quality/` acceptance thresholds from `accelerator.yaml -> acceptance` green before merge.
- MUST NOT disable the `version-matrix.yml` weekly job.

---

## How to help the partner

### Adding a side-effect tool (e.g., "create a ServiceNow ticket")
1. Tell the partner to run `/add-tool` for a guided scaffold.
2. If coding directly: create `src/tools/<tool_name>.py`, wrap the side effect with `hitl.checkpoint(...)`, emit telemetry, add a unit test, add a redteam case.
3. Register it on the worker agent that should use it.
4. Never skip HITL.

### Adding a specialist worker agent
1. Run `/add-worker-agent`.
2. Create `src/scenarios/<scenario>/agents/<agent_name>/{prompt.py, transform.py, validate.py}`.
3. Register the agent in `accelerator.yaml` under `scenario.agents[]` and wire it into `src/scenarios/<scenario>/workflow.py`.
4. Update `src/scenarios/<scenario>/agents/supervisor/prompt.py` with the new worker's capability and routing cue.

### Switching solution shape
- The `single-agent` and `chat-with-actioning` variants are **candidate patterns**, documented in `patterns/<variant>/README.md` — they are not yet materialized as drop-in packages. Run `/switch-to-variant single-agent` (or `chat-with-actioning`) to get a step-by-step walkthrough of re-authoring the scenario under `src/scenarios/<new-id>/` for the target shape; flagship HITL / telemetry / retrieval / content-filter invariants stay regardless of variant.

### Starting a new customer
- Run `/discover-scenario` to fill `docs/discovery/solution-brief.md`.
- Then `/scaffold-from-brief` to customize prompts, tools, retrieval, HITL, evals, manifest.

---

## Things that will fail code review / lint (don't do these)
- `openai.OpenAI()` / `AzureOpenAI()` direct instantiation
- `requests.post` to any LLM endpoint
- Hardcoded resource names, subscription IDs, tenant IDs
- Adding a side-effect tool without `hitl.checkpoint`
- Editing `src/accelerator_baseline/` to wrap Azure SDKs (it is for primitives only)
- Writing agent instructions in code instead of Foundry portal
- Disabling content filters, evals, or telemetry
- `time.sleep` in async code, bare `except:`, swallowing errors silently

---

## Reference
- Top-level: `README.md`, `QUICKSTART.md`, `AGENTS.md`
- Engagement: `accelerator.yaml`, `docs/discovery/solution-brief.md`
- Patterns: `docs/patterns/{architecture,waf-alignment,rai}/README.md`
- Scenarios: `docs/references/`
- Version matrix: `docs/version-matrix.md`
