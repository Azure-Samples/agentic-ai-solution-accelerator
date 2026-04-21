"""Azure AI Search retrieval - the ONLY grounding path for agents.

Agents MUST NOT call out to arbitrary HTTP endpoints for grounding. If you
need a new source, add an index here (and its infra in
``infra/modules/ai-search.bicep``) and declare it under
``scenario.retrieval.indexes`` in ``accelerator.yaml``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.search.documents.aio import SearchClient

from ..accelerator_baseline.telemetry import Event, emit_event
from ..config.settings import load_settings


@dataclass
class RetrievedChunk:
    id: str
    content: str
    source: str
    score: float
    metadata: dict[str, Any]


class SearchRetriever:
    """Generic grounded retrieval over an AI Search index.

    The index *name* is passed by the scenario (via the manifest); the
    *endpoint* and managed-identity auth come from settings. Agents should
    NOT instantiate this directly - the workflow wires the correct index
    name per scenario.
    """

    def __init__(self, index_name: str) -> None:
        if not index_name:
            raise ValueError("SearchRetriever requires a non-empty index_name")
        s = load_settings()
        self._index_name = index_name
        self._client = SearchClient(
            endpoint=s.ai_search_endpoint,
            index_name=index_name,
            credential=DefaultAzureCredential(),
        )

    @property
    def index_name(self) -> str:
        return self._index_name

    async def search(
        self,
        query: str,
        *,
        top: int = 5,
        filter_expr: str | None = None,
    ) -> list[RetrievedChunk]:
        emit_event(Event(
            name="retrieval.query",
            args_redacted={
                "index": self._index_name,
                "query_len": len(query),
                "top": top,
            },
        ))
        results = await self._client.search(
            search_text=query,
            top=top,
            filter=filter_expr,
            query_type="semantic",
            semantic_configuration_name="default",
        )
        out: list[RetrievedChunk] = []
        async for r in results:
            out.append(RetrievedChunk(
                id=r["id"],
                content=r["content"],
                source=r.get("source", ""),
                score=float(r["@search.score"]),
                metadata={k: v for k, v in r.items()
                          if k not in ("id", "content", "source")},
            ))
        emit_event(Event(
            name="retrieval.returned",
            value=float(len(out)),
            unit="chunks",
        ))
        return out

    async def close(self) -> None:
        await self._client.close()
