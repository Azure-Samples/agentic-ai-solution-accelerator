"""Index definitions for the Sales Research & Outreach scenario.

The ``schema`` callable is referenced from ``accelerator.yaml`` and is the
single source of truth for the AI Search index shape. ``src/bootstrap.py`` (running inside the Container App at FastAPI startup)
calls it to create/update the index; at runtime the app doesn't need the
schema — it only needs the index *name* to query.
"""
from __future__ import annotations

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


def index_definition(name: str) -> SearchIndex:
    """Return the ``accounts`` index definition.

    The scenario manifest passes the configured index name (defaults to
    ``accounts``) so partners can rename without touching this file.
    """
    return SearchIndex(
        name=name,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(
                name="source", type=SearchFieldDataType.String, filterable=True
            ),
            SearchableField(
                name="company_name",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="industry",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="last_refreshed",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
            ),
        ],
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[SemanticField(field_name="content")],
                        keywords_fields=[
                            SemanticField(field_name="company_name"),
                            SemanticField(field_name="industry"),
                        ],
                    ),
                )
            ]
        ),
    )
