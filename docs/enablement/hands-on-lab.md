# Hands-on lab — first deployment walkthrough

Self-paced lab for a **partner engineer** new to the agentic AI
solution accelerator. After finishing, you'll be comfortable enough
with the template to run a real customer engagement against it.

This is not training for the customer's end users — that's partner-owned,
separately. And it's not a substitute for reading `docs/getting-started/setup-and-prereqs.md`
(the authoritative prereqs + troubleshooting) or `QUICKSTART.md` (the
seven-step partner motion). The lab walks you through the same surface area
with check-your-work gates so you catch misunderstandings in a sandbox,
not in front of a customer.

---

## Objectives

After the lab you can:

1. Deploy the flagship scenario to your own sandbox subscription with
   `azd up` and confirm it works end-to-end.
2. Open the reference front-end locally and drive the workflow from a
   browser.
3. Read App Insights telemetry emitted by real browser traffic, and know
   which dashboard panels require partner-wired emitters to light up.
4. Run the quality and redteam evals against your deployment and read
   `scripts/enforce-acceptance.py` output.
5. Edit an agent's instructions the supported way (spec file + `azd
   provision`), not by portal drift.
6. Swap the model via `accelerator.yaml → models[]`.
7. Scaffold a new side-effect tool via `/add-tool` with HITL baked in,
   and know why the redteam case is not optional.
8. Scaffold a new scenario with `/scaffold-from-brief` and know what
   it actually does vs what you still author by hand.

---

## Prerequisites

1. An Azure **sandbox** subscription where you have Contributor — do
   **not** use a customer subscription for the lab. Cleanup at the
   end is `azd down --purge`.
2. Regional Foundry quota for `gpt-5-mini` on `GlobalStandard` (the
   shipped default is 30k TPM — see `infra/main.parameters.json`).
   Confirm in the Azure portal → Foundry → Quotas before starting.
3. The tools listed in the "Prerequisites" section of `docs/getting-started/setup-and-prereqs.md`
   (Azure CLI, `azd`, `gh`, Python 3.11, Docker or compatible).
4. A GitHub org/account where you can push a private template clone.
5. VS Code with GitHub Copilot Chat enabled (required for the
   chatmodes under `.github/chatmodes/`).

If any prereq is missing, fix it before continuing — this lab does
not work around a broken local environment. The troubleshooting
matrix in `docs/getting-started/setup-and-prereqs.md` ("Troubleshooting — top 5") is
the first stop when something goes wrong.

---

## Lab 1 — First deploy

**Goal:** reproduce the 15-minute path end-to-end from an unmodified
template clone.

1. Clone the template into your own private repo:

   ```bash
   # Replace <your-handle> with any short name (e.g., contoso-lab-accel becomes from <your-handle>=contoso)
   gh repo create <your-handle>-lab-accel --template Azure-Samples/agentic-ai-solution-accelerator --private
   cd <your-handle>-lab-accel
   code .
   ```

2. In VS Code, confirm Copilot Chat loads the repo's `.github/copilot-instructions.md`
   (you'll see it referenced in the chat sidebar). If it doesn't,
   Copilot is not going to enforce the partner guardrails — stop and
   fix before continuing.

3. Authenticate + provision:

   **About preflight:** the partner motion in `QUICKSTART.md` Step 4 has you run
   `/configure-landing-zone` and `/deploy-to-env` before `azd up`. The lab skips
   both: it deploys Tier 1 (`standalone`) into a sandbox where evals run locally,
   so a GitHub Environment isn't required yet. You'll meet both chatmodes during
   your first real customer deploy. Cross-reference `QUICKSTART.md` Step 4 for
   the production motion.

   ```bash
   az login
   azd auth login
   azd env new lab-dev
   azd up
   ```

   `azd up` provisions Foundry, AI Search, Key Vault, Container
   Apps, App Insights, and the user-assigned MI, then runs the
   `preprovision` (model sync) and `postprovision`
   (`foundry-bootstrap.py` + `seed-search.py`) hooks. Expect
   ~10–15 minutes.

**Check your work:**

- The final line of `azd up` prints an API URL. Hit `/healthz` —
  expect 200.
- In the Azure portal, open the resource group and confirm you have
  a Foundry AIServices account, a model deployment
  (`gpt-5-mini` by default) bound to the `accelerator-default-policy`
  content filter, an AI Search service with an `accounts` index,
  Key Vault, Container App, App Insights, and a user-assigned MI.
- If anything is missing, `docs/getting-started/setup-and-prereqs.md`
  "Troubleshooting — top 5" covers the common failure modes.

---

## Lab 2 — See it work in a browser

**Goal:** exercise the API the way a customer will — through a browser —
and confirm the streaming pipeline produces a usable briefing end-to-end.

The accelerator ships a reference frontend at
`patterns/sales-research-frontend/` — a minimal React + Vite + TypeScript
starter that consumes `POST /research/stream` directly. It is intentionally
plain: no auth, no state persistence, no UI framework. The customer's real
UX is the partner's value-add; this lab just proves the wiring.

**Steps:**

1. Grab the deployed API URL from `azd up`'s final output (or
   `azd env get-values | Select-String AZURE_CONTAINER_APP_URL`). You want
   the base URL — the pattern appends `/research/stream` itself.
2. From the repo root:

   ```bash
   cd patterns/sales-research-frontend
   cp .env.example .env
   # edit .env: VITE_API_BASE_URL=<deployed-api-url>
   npm install
   npm run dev
   ```

3. Open `http://localhost:5173`. The form is pre-filled with sensible
   defaults — click **Run research** and watch the streaming viewer light
   up with `status`, `partial`, and `final` events as the supervisor DAG
   executes. The result panel renders the aggregated briefing; toggle
   **Show raw JSON** to inspect the structured output.

