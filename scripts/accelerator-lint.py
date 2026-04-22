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
    required_keys = ["scenario:", "solution:", "acceptance:", "controls:", "kpis:"]
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
# Scenario manifest — structural (AST-only) validation
# ---------------------------------------------------------------------------
_IMPORT_REF_RE = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*:[A-Za-z_][\w]*$")


def _ast_defines(path: pathlib.Path, attr: str) -> bool:
    """Return True if the given file defines ``attr`` at module scope.

    AST-only: we never execute or import the module; this keeps lint safe on
    machines missing runtime deps (Azure SDKs, Foundry creds, etc.).
    """
    if not path.exists():
        return False
    try:
        import ast as _ast
        tree = _ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    for node in tree.body:
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            if node.name == attr:
                return True
        elif isinstance(node, _ast.Assign):
            for t in node.targets:
                if isinstance(t, _ast.Name) and t.id == attr:
                    return True
        elif isinstance(node, _ast.AnnAssign):
            if isinstance(node.target, _ast.Name) and node.target.id == attr:
                return True
    return False


def _resolve_ref_path(package: str, ref: str) -> tuple[pathlib.Path, str]:
    """Return the filesystem path and attr for a ``module:attr`` import ref."""
    module_suffix, attr = ref.split(":")
    full_module = f"{package}.{module_suffix}"
    fs = ROOT / pathlib.Path(*full_module.split("."))
    candidate_file = fs.with_suffix(".py")
    candidate_pkg = fs / "__init__.py"
    if candidate_file.exists():
        return candidate_file, attr
    return candidate_pkg, attr


@check
def scenario_manifest_valid(ctx: Ctx) -> list[Finding]:
    """AST-validate the ``scenario:`` block.

    - Must exist with required keys.
    - ``package`` leaf must be a Python identifier (no hyphens).
    - Referenced modules must exist on disk and define the named attributes.
    - ``endpoint.path`` must start with ``/``.
    Does NOT import anything; runtime wiring is validated separately in
    :func:`src.workflow.registry.load_scenario`.
    """
    m = ROOT / "accelerator.yaml"
    if not m.exists():
        return []
    try:
        import yaml
    except ImportError:
        return [Finding("scenario-manifest", "warn", "accelerator.yaml",
                        "pyyaml not installed; skipping scenario lint")]
    try:
        data = yaml.safe_load(m.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [Finding("scenario-manifest", "block", "accelerator.yaml",
                        f"accelerator.yaml is not valid YAML: {exc}")]

    scenario = data.get("scenario")
    if not scenario:
        return [Finding("scenario-manifest", "block", "accelerator.yaml",
                        "missing top-level 'scenario' block (required since D2).")]

    out: list[Finding] = []
    required = ["id", "package", "request_schema",
                "workflow_factory", "endpoint", "agents"]
    for k in required:
        if k not in scenario:
            out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                               f"scenario.{k} is required"))

    package = scenario.get("package", "")
    if package:
        leaf = package.split(".")[-1]
        if "-" in leaf or not leaf.isidentifier():
            out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                               f"scenario.package leaf must be a Python "
                               f"identifier (underscores only): {leaf!r}"))

    # Endpoint path
    endpoint = scenario.get("endpoint") or {}
    ep_path = endpoint.get("path", "")
    if not isinstance(ep_path, str) or not ep_path.startswith("/"):
        out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                           "scenario.endpoint.path must start with '/'"))

    # AST-check each import ref
    def _check_ref(field: str, ref: str) -> None:
        if not isinstance(ref, str) or not _IMPORT_REF_RE.match(ref):
            out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                               f"scenario.{field} must match 'module:attr', "
                               f"got {ref!r}"))
            return
        if not package:
            return
        fs_path, attr = _resolve_ref_path(package, ref)
        if not fs_path.exists():
            out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                               f"scenario.{field}: target file not found: "
                               f"{_rel(fs_path)}"))
            return
        if not _ast_defines(fs_path, attr):
            out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                               f"scenario.{field}: {_rel(fs_path)} does not "
                               f"define {attr!r}"))

    if "request_schema" in scenario:
        _check_ref("request_schema", scenario["request_schema"])
    if "workflow_factory" in scenario:
        _check_ref("workflow_factory", scenario["workflow_factory"])

    # Agents: non-empty list of {id, foundry_name}
    agents = scenario.get("agents") or []
    if not isinstance(agents, list) or not agents:
        out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                           "scenario.agents must be a non-empty list"))
    else:
        for i, a in enumerate(agents):
            if not isinstance(a, dict) or "id" not in a or "foundry_name" not in a:
                out.append(Finding("scenario-manifest", "block",
                                   "accelerator.yaml",
                                   f"scenario.agents[{i}] needs 'id' and "
                                   "'foundry_name'"))

    # Retrieval indexes (optional, but if present each must be well-formed)
    retrieval = scenario.get("retrieval") or {}
    idx = retrieval.get("indexes") or []
    for i, entry in enumerate(idx):
        if not isinstance(entry, dict):
            out.append(Finding("scenario-manifest", "block", "accelerator.yaml",
                               f"scenario.retrieval.indexes[{i}] must be a mapping"))
            continue
        for k in ("name", "seed", "schema"):
            if k not in entry:
                out.append(Finding("scenario-manifest", "block",
                                   "accelerator.yaml",
                                   f"scenario.retrieval.indexes[{i}].{k} required"))
        if "schema" in entry:
            _check_ref(f"retrieval.indexes[{i}].schema", entry["schema"])
    return out


