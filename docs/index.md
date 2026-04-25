---
hide:
  - navigation
---

# Agentic AI Solution Accelerator

> **A GitHub template that Microsoft partners clone to deliver a customer-specific agentic AI solution — live in days, not months.** Full engagement motion (discovery → UAT → handover → measure) is weeks, and documented honestly below.

**Flagship scenario:** Sales Research & Personalized Outreach — a supervisor agent routes a research request across specialist workers (Account Researcher, ICP/Fit Analyst, Competitive Context, Outreach Personalizer) and returns a grounded, citeable sales brief with a CRM-ready outreach draft. **Human-in-the-loop gates every CRM write and every email send.**

**Stack:** Microsoft Agent Framework · Azure AI Foundry · Azure AI Search · Managed Identity · Key Vault · Container Apps · Application Insights · `azd` for infra.

!!! tip "New here? Start in three moves"
    1. **Pick your lane** in the role cards below — Lead, Engineer, or Ops.
    2. **Open the linked first action** for your lane and follow it top-to-bottom.
    3. **Want the full picture?** The [workflow map](partner-workflow.md) shows all 7 stages across the three lanes as a clickable swim-lane diagram.

[:material-rocket-launch: Get started](getting-started/index.md){ .md-button .md-button--primary }
[:material-book-open-page-variant: Partner playbook](partner-playbook.md){ .md-button }
[:material-map-marker-path: Full workflow map](partner-workflow.md){ .md-button }

---

## Pick your lane

<div class="role-cards" markdown>

<div class="role-card lead" markdown>
**👤 Delivery Lead**
*Owns the engagement end-to-end*