**Check your work:**

- Every event in the live stream maps to one yielded dict from
  `SalesResearchWorkflow.stream` (see `src/scenarios/sales_research/workflow.py`)
  or from the underlying `SupervisorDAG` (see `src/workflow/supervisor.py`).
  If a new event type appears in the stream that the UI doesn't recognise,
  add it to the `StreamEvent` union in `src/types/research.ts` and to the
  `describe()` switch in `StreamingViewer.tsx`.
- The final panel renders fields from the supervisor's
  `transform_response` (`src/scenarios/sales_research/agents/supervisor/transform.py`).
  If you customise the briefing shape for the customer, update
  `ResearchBriefing` and `ResultPanel.tsx` together.

**Going further:** see `patterns/sales-research-frontend/README.md` for the
SWA deploy flow (`swa deploy ./dist`) and the customisation map. For a real
customer engagement, plan auth (Entra ID via easy-auth on Container Apps or
App Gateway), state persistence, and an actual HITL approval surface before
the UI is customer-facing.

---

## Lab 3 — Read the telemetry

**Goal:** correlate real browser traffic to App Insights events and understand
which dashboard panels require partner-wired emitters.

After clicking **Run research** in Lab 2, you have real traffic. Open App
Insights and trace it.

1. In App Insights → Logs, run:

   ```kql
   customEvents
   | where timestamp > ago(10m)
   | project timestamp, name, customDimensions
   | order by timestamp asc
   ```

   You should see `request.received` → `supervisor.routed` →
   one or more `worker.completed` → `retrieval.returned` →
   `response.returned`. If the request actually routed through a
   HITL-gated side-effect tool (`crm_write_contact`, `send_email`)
   you'll also see `tool.executed` + a `tool.hitl_*` event — but
   many flagship requests don't touch those tools, so don't treat
   those two events as guaranteed per request. Which `tool.hitl_*`
   variant fires depends on whether you set `HITL_APPROVER_ENDPOINT`
   (prod) or `HITL_DEV_MODE=1` (dev-only).

   If you want to drive synthetic traffic without the UI, here's the
   curl form:

   ```bash
   curl -N -X POST "$API_URL/research/stream" \
     -H "Content-Type: application/json" \
     -d '{"company_name":"Contoso","seller_intent":"Discovery call","persona":"VP of Operations"}'
   ```

