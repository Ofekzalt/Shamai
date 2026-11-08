from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.types import RunnableConfig, Send

from app.core.logging import log_extra
from app.modules.investigation.graph.followups import followup_identity, specialist_for
from app.modules.investigation.graph.runtime import get_runtime
from app.modules.investigation.graph.state import RunState

logger = logging.getLogger(__name__)


def _dispatch_payload(state: RunState, followup: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "job_id": state.get("job_id"),
        "request": state.get("request"),
        "profile": state.get("profile"),
        "as_of": state.get("as_of"),
        "lon": state.get("lon"),
        "lat": state.get("lat"),
        "neighborhood": state.get("neighborhood"),
        "active_followup": followup,
    }


def route_after_intake(state: RunState) -> list[Send] | str:
    if not state.get("geocode_ok"):
        return "finalize"
    return [
        Send("market", _dispatch_payload(state, None)),
        Send("development", _dispatch_payload(state, None)),
    ]


def next_followup(state: RunState) -> dict[str, Any] | None:
    dispatched = set(state.get("dispatched_followups") or [])
    for item in state.get("followup_queue") or []:
        key = followup_identity(item)
        if key not in dispatched:
            return item
    return None


def route_supervisor(state: RunState, config: RunnableConfig) -> list[Send] | Literal["writer"]:
    runtime = get_runtime(config)
    used = int(state.get("dispatches_used") or 0)
    if used >= runtime.settings.max_dispatches:
        logger.info(
            "supervisor stopped dispatches",
            extra=log_extra(event="investigation.supervisor", reason="budget"),
        )
        return "writer"
    pending = next_followup(state)
    if pending is None:
        return "writer"
    target = specialist_for(pending)
    logger.info(
        "supervisor dispatch",
        extra=log_extra(
            event="investigation.supervisor",
            reason="dispatch",
            target=target,
            followup_type=pending.get("type"),
        ),
    )
    return [Send(target, _dispatch_payload(state, pending))]


def pending_followups(state: RunState) -> list[dict[str, Any]]:
    dispatched = set(state.get("dispatched_followups") or [])
    out: list[dict[str, Any]] = []
    for item in state.get("followup_queue") or []:
        if followup_identity(item) not in dispatched:
            out.append(item)
    return out
