from __future__ import annotations

from typing import Annotated, Any, TypedDict

RESET = "__reset__"


def _extend(left: list | None, right: list | None) -> list:
    items = list(right or [])
    if items and items[0] == RESET:
        return items[1:]
    return list(left or []) + items


def _extend_unique_followups(left: list | None, right: list | None) -> list:
    from app.modules.investigation.graph.followups import followup_identity

    items = list(right or [])
    if items and items[0] == RESET:
        items = items[1:]
        left = []
    out: list[dict[str, Any]] = list(left or [])
    seen = {followup_identity(item) for item in out if item != RESET}
    for item in items:
        if item == RESET:
            continue
        key = followup_identity(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _add_int(left: int | None, right: int | str | None) -> int:
    if right == RESET:
        return 0
    return int(left or 0) + int(right or 0)


class RunState(TypedDict, total=False):
    job_id: str
    request: dict[str, Any]
    profile: str
    as_of: str
    lon: float
    lat: float
    neighborhood: str | None
    geocode_ok: bool
    intake_error: str | None
    active_followup: dict[str, Any] | None
    agent_results: Annotated[list[dict[str, Any]], _extend]
    followup_queue: Annotated[list[dict[str, Any]], _extend_unique_followups]
    dispatched_followups: Annotated[list[str], _extend]
    evidence_ids: Annotated[list[str], _extend]
    tool_calls: Annotated[list[dict[str, Any]], _extend]
    dispatches_used: Annotated[int, _add_int]
    claims: list[dict[str, Any]]
    rejected_claims: list[dict[str, Any]]
    rewrite_count: int
    missing_information: list[str]
    uncertainty: list[str]
    conflicts: list[str]
    result_json: dict[str, Any]
    phase: str
