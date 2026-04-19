# Security Policy

## Reporting

Report security issues to Microsoft Security Response Center (MSRC):
https://msrc.microsoft.com/create-report

Do NOT file public issues for security vulnerabilities.

## Scope of accepted reports

- T1 core package (`azure-agentic-baseline`)
- T2 profile-required packages (`baseline-drift`, `baseline-feedback`, `baseline-hitl`, `baseline-actions`)
- `baseline-cli`
- Shipped Bicep modules + azd templates for blessed bundles
- Schema files
- Copilot instructions + chat modes (for prompt-injection-enabling issues)

**Out of scope:**
- Partner-authored business logic in customer repos
- T3 reference (`baseline-cache`, `examples/`)
- Customer's own Azure subscription policies or landing zone
- Bugs in Foundry, Entra, Azure infra outside this repo

## Emergency security patch lane

Accepted critical issues (CVE with exploitability, cryptographic compromise, tenant-isolation bypass) are released on the **emergency patch lane** — see `compatibility/upgrade-transaction-model.md` §4.7.

- MSFT side: ring 0 → ring 2 within 24h with governance board sign-off
- Partner side: 7-calendar-day mandatory adoption window
- Emergency patches may NOT contain contract-phase migrations or `forward_fix_only` changes

## Supported versions

- Current release + 2 prior minor versions receive security fixes
- Older versions are unsupported

## Cryptographic model

- Release artifacts signed via sigstore/cosign
- Attestations published to sigstore Rekor (transparency log)
- Qualification manifests bound via GitHub OIDC + Rekor UUID (see `docs/rai/attestation-scope.md`)
