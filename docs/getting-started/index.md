# Getting started — orientation

> **Before you start.** A 2-minute frame for what this accelerator is, what you'll ship, and which of the three Getting started docs to open next.

## What this accelerator is

A Microsoft-published **template repo** for partners delivering agentic AI solutions to customers on **Azure AI Foundry + Microsoft Agent Framework**. Partners fork it once per customer, fill in the discovery brief, and `azd up` lands a working agentic solution in the customer's Azure subscription in ~15 minutes.

The flagship scenario (Sales Research & Personalised Outreach) runs out of the box; you customise it from the `docs/discovery/solution-brief.md` the partner produces during discovery.

## Choose your path

Pick the row that matches what you're doing today. The Getting started nav lists every doc below; this section just tells you the **order** to read them in.

| You are… | Read in this order |
|---|---|
| **First-time partner engineer** (first customer engagement on this accelerator) | [Setup & prereqs](setup-and-prereqs.md) (one-time) → [Hands-on lab](../enablement/hands-on-lab.md) (sandbox rehearsal) → [Quickstart](../QUICKSTART.md) (per-customer deployment) |
| **Returning engineer / customer N+1** (Setup is done, lab is done) | [Quickstart](../QUICKSTART.md) — go straight to it |
| **Delivery lead** (you scope, run discovery, sign off UAT, run handover) | [Partner playbook](../partner-playbook.md) — full 7-stage motion |
| **Customer ops** (day-2 after handover) | The engagement-specific handover packet first; [Day-2 runbook](../customer-runbook.md) as fallback |

## How the docs fit together

```text
orientation (you are here)
    │
    ├─→ Setup & prereqs (one-time)  ──  authoritative for prereqs / secrets / troubleshooting
    │       │
    ├─→ Hands-on lab (sandbox rehearsal, before first customer)
    │       │
    ├─→ Quickstart (per-customer deployment)  ──  the canonical eight-step engineer path
    │
    └─→ Partner playbook  ───────────────────  delivery lead motion (discovery → handover → measure)
```

The Quickstart and the Partner playbook intentionally overlap: the Quickstart is the engineer's mechanics summary, the playbook is the delivery lead's full motion. When they disagree on **setup mechanics**, [Setup & prereqs](setup-and-prereqs.md) wins. When they disagree on **delivery motion**, the playbook wins.

## What you'll have shipped at the end

- A customer-specific clone of this template, deployed to the customer's Azure subscription
- A filled `docs/discovery/solution-brief.md` driving every prompt, tool, retrieval schema, HITL gate, and eval threshold
- CI gates (lint + quality evals + redteam) running on every PR; `azd deploy` shipping merged changes
- An Application Insights dashboard wired to the brief's KPI events

---

**Ready?** First-time? → [**Setup & prereqs**](setup-and-prereqs.md). Returning? → [**Quickstart**](../QUICKSTART.md).

**Need the full engagement motion first?** → [Partner playbook](../partner-playbook.md)
