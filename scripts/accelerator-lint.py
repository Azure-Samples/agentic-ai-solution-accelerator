"""Accelerator lint — ~30 deterministic rules enforced in CI.

Run:
    python scripts/accelerator-lint.py            # full project scan
    python scripts/accelerator-lint.py --fix-hint # show fix hints only
    python scripts/accelerator-lint.py --json     # machine-readable

Exit non-zero on any BLOCKING finding. WARN findings are printed but do not
fail CI. Extend by adding functions to ``CHECKS`` below; keep them pure (no
IO side effects beyond file reads) so they can run in parallel workers.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable

ROOT = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
@dataclass
class Finding:
    rule: str
    severity: str  # "block" | "warn"
    path: str
    message: str


@dataclass
class Ctx:
    files: dict[pathlib.Path, str] = field(default_factory=dict)

    def load(self) -> None:
        for p in ROOT.rglob("*"):
            if not p.is_file():
                continue
            if any(part in {".git", "node_modules", "__pycache__", ".venv"}
                   for part in p.parts):
                continue
            if p.suffix in {".py", ".md", ".yaml", ".yml", ".json", ".bicep", ".toml"}:
                try:
                    self.files[p] = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

    def iter(self, *exts: str) -> Iterable[tuple[pathlib.Path, str]]:
        for p, c in self.files.items():
            if not exts or p.suffix in exts:
                yield p, c


CheckFn = Callable[[Ctx], list[Finding]]
CHECKS: list[CheckFn] = []


def check(fn: CheckFn) -> CheckFn:
    CHECKS.append(fn)
    return fn


def _rel(p: pathlib.Path) -> str:
    return str(p.relative_to(ROOT))


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
@check
def manifest_present(ctx: Ctx) -> list[Finding]:
    m = ROOT / "accelerator.yaml"
    if not m.exists():
        return [Finding("manifest-present", "block", "accelerator.yaml",
                        "accelerator.yaml is required at repo root")]
    txt = m.read_text(encoding="utf-8")
    required_keys = ["solution:", "acceptance:", "controls:", "kpis:"]
    missing = [k for k in required_keys if k not in txt]
    return [Finding("manifest-required-keys", "block", "accelerator.yaml",
                    f"missing top-level key: {k}") for k in missing]


@check
def solution_brief_present(ctx: Ctx) -> list[Finding]:
    brief = ROOT / "docs/discovery/solution-brief.md"
    if not brief.exists():
        return [Finding("brief-present", "block", _rel(brief),
                        "docs/discovery/solution-brief.md is required")]
    txt = brief.read_text(encoding="utf-8")
    placeholder_markers = ["<!-- FILL IN:", "TBD", "TODO:"]
    if any(m in txt for m in placeholder_markers):
        return [Finding("brief-unfilled", "warn", _rel(brief),
                        "Solution brief still contains FILL IN / TBD / TODO markers.")]
    return []


# ---------------------------------------------------------------------------
# Agent code shape
# ---------------------------------------------------------------------------
@check
def agents_three_layer(ctx: Ctx) -> list[Finding]:
    agents_root = ROOT / "src/agents"
    if not agents_root.exists():
        return []
    out: list[Finding] = []
    for agent_dir in agents_root.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
            continue
        for required in ("prompt.py", "transform.py", "validate.py", "__init__.py"):
            if not (agent_dir / required).exists():
                out.append(Finding("agent-three-layer", "block",
                                   _rel(agent_dir / required),
                                   f"{agent_dir.name} missing {required}"))
        init = agent_dir / "__init__.py"
        if init.exists() and "AGENT_NAME" not in init.read_text(encoding="utf-8"):
            out.append(Finding("agent-name-export", "block", _rel(init),
                               "__init__.py must export AGENT_NAME"))
    return out


# ---------------------------------------------------------------------------
# Security / identity
# ---------------------------------------------------------------------------
_SECRET_PATTERNS = [
    re.compile(r"AccountKey=[A-Za-z0-9/+=]{20,}"),
    re.compile(r"(?i)api[_-]?key\s*=\s*[\"'][A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)password\s*=\s*[\"'][^\"']{4,}[\"']"),
    re.compile(r"(?i)connectionstring\s*=\s*[\"']endpoint=.+accountkey="),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"),
]


@check
def no_hardcoded_secrets(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for p, c in ctx.iter():
        for pat in _SECRET_PATTERNS:
            if pat.search(c):
                out.append(Finding("no-secrets", "block", _rel(p),
                                   f"matches secret pattern {pat.pattern[:40]}..."))
                break
    return out


@check
def uses_default_azure_credential(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    bad = re.compile(r"AzureKeyCredential|ClientSecretCredential\(|os\.environ\[['\"].*KEY['\"]\]")
    for p, c in ctx.iter(".py"):
        if p.name == "accelerator-lint.py":
            continue
        if bad.search(c):
            out.append(Finding("default-azure-credential", "block", _rel(p),
                               "use DefaultAzureCredential; no key / secret-credential usage."))
    return out


# ---------------------------------------------------------------------------
# HITL wiring
# ---------------------------------------------------------------------------
@check
def side_effect_tools_call_hitl(ctx: Ctx) -> list[Finding]:
    tools_dir = ROOT / "src/tools"
    if not tools_dir.exists():
        return []
    out: list[Finding] = []
    for p in tools_dir.glob("*.py"):
        c = p.read_text(encoding="utf-8")
        if "HITL_POLICY" not in c:
            continue  # read-only tool
        if "checkpoint(" not in c:
            out.append(Finding("hitl-required", "block", _rel(p),
                               "side-effect tool must call hitl.checkpoint before executing."))
    return out


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------
@check
def no_print_statements(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for p, c in ctx.iter(".py"):
        if p.name == "accelerator-lint.py":
            continue
        for i, line in enumerate(c.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("print(") and "# lint-ok" not in line:
                if "patterns/" in str(p) or "src/" in str(p):
                    out.append(Finding("no-print", "warn", f"{_rel(p)}:{i}",
                                       "use telemetry.emit_event, not print()."))
                    break
    return out


@check
def emits_typed_events(ctx: Ctx) -> list[Finding]:
    required = {"request.received", "response.returned", "tool.executed"}
    seen: set[str] = set()
    pattern = re.compile(r"Event\(name=['\"]([^'\"]+)['\"]")
    for p, c in ctx.iter(".py"):
        if "/accelerator_baseline/" in str(p):
            continue
        for m in pattern.finditer(c):
            seen.add(m.group(1))
    missing = required - seen
    return [Finding("typed-events", "warn", "src/",
                    f"no emitter found for event: {m}") for m in missing]


# ---------------------------------------------------------------------------
# Infrastructure / identity in Bicep
# ---------------------------------------------------------------------------
@check
def container_app_uses_managed_identity(ctx: Ctx) -> list[Finding]:
    f = ROOT / "infra/modules/container-app.bicep"
    if not f.exists():
        return []
    c = f.read_text(encoding="utf-8")
    if "UserAssigned" not in c and "SystemAssigned" not in c:
        return [Finding("aca-mi", "block", _rel(f),
                        "Container App must use UserAssigned or SystemAssigned managed identity.")]
    return []


@check
def key_vault_rbac_only(ctx: Ctx) -> list[Finding]:
    f = ROOT / "infra/modules/key-vault.bicep"
    if not f.exists():
        return []
    c = f.read_text(encoding="utf-8")
    if "enableRbacAuthorization: true" not in c:
        return [Finding("kv-rbac", "block", _rel(f),
                        "Key Vault must use RBAC authorization (enableRbacAuthorization: true)")]
    return []


# ---------------------------------------------------------------------------
# Copilot shaping assets exist
# ---------------------------------------------------------------------------
@check
def copilot_assets_present(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    required = [
        ".github/copilot-instructions.md",
        ".github/chatmodes/discover-scenario.chatmode.md",
        ".github/chatmodes/scaffold-from-brief.chatmode.md",
        "AGENTS.md",
    ]
    for r in required:
        if not (ROOT / r).exists():
            out.append(Finding("copilot-asset", "block", r, f"missing {r}"))
    return out


# ---------------------------------------------------------------------------
# Evals hooked up
# ---------------------------------------------------------------------------
@check
def evals_present(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for path in ("evals/quality/golden_cases.jsonl", "evals/quality/run.py",
                 "evals/redteam/cases.jsonl", "evals/redteam/run.py"):
        if not (ROOT / path).exists():
            out.append(Finding("evals-present", "block", path, f"missing {path}"))
    return out


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------
@check
def ci_workflows_present(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for wf in ("lint.yml", "evals.yml", "deploy.yml", "version-matrix.yml"):
        if not (ROOT / ".github/workflows" / wf).exists():
            out.append(Finding("ci-workflow", "block", f".github/workflows/{wf}",
                               f"missing GitHub workflow: {wf}"))
    return out


# ---------------------------------------------------------------------------
# Acceptance wiring (manifest → evals)
# ---------------------------------------------------------------------------
@check
def acceptance_wired_to_evals(ctx: Ctx) -> list[Finding]:
    m = ROOT / "accelerator.yaml"
    if not m.exists():
        return []
    c = m.read_text(encoding="utf-8")
    # crude: any acceptance threshold mentioned; evals run.py reads thresholds too
    if "acceptance:" in c and "quality_threshold" not in c:
        return [Finding("acceptance-wiring", "warn", "accelerator.yaml",
                        "acceptance block present but no quality_threshold key.")]
    return []


# ---------------------------------------------------------------------------
# Foundry / Bicep policy enforcement
# ---------------------------------------------------------------------------
_BICEP_DEPLOYMENT_RE = re.compile(
    r"resource\s+\w+\s+'Microsoft\.CognitiveServices/accounts/deployments@"
)
_BICEP_RAI_RE = re.compile(
    r"resource\s+\w+\s+'Microsoft\.CognitiveServices/accounts/raiPolicies@"
)
_BICEP_RAI_REF_RE = re.compile(r"raiPolicyName\s*:")


@check
def bicep_has_model_deployment(ctx: Ctx) -> list[Finding]:
    """azd up must provision at least one model deployment (no "bring your own")."""
    infra = ROOT / "infra"
    if not infra.exists():
        return []
    for p, c in ctx.iter(".bicep"):
        if "infra" not in p.parts:
            continue
        if _BICEP_DEPLOYMENT_RE.search(c):
            return []
    return [Finding("bicep-model-deployment", "block", "infra/",
                    "no Microsoft.CognitiveServices/accounts/deployments resource "
                    "found under infra/**; azd up must deploy a model, not rely on "
                    "a pre-existing one.")]


@check
def bicep_has_content_filter(ctx: Ctx) -> list[Finding]:
    """Every model deployment must have a content filter bound."""
    infra = ROOT / "infra"
    if not infra.exists():
        return []
    has_policy = False
    has_binding = False
    for p, c in ctx.iter(".bicep"):
        if "infra" not in p.parts:
            continue
        if _BICEP_RAI_RE.search(c):
            has_policy = True
        if _BICEP_RAI_REF_RE.search(c):
            has_binding = True
    out: list[Finding] = []
    if not has_policy:
        out.append(Finding("bicep-rai-policy", "block", "infra/",
                           "no Microsoft.CognitiveServices/accounts/raiPolicies "
                           "resource found; a default content-filter policy must "
                           "be declared in IaC, not in the Foundry portal."))
    if not has_binding:
        out.append(Finding("bicep-rai-binding", "block", "infra/",
                           "no deployment references raiPolicyName; content filter "
                           "must be bound to the model deployment to prevent "
                           "portal-level bypass."))
    return out


def _load_ga_exceptions() -> dict[str, str]:
    """Load {resource_type: api_version} from infra/.ga-exceptions.yaml."""
    f = ROOT / "infra/.ga-exceptions.yaml"
    if not f.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return {
        e.get("resource_type", ""): str(e.get("api_version", ""))
        for e in data.get("exceptions", [])
        if e.get("resource_type") and e.get("api_version")
    }


_BICEP_RESOURCE_RE = re.compile(
    r"resource\s+\w+\s+'([A-Za-z0-9./]+)@([0-9A-Za-z.\-]+)'", re.MULTILINE
)


@check
def no_preview_api_versions(ctx: Ctx) -> list[Finding]:
    """Every Bicep resource under infra/ must use a non-preview api-version,
    unless explicitly allow-listed in infra/.ga-exceptions.yaml."""
    exceptions = _load_ga_exceptions()
    out: list[Finding] = []
    for p, c in ctx.iter(".bicep"):
        if "infra" not in p.parts:
            continue
        for match in _BICEP_RESOURCE_RE.finditer(c):
            resource_type, api_version = match.group(1), match.group(2)
            if "preview" not in api_version.lower() and not re.search(
                r"(alpha|beta|rc)", api_version.lower()
            ):
                continue
            allowed = exceptions.get(resource_type)
            if allowed == api_version:
                continue
            out.append(Finding(
                "ga-api-version",
                "block",
                _rel(p),
                f"{resource_type}@{api_version} is a preview api-version; "
                f"either switch to GA or add a documented exception to "
                f"infra/.ga-exceptions.yaml.",
            ))
    return out


# ---------------------------------------------------------------------------
# CI chaining: deploy must depend on lint + evals
# ---------------------------------------------------------------------------
@check
def deploy_gated_on_lint_and_evals(ctx: Ctx) -> list[Finding]:
    f = ROOT / ".github/workflows/deploy.yml"
    if not f.exists():
        return [Finding("deploy-gate", "block", ".github/workflows/deploy.yml",
                        "deploy.yml is missing")]
    try:
        import yaml
    except ImportError:
        return []
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [Finding("deploy-gate", "block", ".github/workflows/deploy.yml",
                        f"deploy.yml is not valid YAML: {exc}")]
    jobs = data.get("jobs", {}) or {}
    deploy_job = None
    for name, body in jobs.items():
        if name in {"azd-up", "deploy"}:
            deploy_job = (name, body or {})
            break
    if deploy_job is None:
        return [Finding("deploy-gate", "block", ".github/workflows/deploy.yml",
                        "no `azd-up` or `deploy` job found.")]
    name, body = deploy_job
    needs = body.get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    needs_set = set(needs or [])
    required = {"accelerator-lint", "evals"}
    missing = required - needs_set
    if missing:
        return [Finding("deploy-gate", "block", ".github/workflows/deploy.yml",
                        f"job '{name}' must have `needs: [accelerator-lint, evals]`; "
                        f"missing: {sorted(missing)}")]
    # Check that jobs named accelerator-lint and evals exist in the same workflow.
    missing_jobs = [n for n in ("accelerator-lint", "evals") if n not in jobs]
    if missing_jobs:
        return [Finding("deploy-gate", "block", ".github/workflows/deploy.yml",
                        f"deploy.yml references jobs that do not exist in the same "
                        f"workflow: {missing_jobs}. Define them inline or via `uses:`.")]
    return []


# ---------------------------------------------------------------------------
# Workflow secrets must be documented
# ---------------------------------------------------------------------------
_SECRET_REF_RE = re.compile(r"\$\{\{\s*(secrets|vars)\.([A-Z0-9_]+)\s*\}\}")


@check
def workflow_secrets_documented(ctx: Ctx) -> list[Finding]:
    wf_dir = ROOT / ".github/workflows"
    doc = ROOT / "docs/getting-started.md"
    if not wf_dir.exists():
        return []
    names: set[str] = set()
    for p in wf_dir.glob("*.yml"):
        c = p.read_text(encoding="utf-8", errors="ignore")
        for m in _SECRET_REF_RE.finditer(c):
            names.add(m.group(2))
    # GITHUB_TOKEN is auto-provisioned; don't require it in the doc.
    names.discard("GITHUB_TOKEN")
    if not names:
        return []
    if not doc.exists():
        return [Finding("secrets-doc", "block", "docs/getting-started.md",
                        f"docs/getting-started.md is missing but workflows reference "
                        f"{len(names)} secrets/vars: {sorted(names)}")]
    doc_txt = doc.read_text(encoding="utf-8")
    missing = sorted(n for n in names if n not in doc_txt)
    if missing:
        return [Finding("secrets-doc", "block", "docs/getting-started.md",
                        f"workflow secrets/vars not documented: {missing}")]
    return []


# ---------------------------------------------------------------------------
# SDKs pinned to GA versions (no preview/alpha/beta/rc)
# ---------------------------------------------------------------------------
_BAD_VERSION_TAG = re.compile(r"(a\d|b\d|rc\d|alpha|beta|preview|dev\d)", re.IGNORECASE)


def _parse_pyproject_pins() -> dict[str, str]:
    f = ROOT / "pyproject.toml"
    if not f.exists():
        return {}
    try:
        import tomllib  # py311+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return {}
    data = tomllib.loads(f.read_text(encoding="utf-8"))
    deps = (data.get("project", {}) or {}).get("dependencies", []) or []
    pins: dict[str, str] = {}
    for dep in deps:
        # Split on first non-name char to get package name
        m = re.match(r"([A-Za-z0-9_\-]+)(.*)", dep.strip())
        if m:
            pins[m.group(1).lower()] = m.group(2).strip()
    return pins


def _load_ga_manifest() -> dict[str, dict]:
    f = ROOT / "ga-versions.yaml"
    if not f.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data.get("sdks", {}) or {}


@check
def sdks_pinned_to_ga(ctx: Ctx) -> list[Finding]:
    """Canonical SDK set (agent-framework, azure-ai-*, azure-identity,
    azure-search-documents) must be pinned to non-preview versions, and the
    pin specifiers in pyproject.toml must match ga-versions.yaml."""
    manifest = _load_ga_manifest()
    if not manifest:
        return [Finding("ga-versions-manifest", "block", "ga-versions.yaml",
                        "ga-versions.yaml is required at repo root "
                        "(see d1-ga-sdk-enforce).")]
    pins = _parse_pyproject_pins()
    out: list[Finding] = []
    for sdk, spec in manifest.items():
        sdk_key = sdk.lower()
        actual = pins.get(sdk_key)
        if actual is None:
            out.append(Finding("ga-pin-missing", "block", "pyproject.toml",
                               f"{sdk} is in ga-versions.yaml but not pinned in "
                               f"pyproject.toml dependencies."))
            continue
        if _BAD_VERSION_TAG.search(actual):
            out.append(Finding("ga-pin-preview", "block", "pyproject.toml",
                               f"{sdk} pin contains a non-GA tag "
                               f"(preview/alpha/beta/rc): {actual!r}"))
            continue
        min_v = str(spec.get("min", "")).strip()
        upper = str(spec.get("upper_exclusive", "")).strip()
        if min_v and f">={min_v}" not in actual:
            out.append(Finding("ga-pin-mismatch", "block", "pyproject.toml",
                               f"{sdk} min version mismatch: pyproject has "
                               f"{actual!r}, manifest requires >={min_v}"))
        if upper and f"<{upper}" not in actual:
            out.append(Finding("ga-pin-mismatch", "block", "pyproject.toml",
                               f"{sdk} upper bound mismatch: pyproject has "
                               f"{actual!r}, manifest requires <{upper}"))
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    p.add_argument("--fix-hint", action="store_true")
    args = p.parse_args()

    ctx = Ctx()
    ctx.load()
    findings: list[Finding] = []
    for fn in CHECKS:
        try:
            findings.extend(fn(ctx))
        except Exception as exc:  # a bad check shouldn't tank the whole lint
            findings.append(Finding(fn.__name__, "warn", "scripts/accelerator-lint.py",
                                    f"check error: {exc}"))

    blockers = [f for f in findings if f.severity == "block"]
    warns = [f for f in findings if f.severity == "warn"]

    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        for f in findings:
            icon = "[BLOCK]" if f.severity == "block" else "[warn] "
            print(f"{icon} [{f.rule}] {f.path}: {f.message}")
        print("")
        print(f"{len(blockers)} blocking, {len(warns)} warning findings.")
        if blockers:
            print("Fix blocking findings above. See docs/patterns/ for rationale.")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
