# 5-step quickstart

> Partner's path from "new customer meeting" to "working agent in customer Azure." ~15 minutes of compute, a few hours of your time.

!!! info "Who this is for"
    **Partner engineers** (or the engineering hat of a solo partner) running their first or Nth customer engagement. If you're scoping the work or running discovery, start with the [Partner playbook](../partner-playbook.md) first — the brief that drives Step 3 comes from there.

!!! warning "First time on this accelerator?"
    Run the [hands-on-lab](../enablement/hands-on-lab.md) in a **sandbox subscription** end-to-end before your first customer-facing deployment. The happy path below assumes you've done the lab once.

!!! tip "Engineer joining mid-engagement?"
    If `docs/discovery/solution-brief.md` already exists in the repo, Steps 1–2 are done — jump to [Step 3 →](#step-3--scaffold-the-solution-from-the-brief).

---

## Step 1 — Clone the template

Create the customer's repo from the template. VS Code opens with Copilot already wired to `.github/copilot-instructions.md` — it knows the hard rules (Agent Framework + Foundry only, DefaultAzureCredential only, HITL required for side effects).

```bash
gh repo create <customer>-agents --template Azure/agentic-ai-solution-accelerator --private
cd <customer>-agents
code .
```

!!! success "Done when"
    Repo is cloned locally, VS Code is open, and Copilot Chat responds (try `/delivery-guide` — it should greet you).

**Next →** [Step 2 — Run discovery](#step-2--run-the-discovery-workshop)

---

## Step 2 — Run the discovery workshop

!!! note "Delivery lead task"
    This step is typically driven by the **delivery lead**. If that's a different person, hand the repo over; they'll produce `docs/discovery/solution-brief.md`, then pass it back to you at Step 3.

In Copilot Chat:

```text
/discover-scenario
```

Copilot interviews you (in-room or after a workshop) and writes `docs/discovery/solution-brief.md`. The brief captures business context, users, **ROI hypothesis**, solution shape, constraints, and acceptance evals. It is the **single source of truth** for the engagement — every downstream artifact derives from it.

!!! tip "Customer already provided a PRD / BRD / functional spec?"
    Run `/ingest-prd` **before** `/discover-scenario` to pre-draft the brief from the source doc. Full branch documented in [`discovery/how-to-use.md`](../discovery/how-to-use.md).

!!! success "Done when"
    `docs/discovery/solution-brief.md` exists, is filled in (no TBDs), and the customer sponsor has eyes on the ROI hypothesis.

**Next →** [Step 3 — Scaffold](#step-3--scaffold-the-solution-from-the-brief)

---

## Step 3 — Scaffold the solution from the brief

```text
/scaffold-from-brief
```

Copilot reads the brief and customizes the repo. Prompts, tools, retrieval schema, HITL gates, evals, manifest — all generated per the brief's fields. See the [Step 3 field-mapping table](../QUICKSTART.md#step-3--scaffold-the-solution-from-the-brief) for what lands where.

!!! info "Different business scenario?"
    Flagship `sales-research` lives under `src/scenarios/sales_research/`. For a different scenario, run `python scripts/scaffold-scenario.py <your-id>` to create `src/scenarios/<your-id>/` — everything outside `src/scenarios/` is scenario-agnostic and stays put.

!!! success "Done when"
    Scaffolded changes are committed, `scripts/accelerator-lint.py` passes locally, and the scenario manifest at `accelerator.yaml` reflects the brief.

**Next →** [Step 4 — Provision + deploy](#step-4--provision--deploy-to-customers-azure)

---

## Step 4 — Provision + deploy to customer's Azure

```bash
az login --tenant <customer-tenant-id>
azd auth login
azd env new <customer>-dev
azd up
```

`azd up` provisions Azure AI Foundry · Azure AI Search · Key Vault · Container Apps · App Insights · Managed Identity. **No keys.** Content filters via IaC. Dashboards pre-wired to the brief's KPI events.

!!! warning "Prereqs, secrets, troubleshooting"
    Full authoritative setup is in [`getting-started.md`](../getting-started.md). If `azd up` fails, that doc wins over anything else.

!!! success "Done when"
    Deployed endpoint URL prints at the end of `azd up`, you can hit it and get a response, and Application Insights is receiving telemetry.

**Next →** [Step 5 — Iterate through CI gates](#step-5--iterate-with-copilot-ship-through-ci-gates)

---

## Step 5 — Iterate with Copilot; ship through CI gates

In VS Code, just talk to Copilot:

> *"Add a tool to create a ticket in ServiceNow; it should require HITL for anything with priority high."*

Copilot follows `copilot-instructions.md` — creates the tool module with HITL scaffolding, wires it, adds a unit test.

```bash
git checkout -b feat/servicenow-tool
git add -A && git commit -m "Add ServiceNow tool"
gh pr create
```

The PR triggers four gates:

1. `scripts/accelerator-lint.py` — 30 deterministic rules
2. `evals/quality/` — must clear thresholds in `accelerator.yaml -> acceptance`
3. `evals/redteam/` — XPIA + jailbreak must pass
4. Build + type check

Any red light blocks merge. Green = `azd deploy` against the customer env.

!!! success "Done when"
    PR is green across all four gates, it's merged to `main`, and `azd deploy` has pushed the change to the customer environment.

---

## What's next after the 5 steps?

<div class="grid cards" markdown>

-   :material-map-marker-path: **Full engagement motion**

    ---

    The 5 steps above are the engineer's mechanics path. The full engagement (scope → UAT → handover → monthly review) is the delivery lead's 7-stage motion.

    [→ Partner playbook](../partner-playbook.md)

-   :material-beaker: **Need a different shape?**

    ---

    Candidate patterns under `patterns/` re-author the scenario under a different agent topology. Run `/switch-to-variant` for a walkthrough.

    [→ Patterns](../patterns/architecture/README.md)

-   :material-shield-check: **Heading to UAT**

    ---

    Acceptance evals (quality + redteam) must pass in the customer env, and you're on-call for fixes while the sponsor walks the evals.

    [→ Stage 5 — UAT](../partner-playbook.md#stage-5--uat)

-   :material-handshake: **Preparing for handover**

    ---

    The handover packet is engagement-specific. Fill the template with your customer's endpoint URLs, approver rota, killswitch drill notes, and alerts routing.

    [→ Handover template](../handover/handover-packet-template.md)

</div>

!!! question "Stuck?"
    Check the authoritative [setup & troubleshooting guide](../getting-started.md), open an issue on the [GitHub repo](https://github.com/arush-saxena/agentic-ai-solution-accelerator), or fall back to the canonical [`QUICKSTART.md`](../QUICKSTART.md) which has the same 5 steps in reference form.
