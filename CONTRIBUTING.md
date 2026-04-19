# Contributing

## Scope

This accelerator is currently private-preview. External contributions are not accepted in v1.

Internal contributions (Microsoft + lighthouse partners under engagement) follow:

1. Fork or branch from `main`
2. Sign the Microsoft CLA (automated via CLA bot)
3. Follow the relevant `CODEOWNERS` for required reviewers
4. All PRs run pre-merge validators (see `.github/workflows/`)
5. Schema changes require schema-steward approval
6. RAI-relevant changes require RAI council approval
7. Governance docs require governance board approval

## Change classes

- **Patch:** bug fix, doc fix — any CODEOWNER + validators pass
- **Minor:** new T1/T2 behavior (backward-compat) — accelerator-eng approval
- **Major / breaking:** schema break, bundle change, new T2 — governance board approval (see `docs/governance/governance-board-charter.md`)

## Release process

See `compatibility/upgrade-transaction-model.md`. Follow the expand-contract migration policy for any schema or data change.
