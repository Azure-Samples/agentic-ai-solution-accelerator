"""Citation helpers for grounded agent validators.

Lightweight, dependency-free helpers used inside an agent's ``validate.py``
to enforce two common groundedness rules:

1. **No factual claim without a citation** — :func:`require_citations`
   returns a finding when any of a configured set of factual fields are
   populated but the response carries no citations.
2. **No hallucinated URLs** — :func:`assert_no_hallucinated_urls` rejects
   citations whose URL host did not appear in the workflow's retrieved
   grounding sources.

The expected shape is what flagship workers already emit: a top-level
``"citations"`` list of dicts, each typically carrying ``url``, ``quote``,
``source``, ``id``. Keys are free-form because Foundry agent outputs
vary; only ``url`` is referenced for hallucination checking.

Usage from a worker validator::

    from src.accelerator_baseline.citations import require_citations

    def validate_response(response):
        ok, msg = require_citations(
            response,
            when_fields_present=("recent_news", "buying_committee"),
        )
        if not ok:
            return False, msg
        return True, ""
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

__all__ = [
    "require_citations",
    "assert_no_hallucinated_urls",
    "extract_tool_trace_uris",
]


def require_citations(
    response: dict[str, Any],
    *,
    when_fields_present: Iterable[str],
    field: str = "citations",
) -> tuple[bool, str]:
    """Enforce that ``response[field]`` is non-empty when factual claims exist.

    Returns ``(True, "")`` on success or ``(False, message)`` on violation.

    A factual claim "exists" when any field name in ``when_fields_present``
    is present in the response with a truthy value (non-empty list / non-
    empty string / non-zero number). If no such field is populated, the
    response is permitted to carry zero citations (e.g. a routing-only
    supervisor that just emits ``next_steps``).

    Args:
        response: The transformed agent output (a dict).
        when_fields_present: Field names that, when populated, require
            citations. Pass the worker's factual fields here.
        field: Name of the citations list field. Defaults to
            ``"citations"`` to match flagship convention.
    """
    citations = response.get(field, [])
    if not isinstance(citations, list):
        return False, (
            f"{field!r} must be a list (got {type(citations).__name__})"
        )
    if citations:
        return True, ""
    populated = [f for f in when_fields_present if response.get(f)]
    if populated:
        return False, (
            f"groundedness violation: {populated} populated without "
            f"{field!r}; every factual claim needs a source"
        )
    return True, ""


def assert_no_hallucinated_urls(
    citations: list[dict[str, Any]],
    retrieved_sources: Iterable[str],
    *,
    field: str = "url",
) -> tuple[bool, str]:
    """Reject citations whose URL host is not in ``retrieved_sources``.

    Returns ``(True, "")`` on success or ``(False, message)`` on the first
    citation whose URL host does not match any retrieved source. Matches
    by lowercased hostname so trailing-slash and path differences do not
    trigger false positives.

    Behaviour:
        - Empty ``citations``: returns ``(True, "")``.
        - Empty ``retrieved_sources``: returns ``(True, "")`` (fails open;
          unit-test stub paths and ungrounded scenarios should not break).
        - Citations without a ``url`` field: skipped — IDs and quote-only
          citations are valid in some scenarios.

    Args:
        citations: The list under ``response["citations"]`` after transform.
        retrieved_sources: The URLs (or IDs) that the workflow's grounding
            step actually returned for this turn.
        field: Citation key holding the URL. Defaults to ``"url"``.
    """
    if not citations:
        return True, ""
    retrieved_hosts: set[str] = set()
    for s in retrieved_sources:
        if not s:
            continue
        try:
            host = urlparse(s).hostname or s
        except ValueError:
            host = s
        retrieved_hosts.add(str(host).lower())
    if not retrieved_hosts:
        return True, ""
    for i, c in enumerate(citations):
        url = c.get(field)
        if not url:
            continue
        try:
            host = (urlparse(url).hostname or "").lower()
        except ValueError:
            host = ""
        if host and host not in retrieved_hosts:
            return False, (
                f"citations[{i}].{field} host {host!r} not in retrieved "
                "sources (possible hallucination)"
            )
    return True, ""


def extract_tool_trace_uris(response: Any) -> set[str]:
    """Walk a Foundry ``AgentResponse`` and return URIs from tool traces.

    Foundry agents annotate text content with citation entries when a
    hosted tool (FoundryIQ knowledge base, Bing grounding, etc.) supplies
    retrieved sources. Each citation lives on
    ``response.messages[i].contents[j].annotations[k]`` as a TypedDict
    with at least ``type: "citation"`` and ``url``. This helper extracts
    the set of URLs so a workflow can pass them to
    :func:`assert_no_hallucinated_urls` even in ``foundry_tool``
    retrieval mode (where Python never sees the search call directly).

    The implementation is duck-typed (no agent_framework import) so
    tests can pass plain dicts / SimpleNamespace stubs and the helper
    survives SDK shape drift across preview revs. Anything that doesn't
    look like a citation is skipped silently — a Foundry rev that adds a
    new annotation type will degrade gracefully rather than raise.

    Args:
        response: A Foundry ``AgentResponse`` (or anything exposing
            ``messages -> contents -> annotations``). ``None`` is
            allowed and yields an empty set.

    Returns:
        Set of URL strings (deduplicated, order-insensitive). Empty when
        no citation annotations are present.
    """
    uris: set[str] = set()
    if response is None:
        return uris
    messages = getattr(response, "messages", None)
    if messages is None and isinstance(response, dict):
        messages = response.get("messages")
    for msg in messages or []:
        contents = getattr(msg, "contents", None)
        if contents is None and isinstance(msg, dict):
            contents = msg.get("contents")
        for content in contents or []:
            annots = getattr(content, "annotations", None)
            if annots is None and isinstance(content, dict):
                annots = content.get("annotations")
            for ann in annots or []:
                # ``Annotation`` is a TypedDict at runtime → plain dict.
                if not isinstance(ann, dict):
                    continue
                if ann.get("type") != "citation":
                    continue
                url = ann.get("url")
                if isinstance(url, str) and url:
                    uris.add(url)
    return uris
