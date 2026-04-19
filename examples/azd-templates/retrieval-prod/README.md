# retrieval-prod — azd template

Production grounded-retrieval bundle. No side-effect tools. Public network.

## Prerequisites
- Bundle = `retrieval-prod`; profile = `prod-standard`.
- Spec validates via `python tools/validate-spec.py`.
- T2 required in customer repo `pyproject.toml`: `baseline-drift`, `baseline-feedback`.
- RAI scoping minutes + Impact Assessment signed off.
- Customer has signed off on data classification.

## Quickstart
```bash
azd init --template <accelerator-feed>/retrieval-prod@0.1.0
azd up
```

## What's wired
- Foundry project + supported model deployment
- Container Apps host (production SKUs)
- App Insights + Key Vault (KV-backed Foundry connections)
- AI Search + SharePoint connector patterns
- Eval regression gate in CI
- Portal-drift detection via `baseline-drift`

## Supportability
Community best-effort per [`../../../SUPPORT.md`](../../../SUPPORT.md). Partner owns the customer pager.
