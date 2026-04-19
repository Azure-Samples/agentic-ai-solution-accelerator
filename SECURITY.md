# Security Policy

## Reporting

Report security issues to Microsoft Security Response Center (MSRC):
https://msrc.microsoft.com/create-report

Do **NOT** file public issues on this repo for security vulnerabilities.

## Scope of accepted reports

- T1 core package (`azure-agentic-baseline`)
- T2 profile-required packages (`baseline-drift`, `baseline-feedback`, `baseline-hitl`, `baseline-actions`)
- `baseline-cli`
- Shipped Bicep modules + azd templates for blessed bundles
- Schema files + validator
- Copilot instructions + chat modes (for prompt-injection-enabling issues)

**Out of scope:**
- Partner-authored business logic in customer repos
- T3 reference (`baseline-cache`, `examples/`)
- Customer's own Azure subscription policies or landing zone
- Bugs in Foundry, Entra, Azure infra outside this repo

## Supported versions

- Current release + 2 prior minor versions receive security fixes.
- Older versions are unsupported; upgrade to receive fixes.

## Release signing

Release artifacts are signed via sigstore/cosign. Verification instructions ship with each release.
