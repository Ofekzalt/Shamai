from __future__ import annotations

import json
import logging
from typing import Literal

from langgraph.types import RunnableConfig, Send

from app.core.logging import log_extra
from app.modules.investigation.graph.followups import specialist_for
from app.modules.investigation.graph.runtime import get_runtime
from app.modules.investigation.graph.state import RunState
from app.modules.investigation.graph.supervisor_rules import (
    _dispatch_payload,
    next_followup,
    pending_followups,
)
from app.modules.investigation.graph.supervisor_rules import (
    route_supervisor as rules_route_supervisor,
)

logger = logging.getLogger(__name__)


def route_supervisor_llm(state: RunState, config: RunnableConfig) -> list[Send] | Literal["writer"]:
    runtime = get_runtime(config)
    if runtime.llm is None:
        return rules_route_supervisor(state, config)
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
    remaining = pending_followups(state)
    prompt = (
        "Rank remaining follow-ups. Reply with JSON "
        '{"action":"finish"} or {"action":"dispatch","index":0}. '
        "You may not invent new action types.\n"
        f"{json.dumps(remaining, default=str)}"
    )
    try:
        reply = runtime.llm.complete(
            [
                {"role": "system", "content": "You only rank an existing follow-up queue."},
                {"role": "user", "content": prompt},
            ]
        )
        payload = json.loads(reply.text)
    except (json.JSONDecodeError, RuntimeError, KeyError, TypeError) as exc:
        logger.warning(
            "supervisor llm fallback",
            extra=log_extra(
                event="investigation.llm_fallback",
                agent="supervisor",
                error_type=type(exc).__name__,
            ),
        )
        return rules_route_supervisor(state, config)
    if payload.get("action") == "finish":
        return "writer"
    index = int(payload.get("index") or 0)
    if index < 0 or index >= len(remaining):
        chosen = pending
    else:
        chosen = remaining[index]
    target = specialist_for(chosen)
    logger.info(
        "supervisor dispatch",
        extra=log_extra(
            event="investigation.supervisor",
            reason="dispatch",
            target=target,
            followup_type=chosen.get("type"),
        ),
    )
    return [Send(target, _dispatch_payload(state, chosen))]
