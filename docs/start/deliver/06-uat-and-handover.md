# 9. UAT & handover

> **Goal.** Run customer UAT to acceptance, deliver the handover packet to customer ops.
>
> **Prerequisite.** [8. Iterate & evaluate](05-iterate-and-evaluate.md) complete — quality + redteam evals green; KPI events emitting; dashboards populated.
>
> **Where you'll work.** Customer environment (UAT pass) + handover meeting (live or recorded) + your delivery workspace (where the filled handover packet lands).
>
> **Done when.** Acceptance criteria signed by customer sponsor; handover packet (alerts, dashboards, runbook, eval gates, rollback plan) delivered; customer ops named.

---

## UAT — what "acceptance" means here

Acceptance is **objective + signed**, not "the demo went well."

- **Objective:** every threshold in `accelerator.yaml -> acceptance` is green on the customer environment, against the customer's golden cases (`evals/quality/golden_cases.jsonl`) and the customer-specific redteam cases (`evals/redteam/`).
- **Signed:** the customer sponsor named in `solution-brief.md` Section 1 signs off the acceptance report (the output of `python scripts/enforce-acceptance.py` against the customer environment, captured at the UAT cut-off).

If a threshold misses, **don't ship** — loop back to [8. Iterate & evaluate](05-iterate-and-evaluate.md) and fix in PRs against the customer environment, with the regression suite guarding the merge.

## Handover packet

Use the [handover packet template](../../handover/handover-packet-template.md) as the starting structure. Fill it per engagement and deliver it to the customer team that will own day-2 ops (often a different team from the workshop sponsors).

Minimum contents:

- **Endpoint inventory** — API URL, frontend URL (if any), Foundry project name, resource group name.
- **Approvers** — who is on-call for HITL approvals; backup; escalation.
- **Dashboards** — App Insights workbook URL, KPI panels, latency panels, error panels.
- **Alerts** — what fires, to whom, on what threshold; how to acknowledge.
- **SLAs** — uptime, response time, eval thresholds; what "broken" means and who decides.
- **Eval gates** — `accelerator.yaml -> acceptance` thresholds; how to re-run; how to interpret.
- **Rollback** — how to roll back a bad deploy (`azd deploy` against a tagged commit); how to flip the killswitch (`KILLSWITCH=1` env var).
- **Secret rotation** — schedule and procedure for `AZURE_CLIENT_ID` federated cred rotation, `HITL_APPROVER_ENDPOINT` rotation if the approver moves.
- **Model swap** — how to point an agent at a different model via `accelerator.yaml -> models[]` and re-run `azd up`.

The accelerator-default precedence: the **engagement-specific handover packet supersedes the generic [Operate (Day 2)](07-operate-day-2.md) page** for the customer ops lane. The generic page is a fallback; the packet is canonical for this engagement.

## Handover meeting

Walk the customer ops team through the packet **live**:

- Open the App Insights dashboard. Drive a single end-to-end request. Show the trace.
- Approve a HITL prompt together — show what the approver sees and what gets logged.
- Run the regression eval suite (`python evals/quality/run.py --api-url <customer-api-url>`) and walk the output.
- Hand them the killswitch demonstration (do not actually flip it in prod — show it in a non-prod env).
- Confirm they have access to: the customer GitHub repo (read at minimum), the App Insights workspace, the resource group, the Foundry project.

Record the meeting; archive with the packet in your delivery workspace.

## Archive

In your delivery workspace (not this template repo):

- The filled `solution-brief.md` and `roi-calculator.xlsx`.
- The signed acceptance report.
- The filled handover packet.
- The handover meeting recording.
- A pointer to the customer GitHub repo + customer Azure environments.

---

**Continue →** [10. Operate (Day 2)](07-operate-day-2.md)