2. Open `infra/dashboards/roi-kpis.json` in the repo, copy the JSON,
   then in Application Insights → Workbooks → New → Advanced editor
   paste it and save. Refresh — the "Successful responses per day"
   and "P95 request latency" panels should show data from your
   traffic. The "HITL approval rate" panel only lights up once
   you've exercised a HITL-gated tool (see the "HITL approver"
   section of `docs/customer-runbook.md`).

**Check your work:**

- Answer for yourself: why are both the "$ per call" and
  "Groundedness eval score trend" panels empty in the shipped flagship?
  (The workbook keys those panels off `cost.call` and `eval.result` custom
  events; neither is emitted by the shipped workflow — `cost.py::record_call_cost()`
  exists but isn't wired into the hot path. See `docs/customer-runbook.md`
  "What you inherited" and Section 3 (Operational dials) for the full answer.)

---

## Lab 4 — Run evals + acceptance (baseline)

**Goal:** understand the two-step eval flow.

This is your **baseline** — every mutation lab from here on ends by re-running
this same chain.

1. From the repo root:

   ```bash
   # Replace <your-api-url> with the deployed endpoint (e.g., https://my-app.azurecontainerapps.io)
   python evals/quality/run.py --api-url <your-api-url>
   python evals/redteam/run.py --api-url <your-api-url>
   python scripts/enforce-acceptance.py
   ```

2. Read the output of `enforce-acceptance.py`. It reports which
   thresholds from `accelerator.yaml.acceptance` passed or failed.
3. Lower the `quality_threshold` in `accelerator.yaml` by 0.2 and
   re-run `enforce-acceptance.py`. Notice: the quality gate now
   passes trivially. **Revert** — do not commit a loosened gate.

**Check your work:**

- Look at the `cost_per_call_usd` line in the
  `enforce-acceptance.py` output. In the flagship scenario,
  `src/accelerator_baseline/cost.py::record_call_cost()` is not
  called from the workflow — but `evals/quality/run.py` still
  records a **best-effort** `cost_usd` per case (token-pricing
  if the workflow surfaces usage, latency-based fallback
  otherwise; see `evals/quality/run.py:107-134`). That means the
  gate produces a number from day one; it's just not a true
  workflow cost until a partner wires `record_call_cost` into the
  hot path.
- `src/accelerator_baseline/evals.py:66-75` is the branch that
  *does* fail hard — only if the runner is modified to omit
  `cost_usd` entirely. That's the "inert-is-a-failure" safety net.
- `docs/customer-runbook.md` Section 3 and Section 4 describe what a partner has
  to wire for the cost gate to reflect real model spend, not a
  latency proxy.

---

## Lab 5 — Edit an agent's instructions the supported way

**Goal:** understand that the Foundry portal is not the source of
truth.

1. Open `docs/agent-specs/accel-sales-research-supervisor.md` (or
   whichever agent you want to tweak). This is the **repo-side
   source of truth** for the agent's instructions.
2. Make a small edit — change a guideline, add a sentence, whatever.
   Save.
3. Run `azd provision`. The postprovision hook
   `scripts/foundry-bootstrap.py` updates the agent in Foundry with
   the new instructions.
4. Now open the Foundry portal, find the same agent, and **manually
   edit** the instructions there. Save.
5. Run `azd provision` again.

**Check your work:**

- Re-open the agent in the portal. Your manual edit is **gone** —
  overwritten by the spec file. This is the designed behavior:
  portal edits are transient. The supported rollback path for a
  bad prompt is `git revert` the spec + `azd provision`, not
  "restore from Foundry portal history".
- `docs/customer-runbook.md` Section 6 (Model swap) is the condensed version of this
  behavior for the customer's ops team.

**Now re-run acceptance:**

```bash
python evals/quality/run.py --api-url <your-api-url>
python evals/redteam/run.py --api-url <your-api-url>
python scripts/enforce-acceptance.py
```

Compare to your Lab 4 baseline. A prompt edit can move quality scores in either
direction; if a threshold drops below `accelerator.yaml.acceptance`, revert and
try again. The acceptance gate is the contract.

---

## Lab 6 — Swap the model

