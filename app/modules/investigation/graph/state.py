from __future__ import annotations

from typing import Any, TypedDict


class RunState(TypedDict, total=False):
    job_id: str
    request: dict[str, Any]
    result_json: dict[str, Any]
