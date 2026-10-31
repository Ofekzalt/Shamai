from __future__ import annotations

import json
from typing import Any


def canonical_params(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, separators=(",", ":"))
