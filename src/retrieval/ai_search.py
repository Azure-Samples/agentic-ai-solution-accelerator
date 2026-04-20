"""Azure AI Search retrieval — the ONLY grounding path for agents.

Agents MUST NOT call out to arbitrary HTTP endpoints for grounding. If you
need a new source, add an index here (and its infra in
``infra/modules/ai-search.bicep``).
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


class AccountRetriever:
    """Grounded retrieval over the ``accounts`` index.

    Index schema (indicative — create in infra/):
        id                str (key)
        content           str
        source            str (url)
        company_name      str (filterable)
        industry          str (filterable)
        last_refreshed    datetime
        embedding         vector
    """

    def __init__(self) -> None:
        s = load_settings()
        self._client = SearchClient(
            endpoint=s.ai_search_endpoint,
            index_name=s.ai_search_index,
            credential=DefaultAzureCredential(),
        )

    async def search(self, query: str, *, top: int = 5,
                     filter_expr: str | None = None) -> list[RetrievedChunk]:
        emit_event(Event(name="retrieval.query",
                         args_redacted={"query_len": len(query), "top": top}))
        results = await self._client.search(
            search_text=query, top=top, filter=filter_expr,
            query_type="semantic", semantic_configuration_name="default",
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
        emit_event(Event(name="retrieval.returned",
                         value=float(len(out)), unit="chunks"))
        return out

    async def close(self) -> None:
        await self._client.close()
