"""Stage markdown content for MkDocs Pages build.

Copies canonical markdown from across the repo into a single `docs-build/`
tree so MkDocs sees one flat doc root without polluting the authoring layout.

Layout after staging:
  docs-build/                     <- docs/**
  docs-build/QUICKSTART.md        <- QUICKSTART.md
  docs-build/about/<name>.md      <- AGENTS | SECURITY | SUPPORT | CONTRIBUTING | CLA
  docs-build/chatmodes/*.md       <- .github/chatmodes/*.md

Rewrites links inside each staged file based on the file's origin and
staged depth so cross-doc links resolve within the published tree.
Canonical files in the repo are never modified.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_SRC = REPO_ROOT / "docs"
STAGE = REPO_ROOT / "docs-build"

ROOT_TOP = ["QUICKSTART.md"]
ROOT_ABOUT = ["AGENTS.md", "SECURITY.md", "SUPPORT.md", "CONTRIBUTING.md"]
CHATMODES_SRC = REPO_ROOT / ".github" / "chatmodes"
CLA_SRC = REPO_ROOT / ".github" / "CLA.md"


def rewrites_for_root_top() -> list[tuple[re.Pattern[str], str]]:
    return [
        (re.compile(r"\]\(docs/"), "]("),
        (re.compile(r"\]\(\.github/chatmodes/([^)#]+)\.md"), r"](chatmodes/\1.md"),
        (re.compile(r"\]\(\.github/CLA\.md"), "](about/CLA.md"),
    ]


def rewrites_for_root_about() -> list[tuple[re.Pattern[str], str]]:
    return [
        (re.compile(r"\]\(docs/"), "](../"),
        (re.compile(r"\]\(\.github/chatmodes/([^)#]+)\.md"), r"](../chatmodes/\1.md"),
        (re.compile(r"\]\(\.github/CLA\.md"), "](CLA.md"),
    ]


def rewrites_for_docs_tree(depth: int) -> list[tuple[re.Pattern[str], str]]:
    """Rewrites for a docs/ file staged `depth` dirs below docs-build root.

    Canonical links at depth N use (N+1) ``../`` segments to reach repo
    root. After staging, the file lives at docs-build/<same path>, so it
    needs N ``../`` segments to reach docs-build root. We therefore
    consume one ``../`` from every repo-root-bound link, plus remap the
    destination folders (docs/, .github/chatmodes/, .github/CLA.md) to
    their staged locations.

    Works generically for any depth ≥ 0.
    """
    up_in = "\\.\\./" * (depth + 1)
    up_out = "../" * depth  # string prefix in replacements

    def _md(pattern_body: str, replacement_body: str) -> tuple[re.Pattern[str], str]:
        return (re.compile(r"\]\(" + up_in + pattern_body), "](" + up_out + replacement_body)

    def _click(pattern_body: str, replacement_body: str) -> tuple[re.Pattern[str], str]:
        return (re.compile(r'(click\s+\w+\s+")' + up_in + pattern_body),
                r"\1" + up_out + replacement_body)

    md_rules: list[tuple[re.Pattern[str], str]] = [
        _md(r"QUICKSTART\.md", "QUICKSTART.md"),
        _md(r"README\.md", "index.md"),
        _md(r"AGENTS\.md", "about/AGENTS.md"),
        _md(r"SECURITY\.md", "about/SECURITY.md"),
        _md(r"SUPPORT\.md", "about/SUPPORT.md"),
        _md(r"CONTRIBUTING\.md", "about/CONTRIBUTING.md"),
        _md(r"docs/", ""),
        _md(r"\.github/chatmodes/", "chatmodes/"),
        _md(r"\.github/CLA\.md", "about/CLA.md"),
    ]
    click_rules: list[tuple[re.Pattern[str], str]] = [
        _click(r"QUICKSTART\.md", "QUICKSTART.md"),
        _click(r"README\.md", "index.md"),
        _click(r"\.github/chatmodes/", "chatmodes/"),
        _click(r"docs/", ""),
    ]
    return md_rules + click_rules


def apply_rewrites(text: str, rules: list[tuple[re.Pattern[str], str]]) -> str:
    for pat, repl in rules:
        text = pat.sub(repl, text)
    return text


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_DESCRIPTION_RE = re.compile(r"^description:\s*(.+?)\s*$", re.MULTILINE)


def wrap_chatmode_for_pages(text: str, filename: str) -> str:
    """Wrap a `*.chatmode.md` source for partner-facing publication.

    Chatmodes are runtime system prompts for Copilot Chat — a wall of
    LLM instructions that's confusing as a standalone Pages URL. This
    function:
      1. Prepends a short partner-facing intro (what / when / what to ask).
      2. Collapses the original prompt body inside a `<details>` block so
         the page reads as orientation by default but still exposes the
         full prompt for partners who want it.

    Handles chatmodes with or without YAML frontmatter; the `description`
    field, if present, seeds the intro paragraph. Source `.chatmode.md`
    files are never modified — runtime consumers (Copilot Chat) keep
    seeing the original content.
    """
    description = ""
    body = text
    fm = _FRONTMATTER_RE.match(text)
    if fm:
        body = text[fm.end():]
        desc_m = _DESCRIPTION_RE.search(fm.group(1))
        if desc_m:
            description = desc_m.group(1).strip().strip('"\'')

    slug = filename
    for suffix in (".chatmode.md", ".md"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
            break
    command = f"/{slug}"

    intro_blurb = description or (
        "A scoped Copilot Chat mode bundled with this accelerator for a "
        "specific partner-delivery task."
    )

    body_stripped = body.strip()

    return (
        f"# `{command}` chatmode\n\n"
        f"!!! info \"Partner-facing intro\"\n"
        f"    **What it is:** {intro_blurb}\n\n"
        f"    **When to load it:** In **VS Code with GitHub Copilot Chat** "
        f"installed, after cloning this template repo. Type `{command}` in the "
        f"chat input — Copilot picks up the mode from `.github/chatmodes/` "
        f"automatically. (Other LLM IDEs that read `.github/chatmodes/` work "
        f"the same way.)\n\n"
        f"    **What to ask:** Open-ended task questions in the area above; the "
        f"chatmode walks you through the inputs it needs and produces the "
        f"expected artifacts.\n\n"
        f"The full system prompt is reproduced below for transparency. You "
        f"don't need to read it to use the chatmode — Copilot loads it for "
        f"you when you invoke the command.\n\n"
        f"<details markdown=\"1\">\n"
        f"<summary><strong>System prompt (full text)</strong></summary>\n\n"
        f"{body_stripped}\n\n"
        f"</details>\n"
    )


def stage_file(src: Path, dst: Path, rules: list[tuple[re.Pattern[str], str]]) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    original = src.read_text(encoding="utf-8")
    updated = apply_rewrites(original, rules)
    dst.write_text(updated, encoding="utf-8")
    return updated != original


def stage() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    rewritten = 0

    docs_rules_cache: dict[int, list[tuple[re.Pattern[str], str]]] = {}
    for src in DOCS_SRC.rglob("*.md"):
        rel = src.relative_to(DOCS_SRC)
        depth = len(rel.parts) - 1
        rules = docs_rules_cache.setdefault(depth, rewrites_for_docs_tree(depth))
        if stage_file(src, STAGE / rel, rules):
            rewritten += 1

    # Stage non-markdown assets (workbook CSVs, ROI calculators, images,
    # etc.) so partners can download them from the published site.
    # MkDocs copies any file under `docs_dir` to the site output, so
    # mirroring the source-tree path here is enough — no nav entry
    # needed.
    asset_suffixes = {".csv", ".xlsx", ".xlsm", ".png", ".jpg", ".jpeg",
                      ".svg", ".pdf", ".gif", ".webp", ".css"}
    asset_count = 0
    for src in DOCS_SRC.rglob("*"):
        if not src.is_file() or src.suffix.lower() not in asset_suffixes:
            continue
        rel = src.relative_to(DOCS_SRC)
        dst = STAGE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        asset_count += 1

    top_rules = rewrites_for_root_top()
    for name in ROOT_TOP:
        src = REPO_ROOT / name
        if src.exists() and stage_file(src, STAGE / name, top_rules):
            rewritten += 1

    about_rules = rewrites_for_root_about()
    for name in ROOT_ABOUT:
        src = REPO_ROOT / name
        if src.exists() and stage_file(src, STAGE / "about" / name, about_rules):
            rewritten += 1
    if CLA_SRC.exists() and stage_file(CLA_SRC, STAGE / "about" / "CLA.md", about_rules):
        rewritten += 1

    if CHATMODES_SRC.exists():
        chatmodes_dst = STAGE / "chatmodes"
        chatmodes_dst.mkdir(exist_ok=True)
        for cm in CHATMODES_SRC.glob("*.md"):
            wrapped = wrap_chatmode_for_pages(cm.read_text(encoding="utf-8"), cm.name)
            (chatmodes_dst / cm.name).write_text(wrapped, encoding="utf-8")

    total_md = sum(1 for _ in STAGE.rglob("*.md"))
    print(f"Staged {total_md} markdown files into {STAGE.relative_to(REPO_ROOT)}/")
    print(f"Staged {asset_count} non-markdown assets")
    print(f"Rewrote out-of-tree links in {rewritten} files")


if __name__ == "__main__":
    try:
        stage()
    except Exception as exc:
        print(f"prepare-pages failed: {exc}", file=sys.stderr)
        sys.exit(1)