1. [Scope + discover](discovery/how-to-use.md) — canvas → workshop, or `/ingest-prd` → gap-fill
2. UAT sign-off — review acceptance evals with customer sponsor
3. [Handover meeting](handover/handover-packet-template.md) — walk packet + runbook
4. [Monthly value review](partner-playbook.md#stage-7--measure) — ROI KPIs vs hypothesis

→ [**Start here: Partner playbook**](partner-playbook.md)
</div>

<div class="role-card eng" markdown>
**🛠️ Partner Engineer**
*Builds, ships, supports*

1. [Scaffold from brief](QUICKSTART.md#step-3--scaffold-the-solution-from-the-brief) — `/scaffold-from-brief` (first time? run hands-on-lab)
2. [Provision customer Azure](getting-started/setup-and-prereqs.md) — `azd up` → Foundry · Search · KV · ACA
3. [Iterate with Copilot](QUICKSTART.md#step-4--provision--deploy-to-customers-azure) — PRs gated by lint + evals + redteam
4. UAT support — eval tuning · HITL wiring · fixes

→ [**Start here: Quickstart**](QUICKSTART.md)
</div>

<div class="role-card ops" markdown>
**🏛️ Customer Ops**
*Owns day-2 ops after handover*

1. Receive [handover packet](handover/handover-packet-template.md) — endpoint URLs · approvers · alerts · SLAs
2. [Day-2 ops](customer-runbook.md) — monitor · killswitch · eval re-run · secret rotation · model swap

→ [**Start here: Customer runbook**](customer-runbook.md)
</div>

</div>

<small>Want the full visual? See the [workflow map](partner-workflow.md) — same content, swim-lane diagram, clickable nodes.</small>

---

## Pick your lane (in depth)

=== "🧭 Delivery Lead"

    **You own:** scope, discovery workshop, SOW, UAT sign-off, handover meeting, monthly value review.

    - **Start with:** [Partner playbook](partner-playbook.md) — end-to-end 7-stage motion, SOW guidance, "what good looks like" per stage.
    - **Then run:** `/delivery-guide` in Copilot Chat for a guided pass through the motion.
    - **Also use:** [Discovery guide](discovery/how-to-use.md) · [Handover template](handover/handover-packet-template.md)
    - **Customer already gave you a PRD/BRD/spec?** Run `/ingest-prd` to pre-draft the brief, then `/discover-scenario` gap-fills. Full flow inside [how-to-use.md](discovery/how-to-use.md).

    !!! success "Done when"
        Customer sponsor signs off at UAT (Stage 5), handover packet is delivered with a named owner and date (Stage 6), and the first monthly value review is on the calendar (Stage 7).

=== "🛠️ Partner Engineer"

    **You own:** scaffold, provision, iterate, acceptance evals, UAT support, engagement handover artifacts.

    - **Start with:** [5-step quickstart](getting-started/index.md) — mechanics from clone to customer deploy.
    - **Then run:** `/scaffold-from-brief` once a solution brief exists (engineer's interactive equivalent of the lead's `/delivery-guide`).
    - **Also use:** [Setup & prereqs](getting-started/setup-and-prereqs.md) (authoritative `azd up` troubleshooting) · [Hands-on lab](enablement/hands-on-lab.md)

    !!! warning "First customer engagement? Run the hands-on-lab first"
        The [7-lab sandbox](enablement/hands-on-lab.md) rehearses every chatmode + `azd up` + PR gates against a throwaway subscription. Skipping this is the #1 cause of avoidable first-engagement incidents.

    !!! success "Done when"
        Acceptance evals (quality + redteam) pass in the customer's environment **and** handover artifacts — repo access, runbook, approver rota, killswitch drill notes — are delivered to customer ops.

=== "🏛️ Customer Ops"

    **You own:** day-2 operations after the partner hands over — monitoring, HITL approver rotation, incidents, drills, expansion intake.

    - **Primary:** Your engagement-specific handover packet (the partner delivers this at Stage 6).
    - **Fallback:** [Day-2 runbook](customer-runbook.md) — generic monitoring, killswitch, evals, model swap, secret rotation, incidents. **Partner packet wins on conflict.**

    !!! success "Done when (handover accepted)"
        Alerts route to your on-call, HITL approver rota is current, killswitch + secret-rotation drills have been run once, and you know which partner contact handles expansion requests. *Day-2 ops is steady-state, not a finish line.*

!!! note "Wearing multiple hats at a small partner?"
    The lanes above are **responsibilities, not job titles**. **Solo partner:** run the Lead lane top-to-bottom through Stage 1; drop into the Engineer lane at Stage 2 (scaffold → provision → iterate); return to the Lead lane at Stage 5 (UAT) through Stage 7. **Customer ops is always the customer's lane** — not something the partner wears.

---

## Reference material

!!! abstract "When guidance conflicts, use this precedence"
    Chatmodes in `.github/chatmodes/` (they drive the executable surface) → [Partner playbook](partner-playbook.md) (delivery motion) and [Setup & prereqs](getting-started/setup-and-prereqs.md) (mechanics) → this home page. The engagement-specific handover packet supersedes the generic [customer runbook](customer-runbook.md) for the customer ops lane.

<div class="grid cards" markdown>

-   :material-sitemap: **Patterns & compliance**

    ---

    [Reference architecture](patterns/architecture/README.md) · [WAF alignment](patterns/waf-alignment/README.md) · [Responsible AI](patterns/rai/README.md) · [Azure AI landing zone](patterns/azure-ai-landing-zone/README.md)

-   :material-application-braces: **Scenario walkthroughs**

    ---

    [Customer service actioning](references/customer-service-actioning/README.md) · [RFP response](references/rfp-response/README.md)

-   :material-wrench-cog: **Engineer deep-dives**

    ---

    [Tool catalog](foundry-tool-catalog.md) · [Agent specs](agent-specs/README.md) · [Version matrix](version-matrix.md) · [Architecture](patterns/architecture/README.md)

-   :material-github: **Repository**

    ---

    [GitHub repo](https://github.com/Azure-Samples/agentic-ai-solution-accelerator) · [Chatmodes](chatmodes/delivery-guide.chatmode.md) · [Contributing](about/CONTRIBUTING.md)

</div>
