# Version matrix

Known-good GA-only versions of the SDKs this accelerator depends on. A weekly CI job (`.github/workflows/version-matrix.yml`) runs `scripts/ga-sdk-freshness.py`, which queries PyPI for the latest non-pre-release of each canonical SDK listed in `ga-versions.yaml` and opens a tracking issue if any pinned `min` is behind the latest GA. Deprecation policy: **N-1 minor** supported.

Pinned in `pyproject.toml`; `ga-versions.yaml` is the manifest lint enforces drift against. Update all three together: this table, `pyproject.toml`, and `ga-versions.yaml`.

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
- Foundry model deployments: default `gpt-4o-mini` (flagship; parameterized via `modelName` / `modelDeploymentName` in `infra/main.bicep`). Partners override per engagement; the weekly freshness script validates canonical GA SDKs against PyPI regardless of model choice.
- Azure regions: the deployment is region-agnostic; AI Foundry + AI Search availability is the constraint.

## Cadence
- **Weekly** (`version-matrix.yml`): `ga-sdk-freshness.py` hits PyPI, opens an issue on drift.
- **Monthly**: maintainer review; cut a minor release of the template if fixes or new features land.
- **Quarterly**: blessed-pattern promotions (see `CONTRIBUTING.md`).