**Goal:** do a model swap the supported way.

1. Open `accelerator.yaml` and replace the `default: true` entry
   under `models:` with a different model your sandbox has quota
   for (e.g. `gpt-4.1-mini` instead of `gpt-5-mini`, with a valid
   `version` and a `capacity` within your quota).
2. Run `azd provision`. The preprovision hook
   `scripts/sync-models-from-manifest.py` rewrites the managed azd
   env vars from the new manifest; Bicep re-deploys the Foundry
   model deployment in place; postprovision re-verifies.
3. Re-run the eval chain from Lab 4:

   ```bash
   python evals/quality/run.py --api-url <your-api-url>
   python evals/redteam/run.py --api-url <your-api-url>
   python scripts/enforce-acceptance.py
   ```

   Quality may shift — that's the point. If a threshold drops, the model
   isn't a drop-in replacement.

**Check your work:**

- Try `azd env set AZURE_AI_FOUNDRY_MODEL_NAME=some-other-model`
  and run `azd provision`. Notice: the preprovision sync clobbers
  your override back to what `accelerator.yaml → models[]` says.
  Raw env-var overrides are unsupported; manifest is the source of
  truth.

---

## Lab 7 — Add a side-effect tool with `/add-tool`

**Goal:** experience the scaffolded-with-HITL contract.

1. In Copilot Chat, invoke `/add-tool`. The chatmode (see
   `.github/chatmodes/add-tool.chatmode.md`) asks for seven inputs:
   tool name, external system, operation, reversibility, HITL
   policy, which worker uses it, and auth approach.
2. Pick something plausible — e.g. create a ticket in a ticketing
   system, irreversible, `HITL_POLICY = "always"`, attached to an
   existing worker agent, Managed Identity auth.
3. Copilot generates `src/tools/<tool_name>.py` with HITL
   scaffolding and nudges you to register it on the appropriate
   worker, add a unit test, and add a redteam case under
   `evals/redteam/`. Confirm the worker registration actually
   landed — the chatmode instructs it but partners have to verify.
4. Run `python scripts/accelerator-lint.py` — it must report
   `0 blocking, 0 warning findings`.
5. Run `pytest -q` — the new test must pass.

### Author + run the redteam case

The `/add-tool` chatmode tells you to add a redteam case for the new tool — that's
the contract. Before calling the lab done, do both halves:

1. Add a case to `evals/redteam/cases.jsonl` exercising prompt-injection or
   jailbreak attempts to misuse the tool.
2. Run it:

   ```bash
   python evals/redteam/run.py --api-url <your-api-url>
   ```

Confirm your new case appears in the output and the safety bar in
`accelerator.yaml.acceptance.safety_pass` still holds.

### Now re-run acceptance

```bash
python evals/quality/run.py --api-url <your-api-url>
python evals/redteam/run.py --api-url <your-api-url>
python scripts/enforce-acceptance.py
```

The redteam re-run picks up your new case; quality + acceptance ensure the tool
didn't regress the scenario.

**Check your work:**

- Remove the `checkpoint(...)` call from the tool and re-run lint.
  On any `src/tools/*.py` file that declares `HITL_POLICY`, the
  `hitl-required` rule fails loudly. Put `checkpoint(...)` back
  before continuing.
- Confirm the redteam case you authored above appears in `evals/redteam/run.py`'s
  output. The `safety_pass` threshold in `accelerator.yaml.acceptance` will
  block merge if any redteam case fails — including the one you just added.

---

## Lab 8 — Scaffold a new scenario

**Goal:** understand what `/scaffold-from-brief` actually generates
vs what you still author.

