# Discovery artifacts — how they fit together

Five artifacts ship under `docs/discovery/` for the pre-sales through
kickoff arc of a partner engagement. Each serves one job. Use them in
this order; skipping steps is how engagements end up with a brief that
reads well but doesn't tie to measurable ROI.

## The five artifacts

| # | Artifact | Purpose | Who fills it |
|---|---|---|---|
| 1 | `use-case-canvas.md` | 1-page exec alignment before you spend workshop time | Partner lead + customer sponsor, async |
| 2 | `SOLUTION-BRIEF-GUIDE.md` | How to run the discovery workshop that fills the brief | Read by partner lead; optional coaching for junior facilitators |
| 3 | `discovery-workbook.csv` | Structured capture during the live workshop | Partner facilitator (typing) + customer SMEs (answering) |
| 4 | `solution-brief.md` | Canonical engagement doc — every downstream artifact derives from it | Output of `/discover-scenario` Copilot chatmode (or manually from workbook) |
| 5 | `roi-calculator.xlsx` | Quantifies the hypothesis in §4 of the brief | Partner lead, after §3 of the brief is filled |

## When to use which

### Before the workshop

1. **Use-case canvas** — send to the customer sponsor after the first
   scoping call. If the sponsor can't fill it in ~30 minutes, the
   engagement isn't ready for a workshop. The canvas is a go/no-go
   gate, not a deliverable.

### During the workshop

2. **Discovery workbook** — the facilitator types answers into the CSV
   live. One question per row keeps the conversation disciplined. The
   workbook is *scaffolding*; it gets replaced by the solution brief
   after the session.

### Immediately after

3. **Solution brief** — run `/discover-scenario` in Copilot Chat with
   the filled workbook as context (paste it, or point Copilot at the
   file). The chatmode produces the 7-section brief at
   `docs/discovery/solution-brief.md` **and** updates
   `accelerator.yaml` fields (`solution.*`, `acceptance.*`, `kpis[]`).
   It does **not** touch `scenario:` — that comes from
   `/scaffold-from-brief` + `scripts/scaffold-scenario.py` in the
   scaffold stage.

4. **ROI calculator** — open `roi-calculator.xlsx`, fill blue cells on
   the `Inputs` sheet with numbers from brief §3 + §4. Read the `ROI`
   sheet for annual savings and payback; read the `KPIs` sheet for
   rendered baseline/target values and a copy guide that mirrors the
   `accelerator.yaml:kpis` schema. The block is a copy guide, not
   paste-ready — Excel does not expand cell addresses into text when
   copied.

### Before scaffolding

5. Walk the sponsor through the brief + ROI calculator together. If
   either has TBD fields or the ROI doesn't clear the customer's
   hurdle rate, iterate before running `/scaffold-from-brief`. A
   scaffold is expensive to redo; a discovery redo is cheap.

## What ships in the repo vs what's engagement-specific

**Ships in the repo (template):**
- Every file in `docs/discovery/` is a **template** partners fork per
  engagement. `solution-brief.md` and `roi-calculator.xlsx` ship
  unfilled.
- The files ship with the flagship (sales-research) scenario's
  defaults as sample values where useful, but treat those as
  placeholders.

**Engagement-specific (partner fills):**
- Customer name, sponsor, numbers, KPIs, thresholds.
- At handover, archive the filled copies with the customer engagement
  (your delivery workspace, not this template repo).

## Honesty notes

- The canvas and workbook are discovery *capture*; they don't replace
  the solution brief. If you stop at the workbook, downstream
  automation (lint, scaffold, evals) won't have the structure it
  expects.
- The ROI calculator is a hypothesis tool at discovery. Real numbers
  come from running the accelerator against the customer's data
  during iteration + UAT (partner playbook stages 4–5). Expect to
  reconcile against measured performance before production sign-off.
- `duration_ms` and `ratio` are the only KPI types wired into
  `src/accelerator_baseline/telemetry.py` today. Other types are
  partner-authored.
- The workbook .csv is plain text specifically so it diffs cleanly in
  PRs and Copilot can read it. If the customer prefers a "real"
  workshop template (.xlsx, OneNote, etc.), fork locally — don't
  bloat the template repo.

## Related

- `docs/partner-playbook.md` stage 1 drives the partner motion across
  these artifacts end-to-end.
- `docs/enablement/hands-on-lab.md` is the sandbox rehearsal; Lab 7
  walks a partner engineer through `/discover-scenario` +
  `scaffold-scenario.py`.
- `.github/chatmodes/discover-scenario.chatmode.md` is the chatmode
  that produces the solution brief from workshop notes or live.
