from __future__ import annotations

import uuid
from typing import Any

from langgraph.types import RunnableConfig

from app.core.results import LimitationCode
from app.modules.evidence.claims import ObservedClaim, ObservedField
from app.modules.investigation.graph.followups import followup_identity
from app.modules.investigation.graph.runtime import get_runtime
from app.modules.investigation.graph.state import RunState
from app.modules.investigation.tools.market import MIN_COMPS

_LIMITATION_TEXT = {
    str(LimitationCode.COVERAGE_INCOMPLETE): "Source coverage is incomplete for this as-of window.",
    str(LimitationCode.PROVIDER_FAILED): "A data provider failed; results may be incomplete.",
    str(LimitationCode.TOOL_BUDGET_EXHAUSTED): (
        "The agent stopped before running all tools due to the per-dispatch budget."
    ),
}


def _findings(state: RunState, agent: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for row in state.get("agent_results") or []:
        if row.get("agent") == agent and isinstance(row.get("findings"), dict):
            merged.update(row["findings"])
    return merged


def _evidence_for_tool(state: RunState, tool: str) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for call in state.get("tool_calls") or []:
        if call.get("tool") != tool:
            continue
        for raw in call.get("evidence_ids") or []:
            ids.append(uuid.UUID(str(raw)))
    return ids


def _limitation_text(limitation: dict[str, Any]) -> str:
    code = str(limitation.get("code") or "")
    return _LIMITATION_TEXT.get(code, "A data source limitation applies.")


def _rejected_paths(state: RunState) -> set[str]:
    return {
        str(item["path"])
        for item in state.get("rejected_claims") or []
        if isinstance(item, dict) and item.get("path")
    }


def _append_observed(
    claims: list[dict[str, Any]],
    missing: list[str],
    *,
    rejected: set[str],
    path: str,
    text: str,
    evidence_ids: list[uuid.UUID],
    value: object,
) -> None:
    if path in rejected:
        missing.append(f"Dropped unverified claim at {path}.")
        return
    claims.append(
        ObservedClaim(
            text=text,
            evidence_ids=evidence_ids,
            fields=[ObservedField(path=path, value=value)],
        ).model_dump(mode="json")
    )


def writer_node(state: RunState, config: RunnableConfig) -> dict[str, Any]:
    runtime = get_runtime(config)
    if runtime.on_verifying is not None:
        runtime.on_verifying()

    market = _findings(state, "market")
    development = _findings(state, "development")
    request = state.get("request") or {}
    claims: list[dict[str, Any]] = []
    missing: list[str] = []
    uncertainty: list[str] = []
    rejected = _rejected_paths(state)

    n_comps = market.get("n_comps")
    coverage = market.get("coverage_status")
    market_complete = coverage == "complete"
    if coverage and not market_complete:
        missing.append("Transaction coverage is incomplete for this as-of window.")
    limitation = market.get("limitation")
    if isinstance(limitation, dict) and (limitation.get("code") or limitation.get("message")):
        missing.append(_limitation_text(limitation))
    if isinstance(n_comps, int) and n_comps < MIN_COMPS:
        uncertainty.append("Comparable set is thinner than MIN_COMPS; confidence is reduced.")

    comp_ids = _evidence_for_tool(state, "find_comparables")
    estimate = market.get("estimate_agorot")
    if market_complete and estimate is not None and comp_ids:
        _append_observed(
            claims,
            missing,
            rejected=rejected,
            path="estimate.value_agorot",
            text=f"Comparable-sales estimate is {estimate} agorot.",
            evidence_ids=[comp_ids[-1]],
            value=estimate,
        )
    elif n_comps == 0 and market_complete:
        missing.append("No usable comparables were selected; estimate omitted.")
    elif not market_complete:
        missing.append("Comparable coverage is incomplete; estimate omitted.")

    if market_complete and isinstance(n_comps, int) and n_comps > 0 and comp_ids:
        _append_observed(
            claims,
            missing,
            rejected=rejected,
            path="selected_count",
            text=f"Selected comparable count is {n_comps}.",
            evidence_ids=[comp_ids[-1]],
            value=n_comps,
        )

    plan_ids = _evidence_for_tool(state, "plans_at_location")
    plans = development.get("plans") or []
    plans_coverage = development.get("plans_coverage_status")
    if plans_coverage and plans_coverage != "complete":
        missing.append("Plan coverage is incomplete for this as-of window.")
    plans_limitation = development.get("plans_limitation")
    if isinstance(plans_limitation, dict) and (
        plans_limitation.get("code") or plans_limitation.get("message")
    ):
        missing.append(_limitation_text(plans_limitation))
    if plans and plan_ids:
        plan = plans[0]
        _append_observed(
            claims,
            missing,
            rejected=rejected,
            path="plans.0.status",
            text=f"Plan {plan.get('pl_number')} status is {plan.get('status')}.",
            evidence_ids=[plan_ids[-1]],
            value=plan.get("status"),
        )

    renewal_ids = _evidence_for_tool(state, "renewal_areas")
    renewals = development.get("renewals") or []
    renewal_coverage = development.get("renewal_coverage_status")
    if renewal_coverage and renewal_coverage != "complete":
        missing.append("Renewal coverage is incomplete for this as-of window.")
    renewal_limitation = development.get("renewal_limitation")
    if isinstance(renewal_limitation, dict) and (
        renewal_limitation.get("code") or renewal_limitation.get("message")
    ):
        missing.append(_limitation_text(renewal_limitation))
    if renewal_ids and renewals:
        _append_observed(
            claims,
            missing,
            rejected=rejected,
            path="renewal_count",
            text="Subject is inside a renewal polygon.",
            evidence_ids=[renewal_ids[-1]],
            value=len(renewals),
        )
    elif renewal_ids and renewal_coverage == "complete":
        _append_observed(
            claims,
            missing,
            rejected=rejected,
            path="renewal_count",
            text="Subject is not inside a documented renewal polygon.",
            evidence_ids=[renewal_ids[-1]],
            value=0,
        )

    if market.get("compare_around_event"):
        uncertainty.append(
            "Renewal versus nearby prices is an index-adjusted correlation, not a causal effect."
        )

    dispatched = set(state.get("dispatched_followups") or [])
    for item in state.get("followup_queue") or []:
        if followup_identity(item) not in dispatched:
            missing.append(f"Unanswered follow-up: {item.get('type')}.")

    asking = request.get("asking_price_agorot")
    if asking and market_complete and estimate:
        uncertainty.append(
            "Asking price versus estimate is an interpretation over observed values."
        )

    return {
        "claims": claims,
        "missing_information": missing,
        "uncertainty": uncertainty,
        "conflicts": list(state.get("conflicts") or []),
        "phase": "verifying",
    }
