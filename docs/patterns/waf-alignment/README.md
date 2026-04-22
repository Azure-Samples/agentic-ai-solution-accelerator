# WAF alignment

How each Well-Architected pillar (plus the AI workload extension) shows up in this accelerator.

Legend:

- 🟢 **In the box** — shipped: Bicep, lint, eval, or telemetry enforces it.
- 🟡 **Partner customisation** — pattern-guided; partner tunes per customer.
- 🔴 **Customer responsibility** — accelerator cannot own this.

---

## Reliability

| Decision | Posture | How |
|---|---|---|
| SSE streaming for long calls | 🟢 | `src/main.py` streams via `StreamingResponse`. |
| Per-agent timeout + retry | 🟢 | `agent_framework` client configuration. |
| Eval regression gate in CI | 🟢 | `.github/workflows/evals.yml` runs `evals/quality/` + `evals/redteam/` and enforces `accelerator.yaml.acceptance`. |
| Manifest required for boot | 🟢 | Lint rule `dockerfile_copies_manifest` blocks drift. |
| HA beyond single region | 🟡 | `infra/main.bicep` is region-agnostic; partner wires pairing per SLA. |
| DR RTO/RPO | 🔴 | Customer incident-response posture. |

## Security

| Decision | Posture | How |
|---|---|---|
| Managed identity for all Azure access | 🟢 | `infra/modules/identity.bicep` + app uses `DefaultAzureCredential()`. |
| KV-backed secrets, no inline creds | 🟢 | Lint rules `no_inline_credentials` + `kv_references_only`. |
| Content filter locked at strict default via IaC | 🟢 | `infra/modules/foundry.bicep` (`accelerator-default-policy`); lint rule `content_filter_iac_only` blocks portal drift. |
| XPIA / prompt-injection surface scoped | 🟢 | Retrieval layer only returns declared fields; red-team suite probes leakage. |
| Private link for confidential data | 🟡 | `enablePrivateLink` param in `infra/main.bicep`; partner flips per customer. |
| SDK CVE posture | 🟢 | `pip-audit` stub in `.github/workflows/`; `ga-versions.yaml` pinned, weekly freshness. |
| Data classification enforcement | 🟡 | Declared in `accelerator.yaml` solution block; partner maps to tool catalog. |
| Customer Entra tenancy + DLP | 🔴 | Customer identity + network team. |

## Cost Optimization

| Decision | Posture | How |
|---|---|---|
| Per-call cost tracking in telemetry | 🟢 | `src/accelerator_baseline/telemetry.py` emits typed events; `cost_per_call_usd` in `accelerator.yaml.acceptance` is a CI gate. |
| Acceptance thresholds fail CI on regression | 🟢 | `src/accelerator_baseline/evals.py` + `.github/workflows/evals.yml`. |
| Mandatory Azure tags | 🟢 | `infra/main.bicep` applies `azd-env-name` + `accelerator-version` tags. |
| Model tier selection | 🟡 | `modelName` + `modelCapacity` params in `infra/main.bicep`; partner picks per quota. |
| FinOps maturity + chargeback | 🔴 | Customer finance. |

## Operational Excellence

| Decision | Posture | How |
|---|---|---|
| Single-manifest solution definition | 🟢 | `accelerator.yaml` is the only source of truth; `scripts/accelerator-lint.py` validates. |
| Eval-as-deploy-gate | 🟢 | `.github/workflows/evals.yml` must pass before `azd deploy`. |
| Application Insights wired by default | 🟢 | `infra/modules/monitor.bicep` + `azure-monitor-opentelemetry` in `pyproject.toml`. |
| Weekly SDK freshness signal | 🟢 | `.github/workflows/version-matrix.yml` + `scripts/ga-sdk-freshness.py`. |
| Runbooks for incidents | 🟡 | Pattern-guided; partner owns runbook authoring per engagement. |
| Customer day-2 ops ownership | 🔴 | Customer ops. |

## Performance Efficiency

| Decision | Posture | How |
|---|---|---|
| Streaming responses by default | 🟢 | SSE. |
| Cold-start mitigation | 🟢 | Container Apps min-replicas in `infra/modules/containerapp.bicep`. |
| P95 latency gate | 🟢 | `p95_latency_ms` in `accelerator.yaml.acceptance` is a CI gate. |
| Parallel worker execution | 🟡 | Workflow factory controls fan-out; partner tunes per scenario. |
| Customer capacity planning | 🔴 | Customer infra team + Azure support. |

## AI workload / RAI

| Decision | Posture | How |
|---|---|---|
| Content filter strict by default | 🟢 | Bicep; `content_filter_iac_only` lint. |
| Groundedness threshold as CI gate | 🟢 | `groundedness_threshold` in `accelerator.yaml.acceptance`. |
| HITL on every declared side-effect | 🟢 | Tools in `src/tools/` must register a HITL checkpoint; lint rule `tool_registers_hitl`. |
| Red-team eval suite in CI | 🟢 | `evals/redteam/run.py` + `redteam_must_pass` acceptance gate. |
| Grounding source attribution in response | 🟢 | Workers emit `citations` arrays; `must_cite` eval check. |
| Model choice for domain | 🟡 | `modelName` param; partner validates via evals. |
| Residual prompt injection on novel attacks | 🔴 | Industry-wide unsolved — defence in depth (content filter + grounding restrictions + HITL + red-team + kill switch). |

---

## Explicitly out of scope for v1

- Sovereign cloud.
- Multi-tenant control plane.
- Signed bundles / cryptographic attestation of partner-customised repos.
- Terraform first-class (BYO-IaC is fine — match the Bicep contracts).
- .NET / Java runtime parity (roadmap).
- More than 5 coordinated agents.
