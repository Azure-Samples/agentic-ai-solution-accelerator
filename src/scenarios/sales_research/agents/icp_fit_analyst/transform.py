from __future__ import annotations

import json
from typing import Any

_VALID_NNR = {"strong", "moderate", "weak", "unknown"}


def _coerce_nnr(raw: Any) -> dict[str, str]:
    """Coerce the nnr_indicators block into the closed vocabulary.

    The supervisor downstream prefers a consistent shape over raw model
    output. Unknown values map to ``unknown`` rather than being dropped, so
    the downstream briefing always has the three dimensions rendered.
    """
    if not isinstance(raw, dict):
        raw = {}
    out = {}
    for k in ("size_signal", "growth_signal", "wallet_expansion_signal"):
        v = raw.get(k, "unknown")
        if not isinstance(v, str):
            v = "unknown"
        v = v.strip().lower()
        out[k] = v if v in _VALID_NNR else "unknown"
    return out


def _coerce_signal_evidence(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        signal = item.get("signal")
        source = item.get("source")
        if isinstance(signal, str) and isinstance(source, str) and signal.strip():
            cleaned.append({"signal": signal, "source": source})
    return cleaned


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    return {
        "fit_score": int(data.get("fit_score", 0)),
        "fit_reasons": list(data.get("fit_reasons", []))[:3],
        "fit_risks": list(data.get("fit_risks", []))[:3],
        "recommended_segment": data.get("recommended_segment", "unknown"),
        "recommended_action": data.get("recommended_action", "nurture"),
        "tier_recommendation": data.get("tier_recommendation", "watchlist"),
        "signal_evidence": _coerce_signal_evidence(data.get("signal_evidence")),
        "nnr_indicators": _coerce_nnr(data.get("nnr_indicators")),
        "data_gaps": [s for s in data.get("data_gaps", []) if isinstance(s, str)],
    }
