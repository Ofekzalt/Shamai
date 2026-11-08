from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from statistics import median
from typing import Any

from langgraph.types import RunnableConfig
from sqlalchemy.orm import Session

from app.core.logging import log_extra
from app.modules.investigation.graph.followups import (
    CompareAroundEvent,
    ExplainPricePremium,
    followup_dump,
    followup_identity,
    parse_followup,
)
from app.modules.investigation.graph.guardrails import initial_search_window, next_search_window
from app.modules.investigation.graph.intake import as_of_dt
from app.modules.investigation.graph.runtime import GraphRuntime, get_runtime, node_session
from app.modules.investigation.graph.specialist import ToolBudget
from app.modules.investigation.graph.state import RunState
from app.modules.investigation.tools import market as market_tools
from app.modules.investigation.tools.market import MIN_COMPS

logger = logging.getLogger(__name__)

_MARKET_PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "market.md").read_text(
    encoding="utf-8"
)


def market_node(state: RunState, config: RunnableConfig) -> dict[str, Any]:
    runtime = get_runtime(config)
    budget = ToolBudget(max_calls=runtime.settings.max_tool_calls, agent="market")
    followup = state.get("active_followup")
    with node_session(runtime) as session:
        if followup:
            findings, queued = _handle_followup(state, runtime, session, budget, followup)
        else:
            findings, queued = _first_pass(state, runtime, session, budget)
        dispatched = [followup_identity(followup)] if followup else []
        return {
            "agent_results": [{"agent": "market", "findings": findings}],
            "followup_queue": [followup_dump(item) for item in queued],
            "dispatched_followups": dispatched,
            "evidence_ids": [
                str(eid) for call in budget.calls for eid in call.get("evidence_ids", [])
            ],
            "tool_calls": budget.calls,
            "dispatches_used": 1,
        }


def _first_pass(
    state: RunState,
    runtime: GraphRuntime,
    session: Session,
    budget: ToolBudget,
) -> tuple[dict[str, Any], list]:
    request = state.get("request") or {}
    window = initial_search_window()
    last = None
    budget_exhausted = False
    while True:
        if last is not None and budget.remaining() <= 0:
            budget_exhausted = True
            break
        last = _find_comps(state, runtime, session, budget, window)
        nxt = next_search_window(
            n_comps=last.n_comps,
            radius_m=float(window["radius_m"]),
            time_days=int(window["time_days"]),
            size_tol=float(window["size_tol"]),
        )
        if nxt is None:
            break
        if budget.remaining() <= 0:
            budget_exhausted = True
            break
        window = nxt

    if budget_exhausted:
        logger.warning(
            "market tool budget exhausted",
            extra=log_extra(event="investigation.tool_budget", agent="market"),
        )

    assert last is not None
    findings: dict[str, Any] = {
        "n_comps": last.n_comps,
        "estimate_agorot": last.estimate_value_agorot,
        "confidence": last.confidence,
        "coverage_status": last.coverage_status,
        "limitation": last.limitation,
        "comps": last.comps,
        "search": window,
        "widened": window != initial_search_window() or last.n_comps < MIN_COMPS,
    }
    queued: list = []
    outlier_ids = _outlier_ids(last.comps)
    for source_row_id in outlier_ids:
        if budget.remaining() <= 0:
            logger.warning(
                "market tool budget exhausted",
                extra=log_extra(event="investigation.tool_budget", agent="market"),
            )
            break
        detail = _transaction_detail(state, runtime, session, budget, source_row_id)
        action, reason = _outlier_decision(runtime, source_row_id, detail.found)
        findings.setdefault("outlier_inspections", []).append(
            {
                "source_row_id": source_row_id,
                "found": detail.found,
                "action": action,
                "reason": reason,
            }
        )
        queued.append(
            ExplainPricePremium(
                source_row_id=source_row_id,
                reason="outlier comparable relative to selected set",
            )
        )
    asking = request.get("asking_price_agorot")
    if (
        asking
        and last.estimate_value_agorot
        and asking > last.estimate_value_agorot * 1.15
        and last.comps
    ):
        queued.append(
            ExplainPricePremium(
                source_row_id=last.comps[0]["source_row_id"],
                reason="asking price premium versus estimate",
            )
        )
    return findings, queued


def _handle_followup(
    state: RunState,
    runtime: GraphRuntime,
    session: Session,
    budget: ToolBudget,
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list]:
    item = parse_followup(raw)
    if isinstance(item, CompareAroundEvent):
        result = _compare(state, runtime, session, budget, item)
        return (
            {
                "compare_around_event": {
                    "before_count": result.before_count,
                    "after_count": result.after_count,
                    "correlation_not_causation": True,
                    "event_at": item.event_at.isoformat(),
                }
            },
            [],
        )
    if isinstance(item, ExplainPricePremium):
        detail = _transaction_detail(state, runtime, session, budget, item.source_row_id)
        return (
            {
                "premium_inspection": {
                    "source_row_id": item.source_row_id,
                    "found": detail.found,
                    "action": "keep",
                    "reason": item.reason or "inspected sale behind asking premium",
                }
            },
            [],
        )
    return {}, []


