"""Create (or verify) the ``accounts`` AI Search index + seed it with samples.

Called from ``azure.yaml`` ``postprovision`` hook. Idempotent: safe to re-run.

Inputs (env, set by ``azd``):
    AZURE_AI_SEARCH_ENDPOINT   required
    AZURE_AI_SEARCH_INDEX      default: accounts
    AZURE_AI_SEARCH_SEED       default: data/samples/accounts.json

Auth: DefaultAzureCredential only. The accelerator is opinionated — no
keys in app code. The Bicep module grants ``Search Service Contributor`` +
``Search Index Data Contributor`` to the bootstrap identity.

Exit non-zero if:
- the index can't be created (blocks `azd up`)
- any seed doc fails to upload
- final /query smoke test returns 0 results
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _index_def(name: str) -> SearchIndex:
    return SearchIndex(
        name=name,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="company_name", type=SearchFieldDataType.String,
                            filterable=True, facetable=True),
            SearchableField(name="industry", type=SearchFieldDataType.String,
                            filterable=True, facetable=True),
            SimpleField(name="last_refreshed", type=SearchFieldDataType.DateTimeOffset,
                        filterable=True, sortable=True),
        ],
        semantic_search=SemanticSearch(configurations=[
            SemanticConfiguration(
                name="default",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="company_name"),
                                     SemanticField(field_name="industry")],
                ),
            )
        ]),
    )


def main() -> int:
    endpoint = os.environ.get("AZURE_AI_SEARCH_ENDPOINT")
    if not endpoint:
        print("::error::AZURE_AI_SEARCH_ENDPOINT is not set", file=sys.stderr)
        return 1

    index_name = os.environ.get("AZURE_AI_SEARCH_INDEX", "accounts")
    seed_path = ROOT / os.environ.get("AZURE_AI_SEARCH_SEED", "data/samples/accounts.json")

    cred = DefaultAzureCredential()
    ic = SearchIndexClient(endpoint=endpoint, credential=cred)

    # 1. Create or update the index (idempotent).
    try:
        ic.create_or_update_index(_index_def(index_name))
        print(f"index ok: {index_name}")
    except Exception as exc:
        print(f"::error::failed to create/update index {index_name}: {exc}",
              file=sys.stderr)
        return 1

    # 2. Seed docs (upload = upsert).
    if not seed_path.exists():
        print(f"::warning::seed file not found: {seed_path}; skipping seeding")
    else:
        docs = json.loads(seed_path.read_text(encoding="utf-8"))
        sc = SearchClient(endpoint=endpoint, index_name=index_name, credential=cred)
        result = sc.upload_documents(documents=docs)
        errors = [r for r in result if not r.succeeded]
        if errors:
            print(f"::error::{len(errors)} seed docs failed to upload",
                  file=sys.stderr)
            return 1
        print(f"seeded {len(docs)} documents into {index_name}")

    # 3. Smoke query so provisioning fails fast if something is wrong.
    sc = SearchClient(endpoint=endpoint, index_name=index_name, credential=cred)
    hits = list(sc.search(search_text="*", top=1))
    if not hits:
        print(f"::error::smoke query returned 0 hits for {index_name}",
              file=sys.stderr)
        return 1
    print(f"smoke query ok: {index_name} returned {len(hits)} hit(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
