from __future__ import annotations

import json
from typing import Any


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    return {
        "fit_score": int(data.get("fit_score", 0)),
        "fit_reasons": list(data.get("fit_reasons", []))[:3],
        "fit_risks": list(data.get("fit_risks", []))[:3],
        "recommended_segment": data.get("recommended_segment", "unknown"),
        "recommended_action": data.get("recommended_action", "nurture"),
    }
