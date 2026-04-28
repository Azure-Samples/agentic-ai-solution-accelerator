# 1. Get oriented

> **Goal.** Understand what the accelerator is, the supervisor + workers shape, and what's accelerator vs. partner-owned.
>
> **Prerequisite.** None — you just landed on this site.
>
> **Where you'll work.** Browser (this site).
>
> **Done when.** You can name (a) what the accelerator gives you vs. what you still own, and (b) which steps are one-time vs. per-customer.

---

## What the accelerator is

A Microsoft-published **GitHub template repo** that partners clone — once per customer — to deliver an agentic AI solution into the customer's Azure subscription. It ships a working flagship scenario (Sales Research & Personalised Outreach), a full discovery → handover → measure motion, and the CI gates, evals, telemetry, and HITL plumbing a regulated production workload needs.

The platform is **Microsoft Agent Framework + Azure AI Foundry** — no other orchestration SDKs. Identity is **Managed Identity + Entra everywhere** — no keys, no connection strings.

## The shape: supervisor + workers

The flagship is one supervisor agent that routes a customer request across specialist workers and aggregates their outputs.

```text
                ┌────────────────────────┐
   request ───► │       Supervisor       │ ◄── routes by intent
                └─────────┬──────────────┘
                          │ delegates to
        ┌─────────────────┼─────────────────────┐
        ▼                 ▼                     ▼
 Account Researcher   ICP / Fit Analyst   Outreach Personaliser
 (and more — every worker is stateless, declared in
  WORKERS in src/scenarios/<id>/workflow.py)
```

Two simpler shapes are also supported via `/switch-to-variant`:
**single-agent** (no supervisor) and **chat-with-actioning** (conversational front-end).

## What the accelerator gives you vs. what you own

| The accelerator ships | You still own |
|---|---|
| Discovery chatmode, brief template, ROI calculator | Customer workshop facilitation |
| Scaffolders for new scenarios, agents, tools | Scenario-specific prompts, retrieval schema |
| Bicep infra (AVM-based) + `azd up` | Customer network / private-link overlay (if regulated) |
| CI gates: lint + quality evals + redteam | Branch protection, required reviewers |
| Telemetry baseline + dashboard schema | Customer dashboards, alerting thresholds |
| HITL contract (constant + checkpoint + lint + dev-mode stub) | The production approver (Logic Apps, Teams, ServiceNow) |
| Reference frontend starter | Real customer UX, branding, end-user auth, run-history persistence |
| **Nothing** — the SOW, customer training material | **You** — your partner practice owns those |

The full ownership boundary lives in [Delivery context → Partner playbook](../../partner-playbook.md#what-the-accelerator-gives-you-vs-what-you-still-own). Call it out explicitly in the SOW.

## One-time vs. per-customer

| Step | When |
|---|---|
| 1. Get oriented (here) | Once |
| 2. Set up your machine | Once per partner machine |
| 3. Rehearse in a sandbox | Once per partner engineer, before first customer |
| 4. Clone for the customer | Per engagement |
| 5. Discover with the customer | Per engagement |
| 6. Scaffold from the brief | Per engagement |
| 7. Provision the customer's Azure | Per engagement |
| 8. Iterate & evaluate | Per engagement (continuous) |
| 9. UAT & handover | Per engagement |
| 10. Operate (Day 2) | Per engagement (ongoing) |

## When pages disagree, this is the precedence

This is the canonical precedence rule for the whole site — other pages link here rather than restate it.

1. **Chatmodes** in `.github/chatmodes/` win on the executable surface they drive — they are the runtime contract.
2. **[2. Set up your machine](02-set-up-your-machine.md)** wins on setup mechanics — prereqs, secrets, `azd` invocation, troubleshooting.
3. **[Partner playbook](../../partner-playbook.md)** (under Reference → Delivery context) wins on partner-motion intent — *why* the seven delivery steps are shaped this way.
4. The **delivery walkthrough** (steps 4–10) is the executable summary of the playbook; if it disagrees with the playbook on motion or with *Set up your machine* on mechanics, those win.
5. The engagement-specific **handover packet** supersedes the generic [Operate (Day 2)](../deliver/07-operate-day-2.md) page once the customer has one.

---

**Continue →** [2. Set up your machine](02-set-up-your-machine.md)
