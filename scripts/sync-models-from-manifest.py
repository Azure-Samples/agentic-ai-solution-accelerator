"""Sync accelerator.yaml `models:` block to azd environment variables.

Runs from ``azure.yaml`` as the ``preprovision`` hook, so Bicep
parameters derived from the engagement manifest are in sync with what
the partner has declared in ``accelerator.yaml`` before every ``azd up``.

Contract (authoritative — always writes, no conditional branches):
-----------------------------------------------------------------

If ``accelerator.yaml`` declares a ``models:`` block:

* Exactly one entry has ``default: true`` (and MUST use ``slug: default``
  — the slug ``default`` is reserved for the default deployment).
* The default entry drives four env vars that feed ``main.parameters.json``
  → ``foundry.bicep`` single-deployment params:

    AZURE_AI_FOUNDRY_MODEL_NAME        ← default.model
    AZURE_AI_FOUNDRY_MODEL_VERSION     ← default.version
    AZURE_AI_FOUNDRY_MODEL             ← default.deployment_name
    AZURE_AI_FOUNDRY_MODEL_CAPACITY    ← default.capacity

* Non-default entries are packed into a JSON string and written to:

    AZURE_AI_FOUNDRY_EXTRA_DEPLOYMENTS_JSON  (default "[]")

  ``foundry.bicep`` parses this with ``json()`` into an array of
  ``{slug, deployment_name, model, version, capacity}`` objects and
  creates one deployment per entry (``@batchSize(1)``), bound to the
  shared RAI policy.

If ``models:`` is absent — normalised fixed-point state:

* All five managed env vars are rewritten to the template defaults
  that ``infra/main.parameters.json`` declares (gpt-5-mini / 2025-08-07
  / capacity 30 / extras=[]). This makes "remove the block" a
  convergent operation — state doesn't drift from whatever the last
  sync wrote. Partners who want to override the default deployment
  MUST use the ``models:`` block (single-entry is fine); overriding via
  raw env vars is no longer supported because preprovision would
  clobber them on the next ``azd up``.

Orphan deployments (slug removed from the block after a prior
``azd up`` provisioned it) are NOT auto-deleted by Bicep (incremental
ARM mode). ``scripts/foundry-bootstrap.py`` detects them at
postprovision time and emits an actionable warning with the exact
``az cognitiveservices account deployment delete`` command the partner
can run.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "accelerator.yaml"

_REQUIRED_FIELDS = ("slug", "deployment_name", "model", "version", "capacity")

# Template defaults — MUST mirror the defaults in infra/main.parameters.json
# so that "no models block" and "freshly provisioned with no env vars set"
# produce identical Bicep inputs.
_TEMPLATE_DEFAULTS = {
    "AZURE_AI_FOUNDRY_MODEL_NAME": "gpt-5-mini",
    "AZURE_AI_FOUNDRY_MODEL_VERSION": "2025-08-07",
    "AZURE_AI_FOUNDRY_MODEL": "gpt-5-mini",
    "AZURE_AI_FOUNDRY_MODEL_CAPACITY": "30",
}


def _azd_env_set(key: str, value: str) -> None:
    azd = shutil.which("azd")
    if not azd:
        print(
            "::warning::azd not on PATH; skipping env set "
            f"(would have set {key})",
            file=sys.stderr,
        )
        return
    subprocess.run([azd, "env", "set", key, value], check=True)


def main() -> int:
    if not MANIFEST.exists():
        print(f"::error::{MANIFEST} missing", file=sys.stderr)
        return 1

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    models = manifest.get("models")

    if not models:
        # Normalised fixed-point: write template defaults so state is
        # convergent across add-block / remove-block cycles.
        for key, value in _TEMPLATE_DEFAULTS.items():
            _azd_env_set(key, value)
        _azd_env_set("AZURE_AI_FOUNDRY_EXTRA_DEPLOYMENTS_JSON", "[]")
        print(
            "sync-models: no `models:` block; reset to template defaults "
            f"({_TEMPLATE_DEFAULTS['AZURE_AI_FOUNDRY_MODEL']}, extras=[]). "
            "Add a `models:` block to accelerator.yaml to customise."
        )
        return 0

    if not isinstance(models, list):
        print(
            "::error::accelerator.yaml `models:` must be a list of "
            "deployment entries",
            file=sys.stderr,
        )
        return 1

    default_entries = [m for m in models if isinstance(m, dict) and m.get("default")]
    if len(default_entries) != 1:
        print(
            "::error::accelerator.yaml `models:` needs exactly one entry "
            f"with `default: true` (found {len(default_entries)}). The lint "
            "rule `models_block_shape` normally catches this before "
            "preprovision runs.",
            file=sys.stderr,
        )
        return 1

    default = default_entries[0]
    for field in _REQUIRED_FIELDS:
        if field not in default:
            print(
                f"::error::default `models:` entry missing '{field}'",
                file=sys.stderr,
            )
            return 1
    if default["slug"] != "default":
        print(
            "::error::the default `models:` entry must use `slug: default` "
            "(slug 'default' is reserved). Use a different slug for extra "
            "deployments.",
            file=sys.stderr,
        )
        return 1

    extras = []
    for m in models:
        if m is default:
            continue
        if not isinstance(m, dict):
            print(
                "::error::every `models:` entry must be a mapping",
                file=sys.stderr,
            )
            return 1
        for field in _REQUIRED_FIELDS:
            if field not in m:
                print(
                    f"::error::models[slug={m.get('slug', '?')}] missing "
                    f"'{field}'",
                    file=sys.stderr,
                )
                return 1
        if m["slug"] == "default":
            print(
                "::error::slug 'default' is reserved for the default "
                "deployment; use a different slug for extras",
                file=sys.stderr,
            )
            return 1
        extras.append(
            {
                "slug": str(m["slug"]),
                "deployment_name": str(m["deployment_name"]),
                "model": str(m["model"]),
                "version": str(m["version"]),
                "capacity": int(m["capacity"]),
            }
        )

    _azd_env_set("AZURE_AI_FOUNDRY_MODEL_NAME", str(default["model"]))
    _azd_env_set("AZURE_AI_FOUNDRY_MODEL_VERSION", str(default["version"]))
    _azd_env_set("AZURE_AI_FOUNDRY_MODEL", str(default["deployment_name"]))
    _azd_env_set("AZURE_AI_FOUNDRY_MODEL_CAPACITY", str(int(default["capacity"])))
    _azd_env_set(
        "AZURE_AI_FOUNDRY_EXTRA_DEPLOYMENTS_JSON", json.dumps(extras, separators=(",", ":"))
    )

    print(
        f"sync-models: default={default['deployment_name']} "
        f"({default['model']}@{default['version']}, cap={default['capacity']}) "
        f"extras={len(extras)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
