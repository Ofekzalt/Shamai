from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from langgraph.types import RunnableConfig

from app.core.exceptions import AddressNotGeocodedError
from app.core.logging import log_extra
from app.modules.investigation.graph.address import parse_address
from app.modules.investigation.graph.runtime import get_runtime, node_session
from app.modules.investigation.graph.specialist import ToolBudget
from app.modules.investigation.graph.state import RESET, RunState
from app.modules.investigation.tools import geocode as geocode_tool

logger = logging.getLogger(__name__)


def _as_of(request: dict[str, Any], timezone: str) -> datetime:
    raw = request.get("as_of")
    tz = ZoneInfo(timezone)
    if raw:
        parsed = date.fromisoformat(str(raw)[:10])
        return datetime(parsed.year, parsed.month, parsed.day, tzinfo=tz)
    now = datetime.now(tz=tz)
    return datetime(now.year, now.month, now.day, tzinfo=tz)


def intake(state: RunState, config: RunnableConfig) -> dict[str, Any]:
    runtime = get_runtime(config)
    request = state.get("request") or {}
    address = str(request.get("address") or "")
    street, house_number = parse_address(address)
    as_of = _as_of(request, runtime.settings.timezone)
    budget = ToolBudget(max_calls=runtime.settings.max_tool_calls, agent="intake")
    run_id = state["job_id"]

    with node_session(runtime) as session:
        try:
            result = geocode_tool.geocode(
                session,
                runtime.http,
                run_id=uuid.UUID(run_id),
                street=street,
                house_number=house_number,
            )
        except AddressNotGeocodedError as exc:
            logger.warning(
                "intake geocode rejected",
                extra=log_extra(
                    event="investigation.intake_rejected",
                    job_id=run_id,
                ),
            )
            return {
                "geocode_ok": False,
                "intake_error": str(exc),
                "profile": request.get("profile"),
                "as_of": as_of.isoformat(),
                "agent_results": [RESET],
                "followup_queue": [RESET],
                "dispatched_followups": [RESET],
                "tool_calls": [RESET],
                "evidence_ids": [RESET],
                "dispatches_used": RESET,
                "rewrite_count": 0,
                "rejected_claims": [],
                "claims": [],
            }
        budget.record("geocode", {"street": street, "house_number": house_number})
        return {
            "profile": request.get("profile"),
            "as_of": as_of.isoformat(),
            "lon": result.lon,
            "lat": result.lat,
            "neighborhood": result.neighborhood,
            "geocode_ok": True,
            "evidence_ids": [RESET, *[str(eid) for eid in result.evidence_ids]],
            "tool_calls": [RESET, *budget.calls],
            "followup_queue": [RESET],
            "dispatched_followups": [RESET],
            "agent_results": [RESET],
            "dispatches_used": RESET,
            "rewrite_count": 0,
            "rejected_claims": [],
            "claims": [],
            "missing_information": [],
            "uncertainty": [],
            "conflicts": [],
        }


def as_of_dt(state: RunState) -> datetime:
    raw = state.get("as_of")
    if not raw:
        return datetime.now(tz=UTC)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
