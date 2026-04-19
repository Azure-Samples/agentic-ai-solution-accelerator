# retrieval-prod-pl — azd template

Private-link variant of `retrieval-prod`. Use when customer data classification is confidential/restricted and prod-standard public endpoints are not acceptable.

## Prerequisites
- As `retrieval-prod`, plus:
- Customer VNet + DNS strategy agreed (decision record required).
- Target region must have private-link SKUs GA for Foundry + AI Search.

## Quickstart
```bash
azd init --template agentic-ai-accelerator/retrieval-prod-pl@0.1.0
azd up
```
