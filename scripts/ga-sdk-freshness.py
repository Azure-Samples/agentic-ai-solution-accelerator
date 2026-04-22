"""Weekly GA SDK freshness check.

Reads ``ga-versions.yaml``, queries PyPI for the latest non-pre-release
version of each canonical SDK, and classifies each result into exactly
one bucket:

- **drift** — PyPI has a newer GA than the pinned ``min``. This is the
  only condition that fails the workflow (exit 1).
- **unknown** — PyPI returned nothing usable (404, transient network
  failure, JSON decode error, no GA release published). Surfaced in
  stderr + logs but does NOT fail the workflow, because opening a drift
  issue for a transient PyPI hiccup is worse than missing a week.
- **ok** — PyPI returned a GA that is ``<=`` the pinned ``min``. No
  action needed.

Exit codes:
  0  clean, or only unknowns (transient failures).
  1  at least one drift.
  2  manifest file missing (config error, not a drift condition).

No third-party deps at import time beyond ``pyyaml`` — we use ``urllib``
directly so this runs in a minimal CI image.

Usage::

    python scripts/ga-sdk-freshness.py
    python scripts/ga-sdk-freshness.py --out drift.txt
    python scripts/ga-sdk-freshness.py --fail-on-unknown   # strict mode
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


class LookupUnknown(Exception):
    """PyPI lookup couldn't produce a definitive answer (transient / 404)."""


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


def _pypi_latest_ga(package: str) -> str:
    """Return the highest non-pre-release version of ``package`` on PyPI.

    Raises ``LookupUnknown`` when the lookup fails or the package has no
    GA releases — callers decide whether to treat that as drift.
    """
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        raise LookupUnknown(f"{type(exc).__name__}: {exc}") from exc
    releases = data.get("releases") or {}
    ga = [v for v in releases.keys() if not _BAD_VERSION_TAG.search(v)]
    if not ga:
        raise LookupUnknown("no GA releases in /pypi/{name}/json")
    ga.sort(key=_parse_version)
    return ga[-1]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", help="Write drift report to this path too.")
    p.add_argument(
        "--fail-on-unknown", action="store_true",
        help="Treat PyPI lookup failures as drift (strict mode).",
    )
    args = p.parse_args()

    if not MANIFEST.exists():
        print(f"error: {MANIFEST} not found", file=sys.stderr)
        return 2
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    sdks = manifest.get("sdks") or {}

    drift_lines: list[str] = []
    unknown_lines: list[str] = []
    checked: list[str] = []
    for name, spec in sorted(sdks.items()):
        pinned_min = str(spec.get("min", "")).strip()
        try:
            latest = _pypi_latest_ga(name)
        except LookupUnknown as exc:
            unknown_lines.append(
                f"- `{name}`: PyPI lookup unknown ({exc}); pinned min `{pinned_min}`"
            )
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

    if unknown_lines:
        print("\nUNKNOWN (PyPI lookup failed; not drift):", file=sys.stderr)
        for line in unknown_lines:
            print(line, file=sys.stderr)

    effective_drift = list(drift_lines)
    if args.fail_on_unknown:
        effective_drift.extend(unknown_lines)

    if effective_drift:
        print("\nDRIFT:")
        for line in effective_drift:
            print(line)
        if args.out:
            pathlib.Path(args.out).write_text("\n".join(effective_drift) + "\n", encoding="utf-8")
        return 1
    if args.out:
        pathlib.Path(args.out).write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
