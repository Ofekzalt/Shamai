from __future__ import annotations

import json
from typing import Any


def canonical_request_json(body: dict[str, Any]) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"))
