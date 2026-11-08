from __future__ import annotations

from typing import Any

from app.modules.investigation.graph.state import RunState
from app.modules.reporting.dto import Report


def _findings(state: RunState, agent: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for row in state.get("agent_results") or []:
        if row.get("agent") == agent and isinstance(row.get("findings"), dict):
            merged.update(row["findings"])
    return merged


def finalize_node(state: RunState) -> dict[str, Any]:
    request = state.get("request") or {}
    market = _findings(state, "market")
    development = _findings(state, "development")
    compare = market.get("compare_around_event") or {}
    market_complete = market.get("coverage_status") == "complete"
    n_comps = market.get("n_comps") if market_complete else None
    estimate = market.get("estimate_agorot") if market_complete else None
    if n_comps == 0:
        n_comps = None
        estimate = None
    renewal_complete = development.get("renewal_coverage_status") == "complete"
    renewals = development.get("renewals") or []
    in_renewal = bool(renewals) if renewal_complete else None
    compare_payload = compare if compare.get("correlation_not_causation") else None
    report = Report(
        profile=str(state.get("profile") or request.get("profile") or "homebuyer"),
        address=str(request.get("address") or ""),
        as_of=state.get("as_of"),
        lon=state.get("lon"),
        lat=state.get("lat"),
        asking_price_agorot=request.get("asking_price_agorot"),
        size_sqm=request.get("size_sqm"),
        estimate_agorot=estimate,
        n_comps=n_comps,
        confidence=market.get("confidence") if market_complete else None,
        claims=list(state.get("claims") or []),
        missing_information=list(state.get("missing_information") or []),
        uncertainty=list(state.get("uncertainty") or []),
        conflicts=list(state.get("conflicts") or []),
        in_renewal=in_renewal,
        correlation_not_causation=bool(compare.get("correlation_not_causation")),
        compare_around_event=compare_payload,
    )
    if state.get("intake_error"):
        missing = list(report.missing_information)
        missing.append(str(state["intake_error"]))
        report = report.model_copy(update={"missing_information": missing})
    return {"result_json": report.model_dump(mode="json"), "phase": "done"}
