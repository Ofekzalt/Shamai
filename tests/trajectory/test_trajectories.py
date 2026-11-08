from __future__ import annotations

from app.modules.investigation.tools.market import MIN_COMPS, RADIUS_M, TIME_DAYS
from tests.trajectory.helpers import (
    ORIGIN_LAT,
    ORIGIN_LON,
    request_body,
    run_rules,
    seed_geocode,
    seed_plan,
    seed_renewal,
    seed_transaction,
)


def _tool_names(state: dict) -> list[str]:
    return [call["tool"] for call in state.get("tool_calls") or []]


def _comp_calls(state: dict) -> list[dict]:
    return [call for call in state.get("tool_calls") or [] if call["tool"] == "find_comparables"]


def test_thin_comps_widens_radius(db_session) -> None:
    seed_geocode(db_session)
    for i in range(2):
        seed_transaction(
            db_session,
            source_row_id=f"near-{i}",
            lon=ORIGIN_LON + 0.0003,
            lat=ORIGIN_LAT,
            price_agorot=4_000_000_00,
        )
    for i in range(2):
        seed_transaction(
            db_session,
            source_row_id=f"far-{i}",
            lon=ORIGIN_LON + 0.012,
            lat=ORIGIN_LAT,
            price_agorot=4_000_000_00,
        )
    db_session.flush()
    state = run_rules(db_session, request_body())
    radii = [call["params"]["radius_m"] for call in _comp_calls(state)]
    times = [call["params"]["time_days"] for call in _comp_calls(state)]
    sizes = [call["params"]["size_tol"] for call in _comp_calls(state)]
    assert radii[0] == RADIUS_M[0]
    assert any(radius > RADIUS_M[0] for radius in radii)
    assert any(days > TIME_DAYS[0] for days in times) or any(size > sizes[0] for size in sizes)
    market = next(row["findings"] for row in state["agent_results"] if row["agent"] == "market")
    assert market["n_comps"] < MIN_COMPS
    assert market["confidence"] == "thin"
    assert "stub" not in (state.get("result_json") or {})


def test_outlier_comp_inspects_transaction_detail(db_session) -> None:
    seed_geocode(db_session)
    for i in range(5):
        seed_transaction(
            db_session,
            source_row_id=f"base-{i}",
            lon=ORIGIN_LON + 0.0002,
            lat=ORIGIN_LAT,
            price_agorot=4_000_000_00,
        )
    seed_transaction(
        db_session,
        source_row_id="outlier",
        lon=ORIGIN_LON + 0.0002,
        lat=ORIGIN_LAT,
        price_agorot=20_000_000_00,
    )
    db_session.flush()
    state = run_rules(db_session, request_body(asking_price_agorot=4_100_000_00))
    assert "transaction_detail" in _tool_names(state)
    detail = next(call for call in state["tool_calls"] if call["tool"] == "transaction_detail")
    assert detail["params"]["source_row_id"] == "outlier"
    market = next(row["findings"] for row in state["agent_results"] if row["agent"] == "market")
    inspections = market.get("outlier_inspections") or []
    assert inspections
    assert inspections[0]["reason"]


def test_plan_conflict_queues_resolve(db_session) -> None:
    seed_geocode(db_session)
    for i in range(5):
        seed_transaction(
            db_session,
            source_row_id=f"c-{i}",
            lon=ORIGIN_LON + 0.0002,
            lat=ORIGIN_LAT,
            price_agorot=4_000_000_00,
        )
    seed_plan(db_session, pl_number="P-1", status="approved", source="iplan")
    seed_plan(db_session, pl_number="P-2", status="deposited", source="municipal")
    db_session.flush()
    state = run_rules(db_session, request_body(asking_price_agorot=4_000_000_00))
    types = [item.get("type") for item in state.get("followup_queue") or []]
    assert "ResolvePlanConflict" in types
    assert "plan_status_history" in _tool_names(state)
    assert state.get("conflicts") or any(
        "conflict" in item.lower() for item in state.get("result_json", {}).get("conflicts", [])
    )


def test_renewal_followup_compare_around_event(db_session) -> None:
    seed_geocode(db_session)
    for i in range(5):
        seed_transaction(
            db_session,
            source_row_id=f"r-{i}",
            lon=ORIGIN_LON + 0.0002,
            lat=ORIGIN_LAT,
            price_agorot=4_000_000_00,
        )
    seed_renewal(db_session, status="approved")
    db_session.flush()
    state = run_rules(
        db_session,
        request_body(profile="investor", asking_price_agorot=4_000_000_00),
    )
    types = [item.get("type") for item in state.get("followup_queue") or []]
    assert "CompareAroundEvent" in types
    assert "compare_around_event" in _tool_names(state)
    report = state["result_json"]
    assert report["correlation_not_causation"] is True
    joined = " ".join(report.get("uncertainty") or []).lower()
    assert "correlation" in joined
    assert "caused" not in joined
