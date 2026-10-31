from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import WKTElement
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.point_in_time import visible_as_of
from app.modules.planning.coverage import Cell
from app.modules.planning.models import Plan, PlanningAreaCoverage, PlanStatusEvent, RenewalPolygon


def list_status_events_as_of(
    session: Session,
    plan_id: uuid.UUID,
    as_of: datetime,
) -> list[PlanStatusEvent]:
    stmt = visible_as_of(
        select(PlanStatusEvent).where(PlanStatusEvent.plan_id == plan_id),
        as_of,
    )
    return list(session.scalars(stmt).all())


def upsert_plan(
    session: Session,
    *,
    source: str,
    pl_number: str,
    mp_id: str | None,
    name: str | None,
    wkt: str,
) -> uuid.UUID:
    geom = WKTElement(wkt, srid=4326)
    existing_id = session.scalar(
        select(Plan.id).where(Plan.source == source, Plan.pl_number == pl_number)
    )
    if existing_id is not None:
        session.execute(
            update(Plan).where(Plan.id == existing_id).values(mp_id=mp_id, name=name, geom=geom)
        )
        return existing_id
    plan = Plan(source=source, pl_number=pl_number, mp_id=mp_id, name=name, geom=geom)
    session.add(plan)
    session.flush()
    return plan.id


def upsert_plan_status_event(
    session: Session,
    *,
    plan_id: uuid.UUID,
    source: str,
    status: str,
    effective_at: datetime,
    published_at: datetime | None,
    retrieved_at: datetime,
    available_at: datetime,
    available_at_estimated: bool,
) -> None:
    stmt = insert(PlanStatusEvent).values(
        plan_id=plan_id,
        source=source,
        status=status,
        effective_at=effective_at,
        published_at=published_at,
        retrieved_at=retrieved_at,
        available_at=available_at,
        available_at_estimated=available_at_estimated,
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["plan_id", "status", "effective_at", "source"],
    )
    session.execute(stmt)


def list_plans_at_point_as_of(
    session: Session,
    *,
    lon: float,
    lat: float,
    as_of: datetime,
) -> list[tuple[Plan, PlanStatusEvent]]:
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    stmt = (
        select(Plan, PlanStatusEvent)
        .join(PlanStatusEvent, PlanStatusEvent.plan_id == Plan.id)
        .where(func.ST_Intersects(Plan.geom, point))
        .where(PlanStatusEvent.available_at <= as_of)
    )
    rows = list(session.execute(stmt).all())
    latest: dict[uuid.UUID, tuple[Plan, PlanStatusEvent]] = {}
    for plan, event in rows:
        prev = latest.get(plan.id)
        if prev is None or event.effective_at > prev[1].effective_at:
            latest[plan.id] = (plan, event)
    return list(latest.values())


def upsert_renewal_polygon(
    session: Session,
    *,
    source: str,
    source_feature_id: str,
    taba: str | None,
    snapshot_status: str | None,
    wkt: str,
    effective_at: datetime,
    published_at: datetime | None,
    retrieved_at: datetime,
    available_at: datetime,
    available_at_estimated: bool,
    history_available: bool,
) -> None:
    geom = WKTElement(wkt, srid=4326)
    stmt = insert(RenewalPolygon).values(
        source=source,
        source_feature_id=source_feature_id,
        taba=taba,
        snapshot_status=snapshot_status,
        history_available=history_available,
        geom=geom,
        effective_at=effective_at,
        published_at=published_at,
        retrieved_at=retrieved_at,
        available_at=available_at,
        available_at_estimated=available_at_estimated,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_feature_id"],
        set_={
            "taba": taba,
            "snapshot_status": snapshot_status,
            "geom": geom,
            "retrieved_at": retrieved_at,
            "history_available": history_available,
        },
    )
    session.execute(stmt)


def list_renewal_polygons_at_point_as_of(
    session: Session,
    *,
    lon: float,
    lat: float,
    as_of: datetime,
) -> list[RenewalPolygon]:
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    stmt = visible_as_of(select(RenewalPolygon), as_of).where(
        func.ST_Intersects(RenewalPolygon.geom, point)
    )
    return list(session.scalars(stmt).all())


def get_planning_coverage_cells(
    session: Session,
    *,
    source: str,
    cells: set[Cell],
) -> list[PlanningAreaCoverage]:
    if not cells:
        return []
    stmt = select(PlanningAreaCoverage).where(
        PlanningAreaCoverage.source == source,
        PlanningAreaCoverage.cell_x.in_({c.x for c in cells}),
        PlanningAreaCoverage.cell_y.in_({c.y for c in cells}),
    )
    rows = list(session.scalars(stmt).all())
    return [r for r in rows if Cell(r.cell_x, r.cell_y) in cells]


def upsert_planning_coverage_complete(
    session: Session,
    *,
    source: str,
    cell: Cell,
    window_start: datetime,
    window_end: datetime | None,
    updated_at: datetime,
) -> None:
    stmt = insert(PlanningAreaCoverage).values(
        source=source,
        cell_x=cell.x,
        cell_y=cell.y,
        window_start=window_start,
        window_end=window_end,
        status="complete",
        lease_holder=None,
        lease_expires_at=None,
        updated_at=updated_at,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "cell_x", "cell_y"],
        set_={
            "window_start": window_start,
            "window_end": window_end,
            "status": "complete",
            "updated_at": updated_at,
        },
    )
    session.execute(stmt)
