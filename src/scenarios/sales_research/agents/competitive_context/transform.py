from __future__ import annotations

import json
from typing import Any


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    return {
        "competitors": list(data.get("competitors", [])),
        "differentiators": list(data.get("differentiators", []))[:3],
        "likely_objections": list(data.get("likely_objections", []))[:3],
        "talking_points": list(data.get("talking_points", [])),
    }
