# retrieval-prod — azd template

Production grounded-retrieval bundle. No side-effect tools. Public network.

## Prerequisites
- Path B qualification complete (`.qualification.yaml` Rekor-verified).
- Bundle = `retrieval-prod`; profile = `prod-standard`.
- T2 required: `baseline-drift`, `baseline-feedback`.

## Quickstart
```bash
azd init --template agentic-ai-accelerator/retrieval-prod@0.1.0
azd up
baseline attest --capture && baseline attest --issue
baseline deploy --verify <attestation-id>
```

## Supportability
Full attestation-backed support per `SUPPORT.md`.
