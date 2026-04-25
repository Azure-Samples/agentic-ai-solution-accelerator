from __future__ import annotations

import json
from typing import Any

_VALID_STANCES = {"incumbent", "challenger", "evaluator", "absent", "unknown"}
_VALID_PROVIDERS = {"aws", "gcp", "azure", "oci", "other"}


def _coerce_competitor(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    name = item.get("name")
    if not (isinstance(name, str) and name.strip()):
        return None
    stance = item.get("stance", "unknown")
    if not isinstance(stance, str):
        stance = "unknown"
    stance = stance.strip().lower()
    if stance not in _VALID_STANCES:
        stance = "unknown"
    evidence = item.get("evidence", "")
    if not isinstance(evidence, str):
        evidence = ""
    urls_raw = item.get("evidence_urls", [])
    urls = [u for u in urls_raw if isinstance(u, str)] if isinstance(urls_raw, list) else []
    return {
        "name": name,
        "stance": stance,
        "evidence": evidence,
        "evidence_urls": urls,
    }


def _coerce_cloud_signal(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    provider = item.get("provider", "")
    if not isinstance(provider, str):
        return None
    provider = provider.strip().lower()
    if provider not in _VALID_PROVIDERS:
        return None
    workload = item.get("workload_signal", "")
    if not isinstance(workload, str) or not workload.strip():
        return None
    evidence = item.get("evidence", "")
    if not isinstance(evidence, str):
        evidence = ""
    signal: dict[str, Any] = {
        "provider": provider,
        "workload_signal": workload,
        "evidence": evidence,
    }
    url = item.get("evidence_url")
    if isinstance(url, str) and url.strip():
        signal["evidence_url"] = url
    return signal


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    competitors_raw = data.get("competitors", [])
    competitors: list[dict[str, Any]] = []
    if isinstance(competitors_raw, list):
        for c in competitors_raw:
            cleaned = _coerce_competitor(c)
            if cleaned is not None:
                competitors.append(cleaned)

    cloud_raw = data.get("cloud_footprint_signals", [])
    cloud_signals: list[dict[str, Any]] = []
    if isinstance(cloud_raw, list):
        for s in cloud_raw:
            cleaned = _coerce_cloud_signal(s)
            if cleaned is not None:
                cloud_signals.append(cleaned)

    refs_raw = data.get("competitor_refs", [])
    competitor_refs = [b for b in refs_raw if isinstance(b, str) and b.strip()] \
        if isinstance(refs_raw, list) else []

    return {
        "competitors": competitors,
        "differentiators": list(data.get("differentiators", []))[:3],
        "likely_objections": list(data.get("likely_objections", []))[:3],
        "talking_points": list(data.get("talking_points", [])),
        "cloud_footprint_signals": cloud_signals,
        "competitor_refs": competitor_refs,
    }
