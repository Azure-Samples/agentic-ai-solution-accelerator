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
