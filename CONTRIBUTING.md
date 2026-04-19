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

1. Propose via issue first — describe business problem, bundle, topology, grounding model.
2. Land a README under `examples/scenarios/<slug>/`.
3. Add a corresponding Spec example under `examples/specs/`.
4. Full runnable code lands in Phase D for curated scenarios.

## Adding a pattern doc

Pattern docs go in `content/patterns/<pillar>/`. Keep them opinionated + short. Link to reference scenarios where they demonstrate the pattern.

## Release process

Releases produce signed artifacts on the private feed. See release notes per version for upgrade guidance.
