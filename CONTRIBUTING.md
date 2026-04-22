# Contributing

## Scope

This accelerator is currently **internal preview**. External contributions are not yet accepted.

Internal contributions (Microsoft + lighthouse partners under engagement) follow:

1. Branch from `main`.
2. Sign the Microsoft CLA (automated via CLA bot).
3. Follow the relevant `CODEOWNERS` for required reviewers.
4. All PRs run pre-merge validators (see `.github/workflows/`).
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