# ---------------------------------------------------------------------------
# Agent code shape
# ---------------------------------------------------------------------------
def _scenario_agents_root() -> pathlib.Path | None:
    """Resolve the agents package directory from ``scenario.package``.

    Returns ``None`` if the manifest is missing the scenario block or pyyaml
    isn't installed; other checks will surface those failures.
    """
    m = ROOT / "accelerator.yaml"
    if not m.exists():
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        data = yaml.safe_load(m.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    scenario = data.get("scenario") or {}
    package = scenario.get("package")
    if not package or not isinstance(package, str):
        return None
    fs = ROOT / pathlib.Path(*package.split("."))
    agents_dir = fs / "agents"
    return agents_dir if agents_dir.exists() else None


@check
def agents_three_layer(ctx: Ctx) -> list[Finding]:
    agents_root = _scenario_agents_root()
    if agents_root is None:
        # Back-compat: pre-D2 layouts put agents under src/agents. If both are
        # absent, other checks (scenario-manifest) will report the real issue.
        legacy = ROOT / "src/agents"
        if not legacy.exists():
            return []
        agents_root = legacy
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


_REQUIRED_RAI_CATEGORIES = {"Hate", "Sexual", "Violence", "Selfharm"}
_REQUIRED_RAI_SOURCES = {"Prompt", "Completion"}
_ALLOWED_RAI_SEVERITIES = {"Low", "Medium"}


@check
def bicep_has_content_filter(ctx: Ctx) -> list[Finding]:
    """Every model deployment must have a content filter bound, and the
    policy must actually block medium+ severity on all 4 categories for
    both prompt and completion. ``mode: 'Blocking'`` is required and the
    parent account must set ``disableLocalAuth: true``.
    """
    infra = ROOT / "infra"
    if not infra.exists():
        return []
    has_policy = False
    has_binding = False
    has_blocking_mode = False
    category_source_pairs: set[tuple[str, str]] = set()
    severity_violations: list[str] = []
    # Scan for an accounts/raiPolicies resource body across all infra bicep.
    rai_body_re = re.compile(
        r"resource\s+\w+\s+'Microsoft\.CognitiveServices/accounts/raiPolicies@[^']+'\s*=\s*{(?P<body>.*?)^}",
        re.DOTALL | re.MULTILINE,
    )
    account_re = re.compile(
        r"resource\s+\w+\s+'Microsoft\.CognitiveServices/accounts@[^']+'\s*=\s*{(?P<body>.*?)^}",
        re.DOTALL | re.MULTILINE,
    )
    mode_re = re.compile(r"mode\s*:\s*'([^']+)'")
    field_re = re.compile(r"(?P<key>name|source|severityThreshold)\s*:\s*'(?P<val>[A-Za-z]+)'")
    entry_re = re.compile(r"\{(?P<inner>[^{}]*)\}", re.DOTALL)
    local_auth_re = re.compile(r"disableLocalAuth\s*:\s*true")
    accounts_seen = 0
    accounts_with_local_auth_off = 0
    for p, c in ctx.iter(".bicep"):
        if "infra" not in p.parts:
            continue
        for m in account_re.finditer(c):
            accounts_seen += 1
            if local_auth_re.search(m.group("body")):
                accounts_with_local_auth_off += 1
        for m in rai_body_re.finditer(c):
            has_policy = True
            body = m.group("body")
            mode_m = mode_re.search(body)
            if mode_m and mode_m.group(1) == "Blocking":
                has_blocking_mode = True
            for entry in entry_re.finditer(body):
                fields = {m.group("key"): m.group("val")
                          for m in field_re.finditer(entry.group("inner"))}
                cat = fields.get("name")
                src = fields.get("source")
                sev = fields.get("severityThreshold")
                if not (cat and src and sev):
                    continue
                category_source_pairs.add((cat, src))
                if sev not in _ALLOWED_RAI_SEVERITIES:
                    severity_violations.append(f"{cat}/{src}={sev}")
        if _BICEP_RAI_REF_RE.search(c):
            has_binding = True
    out: list[Finding] = []
    if not has_policy:
        out.append(Finding("bicep-rai-policy", "block", "infra/",
                           "no Microsoft.CognitiveServices/accounts/raiPolicies "
                           "resource found; a default content-filter policy must "
                           "be declared in IaC, not in the Foundry portal."))
        return out
    if not has_binding:
        out.append(Finding("bicep-rai-binding", "block", "infra/",
                           "no deployment references raiPolicyName; content filter "
                           "must be bound to the model deployment to prevent "
                           "portal-level bypass."))
    if not has_blocking_mode:
        out.append(Finding("bicep-rai-mode", "block", "infra/",
                           "raiPolicies resource is missing `mode: 'Blocking'`; "
                           "an advisory-only policy does not satisfy the "
                           "accelerator's default safety posture."))
    required_pairs = {(c, s) for c in _REQUIRED_RAI_CATEGORIES
                      for s in _REQUIRED_RAI_SOURCES}
    missing_pairs = sorted(required_pairs - category_source_pairs)
    if missing_pairs:
        out.append(Finding("bicep-rai-coverage", "block", "infra/",
                           "raiPolicies must cover all 4 categories "
                           "(Hate/Sexual/Violence/Selfharm) on both Prompt and "
                           f"Completion; missing: {missing_pairs}"))
    if severity_violations:
        out.append(Finding("bicep-rai-severity", "block", "infra/",
                           "raiPolicies severityThreshold must be Low or Medium "
                           f"for every entry; offenders: {severity_violations}"))
    if accounts_seen and accounts_with_local_auth_off < accounts_seen:
        out.append(Finding("bicep-account-local-auth", "block", "infra/",
                           "every Microsoft.CognitiveServices/accounts resource "
                           "must set `disableLocalAuth: true` to prevent key-based "
                           "access that bypasses RBAC and RAI policy."))
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
    """Lint chain: accelerator-lint -> azd-up -> evals.

    Evals run *after* azd-up so the API URL comes from the deploy itself;
    fighting the day-0 chicken-and-egg where no URL exists to eval against.
    """
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
    out: list[Finding] = []
    expectations = {
        "accelerator-lint": set(),
        "azd-up": {"accelerator-lint"},
        "evals": {"azd-up"},
    }
    for name, required in expectations.items():
        if name not in jobs:
            out.append(Finding("deploy-gate", "block",
                               ".github/workflows/deploy.yml",
                               f"deploy.yml is missing the '{name}' job"))
            continue
        needs = (jobs[name] or {}).get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        needs_set = set(needs or [])
        missing = required - needs_set
        if missing:
            out.append(Finding("deploy-gate", "block",
                               ".github/workflows/deploy.yml",
                               f"job '{name}' must have `needs` including "
                               f"{sorted(required)}; missing: {sorted(missing)}"))
    return out


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
    missing = sorted(n for n in names
                     if not re.search(rf"\b{re.escape(n)}\b", doc_txt))
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
# No stale path references (kills drift after scenario framework move)
# ---------------------------------------------------------------------------
_DEAD_PATHS: tuple[str, ...] = (
    "src/agents/",
    "sales_research_workflow",
    "partner-playbook.md",
    "customization-guide.md",
)
_DEAD_PATH_GLOB_EXTS = {".md", ".yml", ".yaml", ".py", ".json"}
_DEAD_PATH_EXCLUDED_FILES = {
    # this file defines the dead-path list; literals must appear here
    "scripts/accelerator-lint.py",
}
_DEAD_PATH_EXCLUDED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".azure",
    "patterns",  # candidate pattern docs may cite historical shapes
}