1. In Copilot Chat, run `/discover-scenario` against a realistic
   sandbox scenario you make up (e.g. "summarize support tickets
   weekly"). Answer the questions. The chatmode writes
   `docs/discovery/solution-brief.md` and updates
   `accelerator.yaml` `solution.*`, `acceptance.*`, and `kpis[]`
   from your answers — it does **not** touch the `scenario:`
   block (that comes next).
2. Run `python scripts/scaffold-scenario.py ticket-summary --display "Ticket Summary"`.
   Inspect what it generated under `src/scenarios/ticket_summary/`:
   `schema.py`, `workflow.py`, `retrieval.py`, and a single
   supervisor agent package (`agents/supervisor/{prompt,transform,validate}.py`)
   plus one supervisor spec stub at
   `docs/agent-specs/accel-ticket-summary-supervisor.md`. The
   script also prints a `scenario:` YAML block to stdout for you
   to paste into `accelerator.yaml`.
3. Paste the printed `scenario:` block over the existing
   `scenario:` block in `accelerator.yaml`.
4. Run `python scripts/accelerator-lint.py`. In a fresh scaffold,
   most lint rules will pass because the generated files are
   syntactically valid and the supervisor spec ships with a
   generic baseline. But the `prompt.py`, `transform.py`,
   `validate.py`, and `retrieval.py` are minimal placeholders —
   read them, then build them out: tighten the supervisor
   spec for your domain, add worker agents with
   `scripts/scaffold-agent.py`, author retrieval schema, and
   author golden + redteam cases before deploying to a customer.

**Check your work:**

- Open the generated prompt / transform / validate stubs under
  `src/scenarios/ticket_summary/agents/supervisor/`. They're
  deliberate placeholders. The supervisor spec ships with generic
  baseline instructions that run as-is but aren't domain-aware —
  tighten those instructions for your scenario. Don't ship to a
  customer until real behavior is authored, the supervisor spec
  reflects your domain, golden + redteam cases exist, and lint
  reports `0 blocking, 0 warning findings`.
- `/scaffold-from-brief` drives all of the above in one chatmode
  invocation; the CLI `scripts/scaffold-scenario.py` is the
  underlying mechanic `scaffold-from-brief` calls into. Knowing
  the difference matters when something goes wrong mid-chatmode
  and you have to finish by hand.

---

## Cleanup

```bash
azd down --purge
```

This tears down every resource in the lab environment. Do this
before closing the lab — a lingering Foundry deployment consumes
quota you might need for the next run.

---

## Where to go next

- Deploy the UI from Lab 2 to Azure Static Web Apps with `swa deploy ./dist`
  (`patterns/sales-research-frontend/README.md` has the full flow including
  `VITE_API_BASE_URL` for build-time API binding).
- Run the actual partner motion (`QUICKSTART.md` + `docs/partner-playbook.md`)
  against a scoped sandbox engagement — not a real customer — before
  taking the accelerator to a paying engagement.
- Read `docs/patterns/azure-ai-landing-zone/README.md` and run
  `/configure-landing-zone` against a Tier 2 `avm` overlay in your
  sandbox. Tier 3 `alz-integrated` requires a hub to peer to; if you
  don't have one, stop at Tier 2.
- Discovery artifacts live under `docs/discovery/` — five
  engagement artifacts (`use-case-canvas.md`,
  `SOLUTION-BRIEF-GUIDE.md`, `discovery-workbook.csv`,
  `solution-brief.md`, `roi-calculator.xlsx`) plus
  `how-to-use.md` as the sequencing meta-guide. Run
  `/discover-scenario` when you're ready to turn workshop notes
  into a filled brief.
- Contribution flow for external partners is documented at
  [`.github/CLA.md`](../../.github/CLA.md) — short version: on your
  first PR, a CLA bot comments with a link to
  <https://cla.opensource.microsoft.com>; sign once there and the
  `license/cla` status check turns green. Rely on the status check
  and the portal for the specific repo you're contributing to
  rather than assuming broad coverage. Partner private forks
  (outside the `microsoft`/`Azure` orgs) are outside Microsoft's
  CLA flow entirely; the bot only fires on upstream PRs.

---

## What this lab is not

- Customer training — partner-owned, separately
- A substitute for reading `docs/getting-started/setup-and-prereqs.md` and `QUICKSTART.md`
- Certification — there's no badge or quiz; the check-your-work
  gates exist so you notice your own gaps, not to score you
- A Tier 2 / Tier 3 networking lab — that's `/configure-landing-zone`
  territory and requires infrastructure beyond a dev sandbox