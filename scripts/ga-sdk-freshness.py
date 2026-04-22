"""Weekly GA SDK freshness check.

Reads ``ga-versions.yaml``, queries PyPI for the latest non-pre-release
version of each canonical SDK, and emits drift lines to stdout. Exits 0
on clean, 1 on drift (so the workflow can gate the issue creation).

No third-party deps at import time beyond ``pyyaml`` — we use ``urllib``
directly so this runs in a minimal CI image.

Usage::

    python scripts/ga-sdk-freshness.py
    python scripts/ga-sdk-freshness.py --out drift.txt
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "ga-versions.yaml"

_BAD_VERSION_TAG = re.compile(
    r"(?:a\d+|b\d+|rc\d+|\.dev\d+|-preview|-alpha|-beta|-rc)",
    re.IGNORECASE,
)


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a semver-ish version into a sortable tuple. Drops tags."""
    clean = re.split(r"[a-zA-Z+-]", v)[0]
    parts = []
    for chunk in clean.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _pypi_latest_ga(package: str) -> str | None:
    """Return the highest non-pre-release version of ``package`` on PyPI,
    or ``None`` on network/parse failure.
    """
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    releases = data.get("releases") or {}
    ga = [v for v in releases.keys() if not _BAD_VERSION_TAG.search(v)]
    if not ga:
        return None
    ga.sort(key=_parse_version)
    return ga[-1]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", help="Write drift report to this path too.")
    args = p.parse_args()

    if not MANIFEST.exists():
        print(f"error: {MANIFEST} not found", file=sys.stderr)
        return 2
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    sdks = manifest.get("sdks") or {}

    drift_lines: list[str] = []
    checked: list[str] = []
    for name, spec in sorted(sdks.items()):
        pinned_min = str(spec.get("min", "")).strip()
        latest = _pypi_latest_ga(name)
        if latest is None:
            drift_lines.append(f"- `{name}`: PyPI lookup failed; pinned min `{pinned_min}`")
            continue
        checked.append(f"{name}\t{pinned_min}\t{latest}")
        if not pinned_min:
            continue
        if _parse_version(latest) > _parse_version(pinned_min):
            drift_lines.append(
                f"- `{name}`: pinned min `{pinned_min}` < latest GA `{latest}` on PyPI"
            )

    print("package\tpinned_min\tlatest_ga")
    for row in checked:
        print(row)

    if drift_lines:
        print("\nDRIFT:")
        for line in drift_lines:
            print(line)
        if args.out:
            pathlib.Path(args.out).write_text("\n".join(drift_lines) + "\n", encoding="utf-8")
        return 1
    if args.out:
        pathlib.Path(args.out).write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
