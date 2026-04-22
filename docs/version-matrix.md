# Version matrix

Known-good GA-only versions of the SDKs this accelerator depends on. A weekly CI job (`.github/workflows/version-matrix.yml`) runs `scripts/ga-sdk-freshness.py`, which queries PyPI for the latest non-pre-release of each canonical SDK listed in `ga-versions.yaml`. The script classifies each package into one of three buckets:

- **drift** — PyPI has a newer GA than the pinned `min`. The workflow fails and opens a tracking issue.
- **unknown** — PyPI lookup failed (404, network, JSON decode, or no GA release). The workflow surfaces the warning in the run summary but does **not** fail and does **not** open an issue — a transient PyPI hiccup should not generate noise.
- **ok** — PyPI returned a GA `<=` the pinned `min`.

Deprecation policy: **N-1 minor** supported.

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

## ARM api-versions
- The lint rule `no_preview_api_versions` rejects any `*-preview` api-version in `infra/**`. Narrow, documented exemptions live in `infra/.ga-exceptions.yaml`. Each exemption must carry a `reason` and a `revisit_by` month.
- **Current exemption set** (1 entry): `Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview` — Azure has not yet shipped a non-preview api-version for the Foundry project sub-resource. All other Foundry primitives (model deployments, RAI policy, RBAC) are on GA `2024-10-01`. Revisit: 2026-10.

## Cadence
- **Weekly** (`version-matrix.yml`): `ga-sdk-freshness.py` hits PyPI; opens an issue only on real drift. Transient lookup failures land in the workflow summary as warnings.
- **Monthly**: maintainer review; cut a minor release of the template if fixes or new features land.
- **Quarterly**: blessed-pattern promotions (see `CONTRIBUTING.md`).
