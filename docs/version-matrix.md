# Version matrix

Known-good versions of the SDKs this accelerator depends on. A weekly CI job (`.github/workflows/version-matrix.yml`) re-runs the eval suite against the `latest` release of each package and opens an issue on regression. Deprecation policy: **N-1 minor** supported.

Pinned in `pyproject.toml`; update this table and re-pin together.

| Package | Pinned range | Last validated | Latest tested | Notes |
|---|---|---|---|---|
| `agent-framework` | `>=1.0.0,<2.0.0` | 1.0.x |  | Microsoft Agent Framework — orchestration |
| `azure-ai-projects` | `>=1.0.0,<2.0.0` | 1.0.x |  | Foundry projects + agents API |
| `azure-ai-agents` | `>=1.0.0,<2.0.0` | 1.0.x |  | Foundry agent operations |
| `azure-ai-evaluation` | `>=1.0.0,<2.0.0` | 1.0.x |  | Evals SDK |
| `azure-identity` | `>=1.18.0,<2.0.0` | 1.18.x |  | DefaultAzureCredential, ManagedIdentityCredential |
| `azure-keyvault-secrets` | `>=4.8.0,<5.0.0` | 4.8.x |  | KV references |
| `azure-search-documents` | `>=11.5.0,<12.0.0` | 11.5.x |  | AI Search client |
| `azure-monitor-opentelemetry` | `>=1.6.0,<2.0.0` | 1.6.x |  | App Insights distro |
| `opentelemetry-api` / `-sdk` | `>=1.27.0,<2.0.0` | 1.27.x |  | Pinned together to avoid protocol drift |
| `fastapi` | `>=0.115.0,<1.0.0` | 0.115.x |  | HTTP surface |
| `pydantic` | `>=2.9.0,<3.0.0` | 2.9.x |  | Schemas |

## Platform targets
- Python: **3.11** and **3.12**. 3.13 once Agent Framework declares support.
- Foundry model deployments: `gpt-5.2` (flagship default). Alternatives validated as a list in the weekly matrix.
- Azure regions: the deployment is region-agnostic; AI Foundry + AI Search availability is the constraint.

## Cadence
- Weekly CI: pinned + `--upgrade --pre` smoke; open issue on diff.
- Monthly: maintainer review; cut a minor release of the template if fixes or new features land.
- Quarterly: blessed-pattern promotions (see `CONTRIBUTING.md`).
