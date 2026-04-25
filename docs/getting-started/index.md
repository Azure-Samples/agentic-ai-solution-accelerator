# Getting started — orientation

> **Before you start.** A 2-minute frame for what this accelerator is, what you'll ship, and where to go next. The mechanics live in the [Quickstart](../QUICKSTART.md); this page just gets you pointed in the right direction.

## What this accelerator is

A Microsoft-published **template repo** for partners delivering agentic AI solutions to customers on **Azure AI Foundry + Microsoft Agent Framework**. Partners fork it once per customer, fill in the discovery brief, and `azd up` lands a working agentic solution in the customer's Azure subscription in ~15 minutes.

The flagship scenario (Sales Research & Personalised Outreach) runs out of the box; you customise it from the `docs/discovery/solution-brief.md` the partner produces during discovery.

## Who's reading this

| If you are… | Start here |
|---|---|
| **Partner engineer** scaffolding a new customer engagement | [5-step Quickstart](../QUICKSTART.md) — clone → discover → scaffold → `azd up` → iterate |
| **Delivery lead / TPM** scoping or running discovery | [Partner playbook](../partner-playbook.md) — the full 7-stage motion, with discovery upstream of the engineer's work |
| **First-timer** wanting a sandbox rehearsal before a customer | [Hands-on lab](../enablement/hands-on-lab.md) — guided check-your-work walkthrough in your own subscription |
| **Engineer hitting a setup error** (`azd`, prereqs, secrets) | [Setup & prereqs](../getting-started.md) — authoritative reference; wins over every other doc on setup mechanics |

## How the docs fit together

```text
orientation (you are here)
    │
    ├─→ Quickstart  ─────────  the canonical 5-step engineer path
    │       │
    │       └─→ Setup & prereqs  ──  authoritative for prereqs / secrets / troubleshooting
    │
    ├─→ Partner playbook  ────  delivery lead motion (discovery → handover → measure)
    │
    └─→ Hands-on lab  ────────  sandbox rehearsal before first customer
```

The Quickstart and the Partner playbook intentionally overlap: the Quickstart is the engineer's mechanics summary, the playbook is the delivery lead's full motion. When they disagree on **setup mechanics**, [Setup & prereqs](../getting-started.md) wins. When they disagree on **delivery motion**, the playbook wins.

## What you'll have shipped at the end

- A customer-specific clone of this template, deployed to the customer's Azure subscription
- A filled `docs/discovery/solution-brief.md` driving every prompt, tool, retrieval schema, HITL gate, and eval threshold
- CI gates (lint + quality evals + redteam) running on every PR; `azd deploy` shipping merged changes
- An Application Insights dashboard wired to the brief's KPI events

---

**Ready?** → [**Go to the 5-step Quickstart**](../QUICKSTART.md)

**Need the full engagement motion first?** → [Partner playbook](../partner-playbook.md)
