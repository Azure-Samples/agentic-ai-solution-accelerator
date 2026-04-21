from __future__ import annotations

import json
from typing import Any


def transform_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    return {
        "subject": data.get("subject", "").strip(),
        "body_markdown": data.get("body_markdown", "").strip(),
        "primary_cta": data.get("primary_cta", "").strip(),
        "personalization_anchors": list(data.get("personalization_anchors", [])),
    }