def _find_comps(
    state: RunState,
    runtime: GraphRuntime,
    session: Session,
    budget: ToolBudget,
    window: dict[str, float | int],
):
    run_id = uuid.UUID(state["job_id"])
    request = state.get("request") or {}
    as_of = as_of_dt(state)
    params = {
        "lon": state["lon"],
        "lat": state["lat"],
        "as_of": as_of.isoformat(),
        "size_sqm": request.get("size_sqm"),
        "radius_m": window["radius_m"],
        "time_days": window["time_days"],
        "size_tol": window["size_tol"],
    }
    record = budget.record("find_comparables", params)
    result = market_tools.find_comparables(
        session,
        runtime.http,
        run_id=run_id,
        lon=float(state["lon"]),
        lat=float(state["lat"]),
        as_of=as_of,
        size_sqm=float(request["size_sqm"]),
        radius_m=float(window["radius_m"]),
        time_days=int(window["time_days"]),
        size_tol=float(window["size_tol"]),
        floor=request.get("floor"),
        rooms=request.get("rooms"),
    )
    record["evidence_ids"] = [str(eid) for eid in result.evidence_ids]
    return result


def _transaction_detail(
    state: RunState,
    runtime: GraphRuntime,
    session: Session,
    budget: ToolBudget,
    source_row_id: str,
):
    run_id = uuid.UUID(state["job_id"])
    as_of = as_of_dt(state)
    params = {"source_row_id": source_row_id}
    record = budget.record("transaction_detail", params)
    result = market_tools.transaction_detail(
        session,
        runtime.http,
        run_id=run_id,
        source_row_id=source_row_id,
        lon=float(state["lon"]),
        lat=float(state["lat"]),
        as_of=as_of,
    )
    record["evidence_ids"] = [str(eid) for eid in result.evidence_ids]
    return result


def _compare(
    state: RunState,
    runtime: GraphRuntime,
    session: Session,
    budget: ToolBudget,
    item: CompareAroundEvent,
):
    run_id = uuid.UUID(state["job_id"])
    as_of = as_of_dt(state)
    event_at = item.event_at
    if event_at.tzinfo is None:
        event_at = event_at.replace(tzinfo=as_of.tzinfo)
    params = {
        "event_at": event_at.isoformat(),
        "radius_m": item.radius_m,
    }
    record = budget.record("compare_around_event", params)
    result = market_tools.compare_around_event(
        session,
        runtime.http,
        run_id=run_id,
        lon=float(state["lon"]),
        lat=float(state["lat"]),
        as_of=as_of,
        event_at=event_at,
        radius_m=item.radius_m,
    )
    record["evidence_ids"] = [str(eid) for eid in result.evidence_ids]
    return result


def _outlier_ids(comps: list[dict[str, Any]]) -> list[str]:
    prices = [int(row["price_agorot"]) for row in comps if row.get("price_agorot")]
    if len(prices) < 3:
        return []
    ordered = sorted(prices)
    mid = median(ordered)
    if mid <= 0:
        return []
    flagged: list[str] = []
    for row in comps:
        price = int(row.get("price_agorot") or 0)
        if price >= mid * 2.5 or (mid >= price * 2.5 and price > 0):
            flagged.append(str(row["source_row_id"]))
    return flagged


def _outlier_decision(runtime: GraphRuntime, source_row_id: str, found: bool) -> tuple[str, str]:
    fallback = (
        "keep",
        "inspected deviant sale; retained pending stronger evidence to drop",
    )
    if runtime.variant != "llm" or runtime.llm is None:
        return fallback
    try:
        reply = runtime.llm.complete(
            [
                {"role": "system", "content": _MARKET_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Decide keep or drop for this flagged comparable. "
                        'Reply with JSON {"action":"keep"|"drop","reason":"..."}. '
                        f"source_row_id={source_row_id} found={found}"
                    ),
                },
            ]
        )
        payload = json.loads(reply.text)
    except (json.JSONDecodeError, RuntimeError, KeyError, TypeError) as exc:
        logger.warning(
            "market llm fallback",
            extra=log_extra(
                event="investigation.llm_fallback",
                agent="market",
                error_type=type(exc).__name__,
            ),
        )
        return fallback
    action = payload.get("action")
    if action not in {"keep", "drop"}:
        return fallback
    reason = str(payload.get("reason") or fallback[1])
    return str(action), reason
