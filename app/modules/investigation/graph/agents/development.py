from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from langgraph.types import RunnableConfig
from sqlalchemy.orm import Session

from app.core.logging import log_extra
from app.core.results import LimitationCode
from app.modules.investigation.graph.followups import (
    CompareAroundEvent,
    ResolvePlanConflict,
    followup_dump,
    followup_identity,
    parse_followup,
)
from app.modules.investigation.graph.intake import as_of_dt
from app.modules.investigation.graph.runtime import GraphRuntime, get_runtime, node_session
from app.modules.investigation.graph.specialist import ToolBudget
from app.modules.investigation.graph.state import RunState
from app.modules.investigation.tools import development as development_tools

_APPROVED_STATUSES = frozenset({"approved", "אושר", "מאושר", "in_force", "תקף", "אושר למתן תוקף"})

logger = logging.getLogger(__name__)


def development_node(state: RunState, config: RunnableConfig) -> dict[str, Any]:
    runtime = get_runtime(config)
    budget = ToolBudget(max_calls=runtime.settings.max_tool_calls, agent="development")
    followup = state.get("active_followup")
    with node_session(runtime) as session:
        if followup:
            findings, queued, conflicts = _handle_followup(
                state, runtime, session, budget, followup
            )
        else:
            findings, queued, conflicts = _first_pass(state, runtime, session, budget)
        dispatched = [followup_identity(followup)] if followup else []
        return {
            "agent_results": [{"agent": "development", "findings": findings}],
            "followup_queue": [followup_dump(item) for item in queued],
            "dispatched_followups": dispatched,
            "conflicts": conflicts,
            "tool_calls": budget.calls,
            "evidence_ids": [
                str(eid) for call in budget.calls for eid in call.get("evidence_ids", [])
            ],
            "dispatches_used": 1,
        }


def _first_pass(
    state: RunState,
    runtime: GraphRuntime,
    session: Session,
    budget: ToolBudget,
) -> tuple[dict[str, Any], list, list[str]]:
    run_id = uuid.UUID(state["job_id"])
    as_of = as_of_dt(state)
    plans_result = _call_plans(state, runtime, session, budget, run_id, as_of)
    histories: list[dict[str, Any]] = []
    for plan in plans_result.plans:
        if budget.remaining() <= 0:
            if len(histories) < len(plans_result.plans):
                logger.warning(
                    "development tool budget exhausted",
                    extra=log_extra(event="investigation.tool_budget", agent="development"),
                )
            break
        history = _call_history(state, runtime, session, budget, run_id, as_of, plan["plan_id"])
        histories.append({"plan_id": plan["plan_id"], "events": history.events})
    if budget.remaining() > 0:
        renewals = _call_renewals(state, runtime, session, budget, run_id, as_of)
        renewal_rows = renewals.renewals
        renewal_coverage = renewals.coverage_status
        renewal_limitation = renewals.limitation
    else:
        logger.warning(
            "development tool budget exhausted",
            extra=log_extra(event="investigation.tool_budget", agent="development"),
        )
        renewal_rows = []
        renewal_coverage = None
        renewal_limitation = {
            "code": LimitationCode.TOOL_BUDGET_EXHAUSTED,
            "message": "Tool budget exhausted before renewal lookup.",
        }

    findings = {
        "plans": plans_result.plans,
        "histories": histories,
        "renewals": renewal_rows,
        "plans_coverage_status": plans_result.coverage_status,
        "plans_limitation": plans_result.limitation,
        "renewal_coverage_status": renewal_coverage,
        "renewal_limitation": renewal_limitation,
    }
    queued: list = []
    conflicts: list[str] = []
    statuses = {str(plan.get("status")) for plan in plans_result.plans if plan.get("status")}
    if len(plans_result.plans) >= 2 and len(statuses) >= 2:
        plan_ids = [str(plan["plan_id"]) for plan in plans_result.plans]
        queued.append(
            ResolvePlanConflict(
                plan_ids=plan_ids,
                reason="plan sources disagree on status at the subject point",
            )
        )
    for row in renewal_rows:
        status = str(row.get("snapshot_status") or "").lower()
        if status in {s.lower() for s in _APPROVED_STATUSES}:
            event_raw = row.get("effective_at")
            event_at = datetime.fromisoformat(event_raw) if event_raw else as_of
            queued.append(
                CompareAroundEvent(
                    event_at=event_at,
                    reason="approved or documented renewal polygon near the subject",
                )
            )
            break
    return findings, queued, conflicts


def _handle_followup(
    state: RunState,
    runtime: GraphRuntime,
    session: Session,
    budget: ToolBudget,
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list, list[str]]:
    item = parse_followup(raw)
    if isinstance(item, ResolvePlanConflict):
        run_id = uuid.UUID(state["job_id"])
        as_of = as_of_dt(state)
        events_by_plan: list[dict[str, Any]] = []
        for plan_id in item.plan_ids:
            if budget.remaining() <= 0:
                break
            history = _call_history(state, runtime, session, budget, run_id, as_of, plan_id)
            events_by_plan.append({"plan_id": plan_id, "events": history.events})
        conflict = (
            item.reason or "Municipal and iplan statuses disagree; both retained as a conflict."
        )
        return (
            {"resolved_conflict": events_by_plan},
            [],
            [conflict],
        )
    return {}, [], []


def _call_plans(state, runtime, session, budget, run_id, as_of):
    params = {"lon": state["lon"], "lat": state["lat"]}
    record = budget.record("plans_at_location", params)
    result = development_tools.plans_at_location(
        session,
        runtime.http,
        run_id=run_id,
        lon=float(state["lon"]),
        lat=float(state["lat"]),
        as_of=as_of,
    )
    record["evidence_ids"] = [str(eid) for eid in result.evidence_ids]
    return result


def _call_history(state, runtime, session, budget, run_id, as_of, plan_id: str):
    params = {"plan_id": plan_id}
    record = budget.record("plan_status_history", params)
    result = development_tools.plan_status_history(
        session,
        runtime.http,
        run_id=run_id,
        plan_id=uuid.UUID(plan_id),
        as_of=as_of,
    )
    record["evidence_ids"] = [str(eid) for eid in result.evidence_ids]
    return result


def _call_renewals(state, runtime, session, budget, run_id, as_of):
    params = {"lon": state["lon"], "lat": state["lat"]}
    record = budget.record("renewal_areas", params)
    result = development_tools.renewal_areas(
        session,
        runtime.http,
        run_id=run_id,
        lon=float(state["lon"]),
        lat=float(state["lat"]),
        as_of=as_of,
    )
    record["evidence_ids"] = [str(eid) for eid in result.evidence_ids]
    return result