@check
def no_dead_paths(ctx: Ctx) -> list[Finding]:
    """Repo must not reference path shapes that were retired by the scenario
    framework (D2) or dropped during the D3 docs sweep.

    After D2 every agent lives under ``src/scenarios/<scenario>/agents/``
    and every workflow under ``src/scenarios/<scenario>/workflow.py``.
    The old ``src/agents/`` tree and the ``sales_research_workflow`` module
    name are dead. ``docs/partner-playbook.md`` and
    ``docs/customization-guide.md`` were deleted in D3. A Copilot-led
    partner following a stale reference lands in a dead path, which is
    embarrassing for a Microsoft-branded template. This rule fails if any
    of those strings appear in any reviewed file.
    """
    out: list[Finding] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in _DEAD_PATH_GLOB_EXTS:
            continue
        rel_posix = path.relative_to(ROOT).as_posix()
        if rel_posix in _DEAD_PATH_EXCLUDED_FILES:
            continue
        if any(part in _DEAD_PATH_EXCLUDED_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in _DEAD_PATHS:
            if needle in text:
                out.append(Finding(
                    "dead-path-ref", "block", _rel(path),
                    f"references retired path {needle!r}; update to the "
                    f"post-D2 scenario layout or drop the reference.",
                ))
    return out


# ---------------------------------------------------------------------------
# Dockerfile must not pin SDKs independently of pyproject.toml
# ---------------------------------------------------------------------------
def _iter_pinned_packages(text: str):
    """Yield ``(pkg, line_no)`` pairs for every package+version-operator
    pair in ``text``. Matches both quoted (``"pkg==x.y"``) and unquoted
    (``RUN pip install pkg==x.y``) forms by scanning line-by-line for the
    shape ``<name><op><version>``. ``<name>`` must start with a letter to
    avoid matching python version selectors like ``python3.11``.
    """
    pin_re = re.compile(
        r"(?<![\w.-])([A-Za-z][A-Za-z0-9_.\-\[\]]*)\s*(?:==|>=|<=|~=|!=|>|<)\s*[0-9][\w.\-]*"
    )
    for idx, line in enumerate(text.splitlines(), start=1):
        for m in pin_re.finditer(line):
            yield m.group(1).lower().split("[")[0], idx


@check
def dockerfile_matches_ga_pins(ctx: Ctx) -> list[Finding]:
    """src/Dockerfile must NOT pin SDKs independently of pyproject.toml.

    Version pins are authoritative in pyproject.toml + ga-versions.yaml. A
    Dockerfile that re-declares canonical SDK pins inline (quoted OR
    unquoted) can drift from the matrix that ``sdks_pinned_to_ga``
    enforces, so the deployed container ends up running SDKs that CI never
    sees. The rule is simple: any canonical SDK listed in ga-versions.yaml
    must not appear as an inline pin in the Dockerfile. Partners should
    ``pip install .`` (or equivalent) so the image matches pyproject.
    """
    dockerfile = ROOT / "src" / "Dockerfile"
    if not dockerfile.exists():
        return []
    manifest = _load_ga_manifest()
    if not manifest:
        return []
    canonical = {k.lower() for k in manifest.keys()}
    text = dockerfile.read_text(encoding="utf-8", errors="ignore")
    out: list[Finding] = []
    for pkg, line_no in _iter_pinned_packages(text):
        if pkg in canonical:
            out.append(Finding(
                "dockerfile-ga-drift", "block", _rel(dockerfile),
                f"line {line_no}: {pkg} is pinned inline in src/Dockerfile. "
                f"Remove the inline pin and install from pyproject.toml "
                f"(`pip install .`) so the runtime image matches the GA "
                f"matrix enforced by lint.",
            ))
    return out


# ---------------------------------------------------------------------------
# Dockerfile must copy the accelerator manifest (scenario loader needs it)
# ---------------------------------------------------------------------------
_DOCKERFILE_MANIFEST_RE = re.compile(
    r"^\s*COPY\s+[^\n]*\baccelerator\.yaml\b", re.MULTILINE
)


@check
def dockerfile_copies_manifest(ctx: Ctx) -> list[Finding]:
    """src/Dockerfile must COPY accelerator.yaml into the image.

    ``src.workflow.registry`` resolves ``ROOT`` from ``src/__file__`` and
    reads ``accelerator.yaml`` at process startup (``src.main`` calls
    ``load_scenario()`` eagerly before mounting any route). If the image
    ships without the manifest, the container crashes on boot and ``azd
    up`` does not produce a working deployment — the single loudest
    promise the accelerator makes. This rule fails if no ``COPY`` line
    in the Dockerfile references ``accelerator.yaml``.
    """
    dockerfile = ROOT / "src" / "Dockerfile"
    if not dockerfile.exists():
        return []
    text = dockerfile.read_text(encoding="utf-8", errors="ignore")
    if _DOCKERFILE_MANIFEST_RE.search(text):
        return []
    return [Finding(
        "dockerfile-missing-manifest", "block", _rel(dockerfile),
        "Dockerfile does not COPY accelerator.yaml. The container cannot "
        "boot without the manifest — src.workflow.registry loads it at "
        "startup. Add `COPY accelerator.yaml ./` before `pip install .`.",
    )]


# ---------------------------------------------------------------------------
# Agent specs must not hardcode the model (Bicep is the source of truth)
# ---------------------------------------------------------------------------
_SPEC_MODEL_RE = re.compile(r"^\*\*Model:\*\*", re.MULTILINE)


@check
def agent_specs_no_hardcoded_model(ctx: Ctx) -> list[Finding]:
    """Agent spec files must not declare ``**Model:**``. The single model
    deployed by ``infra/modules/foundry.bicep`` (``AZURE_AI_FOUNDRY_MODEL``
    env) is authoritative for every agent, so specs that pin a model name
    will silently drift from what azd actually provisions.
    """
    specs_dir = ROOT / "docs/agent-specs"
    if not specs_dir.exists():
        return []
    out: list[Finding] = []
    for p in specs_dir.glob("accel-*.md"):
        if _SPEC_MODEL_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
            out.append(Finding(
                "agent-spec-model-ban", "block", _rel(p),
                "agent specs must not declare **Model:**; the model comes "
                "from AZURE_AI_FOUNDRY_MODEL (emitted by Bicep)."
            ))
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
