# Getting started — orientation

> **Before you start.** A 2-minute frame for what this accelerator is, what you'll ship, and where to go next. The mechanics live in the [Quickstart](../QUICKSTART.md); this page just gets you pointed in the right direction.

## What this accelerator is

A Microsoft-published **template repo** for partners delivering agentic AI solutions to customers on **Azure AI Foundry + Microsoft Agent Framework**. Partners fork it once per customer, fill in the discovery brief, and `azd up` lands a working agentic solution in the customer's Azure subscription in ~15 minutes.

The flagship scenario (Sales Research & Personalised Outreach) runs out of the box; you customise it from the `docs/discovery/solution-brief.md` the partner produces during discovery.

## Pick your lane

One signpost — pick the lane that matches what you're doing today. You can come back here when your role on the engagement changes.

- **Leading the engagement?** → [**Partner playbook**](../partner-playbook.md) — the full motion (discovery → scaffold → provision → iterate → UAT → handover → measure).
- **Building inside the repo?** → [**Quickstart**](../QUICKSTART.md) — 5 steps to a running scaffold in the customer's Azure.
- **Running an enablement workshop?** → [**Hands-on lab**](../enablement/hands-on-lab.md) — guided check-your-work walkthrough in your own subscription.
- **First time on Azure / Foundry, or hitting a setup error?** → [**Setup & prereqs**](setup-and-prereqs.md) — authoritative reference for prereqs, secrets, `azd` invocation, and troubleshooting.

## How the docs fit together

```text
orientation (you are here)
    │
    ├─→ Quickstart  ─────────  the canonical seven-step engineer path
    │       │
    │       └─→ Setup & prereqs  ──  authoritative for prereqs / secrets / troubleshooting
    │
    ├─→ Partner playbook  ────  delivery lead motion (discovery → handover → measure)
    │
    └─→ Hands-on lab  ────────  sandbox rehearsal before first customer
```

The Quickstart and the Partner playbook intentionally overlap: the Quickstart is the engineer's mechanics summary, the playbook is the delivery lead's full motion. When they disagree on **setup mechanics**, [Setup & prereqs](setup-and-prereqs.md) wins. When they disagree on **delivery motion**, the playbook wins.

## What you'll have shipped at the end

- A customer-specific clone of this template, deployed to the customer's Azure subscription
- A filled `docs/discovery/solution-brief.md` driving every prompt, tool, retrieval schema, HITL gate, and eval threshold
- CI gates (lint + quality evals + redteam) running on every PR; `azd deploy` shipping merged changes
- An Application Insights dashboard wired to the brief's KPI events

---

**Ready?** → [**Proceed to Quickstart**](../QUICKSTART.md)

**Need the full engagement motion first?** → [Partner playbook](../partner-playbook.md)
