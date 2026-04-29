"""Unit tests for src.accelerator_baseline.citations."""
from __future__ import annotations

from src.accelerator_baseline.citations import (
    assert_no_hallucinated_urls,
    require_citations,
)


def test_require_citations_passes_when_no_factual_fields_present():
    ok, msg = require_citations(
        {"summary": "", "citations": []},
        when_fields_present=("recent_news", "buying_committee"),
    )
    assert ok and msg == ""


def test_require_citations_passes_when_citations_present():
    ok, msg = require_citations(
        {"recent_news": ["x"], "citations": [{"url": "https://example.com"}]},
        when_fields_present=("recent_news",),
    )
    assert ok and msg == ""


def test_require_citations_fails_when_factual_field_populated_no_citations():
    ok, msg = require_citations(
        {"recent_news": ["x"], "citations": []},
        when_fields_present=("recent_news", "buying_committee"),
    )
    assert not ok
    assert "recent_news" in msg
    assert "groundedness" in msg


def test_require_citations_rejects_non_list_citations():
    ok, msg = require_citations(
        {"recent_news": ["x"], "citations": "not a list"},
        when_fields_present=("recent_news",),
    )
    assert not ok
    assert "must be a list" in msg


def test_require_citations_treats_empty_string_as_unpopulated():
    ok, msg = require_citations(
        {"recent_news": "", "citations": []},
        when_fields_present=("recent_news",),
    )
    assert ok and msg == ""


def test_assert_no_hallucinated_urls_passes_when_host_matches():
    ok, _ = assert_no_hallucinated_urls(
        [{"url": "https://www.contoso.com/news/1"}],
        ["https://www.contoso.com/wiki", "https://docs.contoso.com/"],
    )
    assert ok


def test_assert_no_hallucinated_urls_fails_on_unknown_host():
    ok, msg = assert_no_hallucinated_urls(
        [{"url": "https://hallucinated.example/x"}],
        ["https://www.contoso.com/wiki"],
    )
    assert not ok
    assert "hallucinated.example" in msg


def test_assert_no_hallucinated_urls_fails_open_when_no_sources():
    ok, _ = assert_no_hallucinated_urls(
        [{"url": "https://anything.example/x"}], [],
    )
    assert ok


def test_assert_no_hallucinated_urls_skips_url_less_citations():
    ok, _ = assert_no_hallucinated_urls(
        [{"id": "doc-42", "quote": "..."}],
        ["https://www.contoso.com/wiki"],
    )
    assert ok


def test_assert_no_hallucinated_urls_empty_citations():
    ok, _ = assert_no_hallucinated_urls([], ["https://x.example"])
    assert ok
