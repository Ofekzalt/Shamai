from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.investigation.graph.followups import (
    CompareAroundEvent,
    ExplainPricePremium,
    ResolvePlanConflict,
    followup_identity,
    specialist_for,
)
from app.modules.investigation.graph.guardrails import initial_search_window, next_search_window
from app.modules.investigation.graph.state import _extend_unique_followups
from app.modules.investigation.tools.market import MIN_COMPS, RADIUS_M


def test_resolve_plan_conflict_identity_ignores_plan_id_order() -> None:
    a = ResolvePlanConflict(plan_ids=["b", "a"])
    b = ResolvePlanConflict(plan_ids=["a", "b"])
    assert followup_identity(a) == followup_identity(b)


def test_followup_identity_ignores_reason() -> None:
    a = ExplainPricePremium(source_row_id="x", reason="one")
    b = ExplainPricePremium(source_row_id="x", reason="two")
    assert followup_identity(a) == followup_identity(b)


def test_followup_dedup_reducer() -> None:
    event = CompareAroundEvent(event_at=datetime(2024, 1, 1, tzinfo=UTC), reason="a")
    again = CompareAroundEvent(event_at=datetime(2024, 1, 1, tzinfo=UTC), reason="b")
    merged = _extend_unique_followups(
        [event.model_dump(mode="json")],
        [again.model_dump(mode="json")],
    )
    assert len(merged) == 1


def test_specialist_routing() -> None:
    assert specialist_for(ExplainPricePremium(source_row_id="1")) == "market"
    assert specialist_for({"type": "ResolvePlanConflict", "plan_ids": ["a"]}) == "development"


def test_development_skips_renewals_when_budget_exhausted(monkeypatch) -> None:
    from app.modules.investigation.graph.agents import development as development_agent
    from app.modules.investigation.graph.specialist import ToolBudget

    plan_ids = [str(uuid.uuid4()) for _ in range(8)]

    def fake_plans(_state, _runtime, _session, budget, _run_id, _as_of):
        budget.record("plans_at_location", {})
        return SimpleNamespace(
            plans=[{"plan_id": pid, "status": "approved"} for pid in plan_ids],
            coverage_status="complete",
            limitation=None,
        )

    def fake_history(_state, _runtime, _session, budget, _run_id, _as_of, plan_id):
        budget.record("plan_status_history", {"plan_id": plan_id})
        return SimpleNamespace(events=[])

    called = {"renewals": False}

    def fake_renewals(*_args, **_kwargs):
        called["renewals"] = True
        return SimpleNamespace(renewals=[], coverage_status="complete", limitation=None)

    monkeypatch.setattr(development_agent, "_call_plans", fake_plans)
    monkeypatch.setattr(development_agent, "_call_history", fake_history)
    monkeypatch.setattr(development_agent, "_call_renewals", fake_renewals)
    findings, _, _ = development_agent._first_pass(
        {
            "job_id": str(uuid.uuid4()),
            "lon": 34.78,
            "lat": 32.08,
            "as_of": "2025-01-01T00:00:00+00:00",
        },
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        ToolBudget(max_calls=8, agent="development"),
    )
    assert called["renewals"] is False
    assert findings["renewal_coverage_status"] is None
    assert findings["renewal_limitation"]["code"] == "tool_budget_exhausted"


def test_widen_order_radius_then_time() -> None:
    start = initial_search_window()
    nxt = next_search_window(
        n_comps=0,
        radius_m=float(start["radius_m"]),
        time_days=int(start["time_days"]),
        size_tol=float(start["size_tol"]),
    )
    assert nxt is not None
    assert nxt["radius_m"] == RADIUS_M[1]
    last_radius = next_search_window(
        n_comps=0,
        radius_m=float(RADIUS_M[-1]),
        time_days=int(start["time_days"]),
        size_tol=float(start["size_tol"]),
    )
    assert last_radius is not None
    assert last_radius["radius_m"] == RADIUS_M[-1]
    assert last_radius["time_days"] != start["time_days"]
    assert (
        next_search_window(
            n_comps=MIN_COMPS,
            radius_m=float(start["radius_m"]),
            time_days=int(start["time_days"]),
            size_tol=float(start["size_tol"]),
        )
        is None
    )
