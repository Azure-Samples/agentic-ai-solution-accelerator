---
description: Define grounding for the scenario — pick FoundryIQ Knowledge Base versus no grounding per agent, declare AI Search indexes underneath FoundryIQ, and list any Foundry portal catalog tools each agent should call.
tools: ['codebase', 'editFiles', 'search', 'runCommands']
---

# /define-grounding — wire knowledge + tools to each worker

Use this after `/scaffold-from-brief` (or any time grounding shifts) to declare **how each worker gets its facts and which side tools it can call**. Outcome: a fully populated `scenario.agents[]` block in `accelerator.yaml` plus matching `scenario.retrieval.indexes[]` entries, validated by `scripts/accelerator-lint.py`.

This is **declarative only** — you don't write Python, you don't click around the Foundry portal. The accelerator's startup bootstrap (`src/bootstrap.py`) reads the manifest on the next `azd deploy` and provisions FoundryIQ Knowledge Sources + Knowledge Bases + agent attachments. Partner-attached catalog tools (Foundry portal) are preserved across deploys (Phase 2b).

## Preconditions
- `docs/discovery/solution-brief.md` is complete (section 5 names the grounding sources and any external systems the workers must call).
- `accelerator.yaml -> scenario.agents[]` lists every worker (each entry has at minimum `id` and `foundry_name`).
- The Bicep-provisioned AI Search account exists (it underpins FoundryIQ — created automatically by `azd up`).

## Step 1 — Pick the grounding mode per worker

Two modes are supported. **Always start with `foundry_tool`** unless the worker is purely transformational (e.g., a router or a formatter) and genuinely doesn't read facts.

| Mode | When to pick it | What you must add |
|---|---|---|
| `foundry_tool` | Worker needs grounded facts (any factual claim, citation, or retrieval). FoundryIQ is the consolidated enterprise knowledge layer; AI Search lives **underneath** it. | A `retrieval:` block on the agent + an entry in `scenario.retrieval.indexes[]`. |
| `none`         | Worker is purely transformational — receives upstream worker outputs and reshapes them. No external facts. | Nothing under `retrieval:` (omit the block entirely). |

For `foundry_tool` mode, paste this snippet under the matching `scenario.agents[]` entry, edit values, and remove the comments:

```yaml
- id: <worker_id>
  foundry_name: accel-<scenario-id>-<worker_id_with_dashes>
  retrieval:
    mode: foundry_tool      # FoundryIQ Knowledge Base — preferred
    index: <index_name>     # must match a name in scenario.retrieval.indexes[]
    top_k: 5
    query_type: vector_semantic_hybrid
```

## Step 2 — Declare each AI Search index under FoundryIQ

For each unique `index` name referenced above, add (or confirm) an entry in `scenario.retrieval.indexes[]`:

```yaml
scenario:
  retrieval:
    indexes:
      - name: <index_name>
        seed: data/samples/<index_name>.json   # bootstrap loads this on first deploy
        schema: retrieval:index_definition     # or a partner-defined schema callable
        # source_data_fields are the per-document metadata FoundryIQ surfaces as
        # citation fields. Defaults to ["source"] when omitted. Extend with any
        # fields you want the worker to cite alongside the source URL.
        source_data_fields:
          - source
          - <other_metadata_field>
```

Two lint rules guard this block:
- `retrieval-source-data-fields` — every field listed must exist in the index schema (the schema callable's `SearchIndex(fields=[...])`).
- `retrieval.indexes[*].schema` — the ref must resolve to a callable on import.

## Step 3 — List Foundry portal catalog tools (optional)

If a worker needs an external system call covered by the Foundry built-in tool catalog (1300+ MCP tools — ServiceNow, Confluence, GitHub, Jira, etc.), declare it on the agent so the manifest stays the contract:

```yaml
- id: ticket_creator
  foundry_name: accel-<scenario-id>-ticket-creator
  retrieval:
    mode: foundry_tool
    index: tickets
  catalog_tools:                  # optional; partner-attached in the Foundry portal
    - servicenow_create_incident
    - github_open_issue
```

The accelerator does **not** attach catalog tools through Bicep — the catalog is too dynamic to model declaratively. After `azd deploy`, attach each tool in the Foundry portal under the agent's **Tools** section:

> **Foundry portal — Agents → `<foundry_name>` → Tools → Add tool → Built-in tools → pick from catalog → Save.**

Bootstrap (`src/bootstrap.py`) preserves these attachments across future deploys; only the agent's instructions and model are rewritten on each `azd deploy`. The `catalog_tools[]` entry exists for documentation and lint coverage — the runtime contract is whatever is attached in the portal.

### Side-effect catalog tools require HITL

Any catalog tool that **writes, sends, or deletes** in an external system must be gated by Human-in-the-Loop. The accelerator's `src/accelerator_baseline/hitl.py` only wraps in-process tools (`src/tools/<tool>.py`); catalog tools call out from inside Foundry and bypass that wrapper. To gate them, you have two options:

1. **(Recommended) Re-implement as an in-process tool.** Run `/add-tool` to create `src/tools/<tool_name>.py`; the scaffolder wraps it with `hitl.checkpoint(...)` and emits the right telemetry. Then **do not** attach the matching catalog tool in the portal — your Python wrapper supersedes it.
2. **Keep it as a catalog tool, with portal-side approvals.** Configure the action's "Requires approval" workflow inside the Foundry portal. Document the approver in your runbook. The accelerator will still capture the call in the agent's run trace (visible in the Foundry portal trace UI).

The lint rule `catalog-tool-hitl` warns when a catalog tool with a side-effect-shaped name (`*_create_*`, `*_send_*`, `*_delete_*`, `*_update_*`, `*_post_*`) is attached without a matching `src/tools/<tool>.py` HITL wrapper, so the partner can't accidentally ship an unapproved write path.

## Step 4 — Validate

```bash
python scripts/accelerator-lint.py     # 0 blocking, 0 warning expected
python -c "from src.main import app; print('OK')"
```

If lint fails on `scenario-manifest`, your `retrieval.mode` or schema ref is wrong. If it fails on `retrieval-source-data-fields`, a `source_data_fields` entry doesn't exist in the index schema. If the lint warns on `catalog-tool-hitl`, follow the side-effect guidance above.

## What happens on the next `azd deploy`

`src/bootstrap.py` reads `accelerator.yaml`, then for every `foundry_tool` agent:
1. Provisions a Knowledge Source (AI Search index ↔ FoundryIQ wrapper) if absent.
2. Provisions a Knowledge Base bound to that source if absent.
3. Attaches an MCP tool to the agent pointing at the Knowledge Base.
4. Refreshes instructions + model from `docs/agent-specs/<foundry_name>.md`.
5. **Preserves** any catalog tools the partner attached in the portal (Phase 2b merge).

## Guardrails
- Never edit `retrieval.mode` to a value other than `foundry_tool` or `none`.
- Never attach a Knowledge Base by clicking in the portal — declare it here so the spec is reproducible.
- Never attach a side-effect catalog tool without a HITL story (see Step 3 callout).
- AI Search is **always** wired underneath FoundryIQ; no agent should be configured to query AI Search directly.
