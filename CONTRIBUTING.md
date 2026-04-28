# Contributing

This accelerator is a Microsoft-maintained template for partners
delivering agentic AI solutions to customers on Microsoft Agent
Framework + Microsoft Foundry. Contributions — bug reports, doc
fixes, pattern suggestions, new reference scenarios — are welcome
from partners and the broader community.

## Ways to contribute

- **File an issue** for bugs, gaps, or questions:
  [github.com/Azure-Samples/agentic-ai-solution-accelerator/issues](https://github.com/Azure-Samples/agentic-ai-solution-accelerator/issues)
- **Open a pull request** for small fixes (typos, broken links,
  clearer wording) directly against `main`.
- **Propose a new reference scenario or pattern** via issue first so
  we can align on scope before you invest in the implementation.

## Pull request basics

1. Branch from `main`.
2. Sign the Microsoft CLA if the portal indicates one is required —
   a CLA bot will comment on your first PR with a link. See
   [`.github/CLA.md`](.github/CLA.md) for the pointer doc.
3. Follow the relevant `CODEOWNERS` for required reviewers.
4. All PRs run pre-merge validators (see `.github/workflows/`) —
   lint, strict MkDocs build, link check. Keep them green.
5. Schema changes require schema-steward approval.
6. RAI-relevant changes require RAI council review.

## Change classes

- **Patch:** bug fix, doc fix — any CODEOWNER + validators pass.
- **Minor:** new T1/T2 behavior (backward-compat) — accelerator-eng approval.
- **Major / breaking:** schema break, bundle change, new T2 package — accelerator-eng leads + RAI council review for RAI-touching changes.

## Adding a reference scenario

1. Propose via issue first — describe business problem, solution shape, topology, grounding model.
2. Run `python scripts/scaffold-scenario.py <slug>` to materialize the scaffold under `src/scenarios/<slug>/`.
3. Paste the printed `scenario:` snippet into `accelerator.yaml` (replacing the existing block on a reference branch, or use a variant file for multi-scenario demos).
4. Land a README + walkthrough under `docs/references/<slug>/` describing the business case, KPIs, and how the scenario was customized.
5. Keep `evals/quality/` and `evals/redteam/` green; the lint (`scripts/accelerator-lint.py`) will enforce the manifest contract.

## Adding a pattern doc

Pattern docs go in `docs/patterns/<pillar>/`. Keep them opinionated + short. Link to reference scenarios where they demonstrate the pattern.

## Release process

Releases tag `main` when the flagship + framework + evals are green against the weekly pinned-latest CI. Release notes call out manifest changes (schema edits, new required keys) so partner forks can rebase cleanly.
