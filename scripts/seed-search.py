"""Create (or verify) every AI Search index declared by the scenario + seed it.

Called from ``azure.yaml`` ``postprovision`` hook. Idempotent: safe to re-run.

Manifest-driven: reads ``scenario.retrieval.indexes[]`` from
``accelerator.yaml``. For each entry:
- imports the declared ``schema`` callable (``module:attr`` relative to
  ``scenario.package``)
- calls it with the index ``name`` to get the ``SearchIndex`` definition
- create-or-updates the index on the Search service
- uploads documents from ``seed`` (relative to repo root) if the file exists
- runs a smoke ``/query`` and fails fast if it returns zero results

Inputs (env, set by ``azd``):
    AZURE_AI_SEARCH_ENDPOINT   required

Auth: DefaultAzureCredential only. The Bicep module grants ``Search Service
Contributor`` + ``Search Index Data Contributor`` to the bootstrap identity.
"""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so "src.*" imports resolve when invoked bare


def _load_indexes() -> list[dict]:
    """Parse ``scenario.retrieval.indexes`` from ``accelerator.yaml``."""
    from src.workflow.registry import read_scenario_raw

    scenario = read_scenario_raw(ROOT / "accelerator.yaml")
    package = scenario["package"]
    entries = (scenario.get("retrieval") or {}).get("indexes") or []
    parsed: list[dict] = []
    for i, e in enumerate(entries):
        for k in ("name", "seed", "schema"):
            if k not in e:
                raise ValueError(
                    f"accelerator.yaml: scenario.retrieval.indexes[{i}] "
                    f"missing {k!r}"
                )
        module_suffix, attr = e["schema"].split(":")
        full_mod = f"{package}.{module_suffix}"
        schema_fn = getattr(importlib.import_module(full_mod), attr)
        parsed.append({"name": e["name"], "seed": e["seed"],
                       "schema_fn": schema_fn})
    return parsed


def main() -> int:
    endpoint = os.environ.get("AZURE_AI_SEARCH_ENDPOINT")
    if not endpoint:
        print("::error::AZURE_AI_SEARCH_ENDPOINT is not set", file=sys.stderr)
        return 1

    try:
        indexes = _load_indexes()
    except Exception as exc:
        print(f"::error::failed to parse scenario retrieval indexes: {exc}",
              file=sys.stderr)
        return 1

    if not indexes:
        print("::warning::scenario.retrieval.indexes is empty; nothing to seed")
        return 0

    cred = DefaultAzureCredential()
    ic = SearchIndexClient(endpoint=endpoint, credential=cred)

    for entry in indexes:
        name = entry["name"]
        seed_path = ROOT / entry["seed"]
        schema_fn = entry["schema_fn"]

        try:
            ic.create_or_update_index(schema_fn(name))
            print(f"index ok: {name}")
        except Exception as exc:
            print(f"::error::failed to create/update index {name}: {exc}",
                  file=sys.stderr)
            return 1

        if not seed_path.exists():
            print(f"::warning::seed file not found: {seed_path}; skipping seeding")
        else:
            docs = json.loads(seed_path.read_text(encoding="utf-8"))
            sc = SearchClient(endpoint=endpoint, index_name=name, credential=cred)
            result = sc.upload_documents(documents=docs)
            errors = [r for r in result if not r.succeeded]
            if errors:
                print(f"::error::{len(errors)} seed docs failed to upload into {name}",
                      file=sys.stderr)
                return 1
            print(f"seeded {len(docs)} documents into {name}")

        sc = SearchClient(endpoint=endpoint, index_name=name, credential=cred)
        hits = list(sc.search(search_text="*", top=1))
        if not hits:
            print(f"::error::smoke query returned 0 hits for {name}",
                  file=sys.stderr)
            return 1
        print(f"smoke query ok: {name} returned {len(hits)} hit(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
