# 3. Rehearse in a sandbox

*Step 3 of 10 · Get ready*

!!! info "Step at a glance"
    **🎯 Goal** — Clone the template into your own dev subscription, run the full deploy + eval loop end-to-end, feel one HITL approval — before you face a customer.

    **📋 Prerequisite** — [2. Set up your machine](02-set-up-your-machine.md) complete.

    **💻 Where you'll work** — VS Code + Azure portal (your sandbox subscription) + Foundry portal (`ai.azure.com`).

    **✅ Done when** — Sandbox app responds to `/research/stream`; quality and redteam evals pass; you've watched one App Insights trace and approved one HITL prompt.

---

This step is the **sandbox rehearsal** — done once per partner engineer, before your first customer-facing engagement. Returning engineers skip straight to *4. Clone for the customer* on subsequent engagements.

It is **not** customer training. It is partner-engineer training, with check-your-work gates so you catch misunderstandings in your own sub instead of in front of a customer.

## Lab objectives

After finishing the sandbox rehearsal you can:

1. Deploy the flagship scenario to your own sandbox subscription with `azd up` and confirm it works end-to-end.
2. Open the reference front-end locally and drive the workflow from a browser.
3. Read App Insights telemetry emitted by real browser traffic, and know which dashboard panels require partner-wired emitters to light up.
4. Run the quality and redteam evals against your deployment and read `scripts/enforce-acceptance.py` output.
5. Edit an agent's instructions the supported way (spec file + `azd provision`), not by portal drift.
6. Swap the model via `accelerator.yaml → models[]`.
7. Scaffold a new side-effect tool via `/add-tool` with HITL baked in, and know why the redteam case is not optional.
8. Scaffold a new scenario with `/scaffold-from-brief` and know what it actually does vs what you still author by hand.

## Where you'll work in the sandbox

| Where | What you do there |
|---|---|
| **VS Code** | Run repo-local commands in the integrated terminal (`` Ctrl+` ``); edit files; talk to GitHub Copilot Chat in the right sidebar (chatmodes via `/`) |
| **GitHub web** | Watch Actions runs (optional in the lab; required in real engagements) |
| **Azure portal** | Resource group, App Insights logs and dashboards, Foundry quota |
| **Foundry portal** (ai.azure.com) | Visually confirm agents (Lab 5 demonstrates that portal edits get overwritten by spec files on next `azd provision`) |

## Sandbox smoke-test (start here)

```bash
# 1. Clone the template into a sandbox repo (NOT a customer repo — that's step 4)
gh repo create <your-handle>-accel-sandbox --template Azure-Samples/agentic-ai-solution-accelerator --private --clone
cd <your-handle>-accel-sandbox
code .

# 2. Authenticate to your SANDBOX subscription
az login --tenant <your-sandbox-tenant-id>
azd auth login

# 3. Provision + deploy
azd env new sandbox-dev
azd up
```

`azd up` returns the API URL. Hit `/healthz` to confirm the scenario loaded; hit `/research/stream` with a sample payload to run the flagship end-to-end.

Cleanup when done: `azd down --purge`.

## The labs (sequential)

The 8 labs walk the same surface with check-your-work gates. They live in the existing lab guide and are referenced here in order:

- Lab 1 — Deploy + smoke-test
- Lab 2 — Open the reference frontend and drive the workflow
- Lab 3 — Read App Insights telemetry
- Lab 4 — Run quality + redteam evals
- Lab 5 — Edit an agent spec the supported way
- Lab 6 — Swap the model
- Lab 7 — Scaffold a side-effect tool with `/add-tool`
- Lab 8 — Scaffold a new scenario with `/scaffold-from-brief`

→ [Open the lab guide](../../enablement/hands-on-lab.md) (8 labs in order)

## What's intentionally **out of scope** in the sandbox

These all become real in step 7 once you have a customer:

- GitHub Environment-scoped OIDC secrets — sandbox `azd up` runs locally with `azd auth login` only.
- Multi-environment `deploy/environments.yaml` — single `sandbox-dev` env is fine here.
- Private endpoints, AVM, or ALZ overlay — Tier 1 standalone for the sandbox.
- Production HITL approver webhook — `HITL_DEV_MODE=1` auto-approves in the sandbox.

---

**Continue →** when you have a real engagement, go to [4. Clone for the customer](../deliver/01-clone-for-the-customer.md). Otherwise stop here — Track 1 (*Get ready*) is complete.
