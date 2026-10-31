from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import log_extra
from app.core.point_in_time import compute_available_at
from app.core.results import CoverageStatus, Limitation, LimitationCode, ServiceResult
from app.infrastructure.gis.arcgis import HttpGetClient
from app.infrastructure.gis.coverage_grid import Cell, cells_for_bbox
from app.modules.planning.constants import (
    BBOX_PAD,
    IPLAN_LAG_DAYS,
    IPLAN_SOURCE,
    RENEWAL_LAG_DAYS,
    RENEWAL_SOURCE,
)
from app.modules.planning.coverage import open_window_stale, window_covers
from app.modules.planning.dto import (
    PlanAtPoint,
    PlansAtPointQuery,
    PlanStatusEventRecord,
    RenewalAtPoint,
    RenewalAtPointQuery,
)
from app.modules.planning.providers import iplan, tlv_renewal
from app.modules.planning.repository import (
    get_plan,
    get_planning_coverage_cells,
    list_plans_at_point_as_of,
    list_renewal_polygons_at_point_as_of,
    list_status_events_as_of,
    upsert_plan,
    upsert_plan_status_event,
    upsert_planning_coverage_complete,
    upsert_renewal_polygon,
)

logger = logging.getLogger(__name__)


def _bbox_around(lon: float, lat: float) -> tuple[float, float, float, float]:
    return lon - BBOX_PAD, lat - BBOX_PAD, lon + BBOX_PAD, lat + BBOX_PAD


def _cells_need_planning_fetch(
    session: Session,
    cells: set[Cell],
    *,
    source: str,
    window_start: datetime,
    window_end: datetime,
    lag_days: int,
    now: datetime,
) -> set[Cell]:
    existing = {
        Cell(r.cell_x, r.cell_y): r
        for r in get_planning_coverage_cells(session, source=source, cells=cells)
    }
    missing: set[Cell] = set()
    for cell in cells:
        row = existing.get(cell)
        if row is None or row.status != "complete":
            missing.add(cell)
            continue
        if not window_covers(
            window_start=row.window_start,
            window_end=row.window_end,
            requested_start=window_start,
            requested_end=window_end,
        ):
            missing.add(cell)
            continue
        if open_window_stale(
            window_end=row.window_end,
            lag_days=lag_days,
            now=now,
            requested_end=window_end,
        ):
            missing.add(cell)
    return missing


def _synthesize_status_events(
    session: Session,
    client: HttpGetClient,
    *,
    pl_number: str,
    plan_id,
    retrieved_at: datetime,
) -> None:
    meta = iplan.fetch_plan_metadata(client, pl_number=pl_number)
    if meta is None:
        return
    for field, status in (
        ("depositing_date", "deposited"),
        ("pl_date_advertise", "advertised"),
        ("last_update_date", "updated"),
    ):
        raw = meta.get(field)
        if raw is None:
            continue
        effective = iplan.parse_date(raw)
        if effective is None:
            continue
        available_at, estimated = compute_available_at(
            effective_at=effective,
            published_at=None,
            lag_days=IPLAN_LAG_DAYS,
        )
        upsert_plan_status_event(
            session,
            plan_id=plan_id,
            source=IPLAN_SOURCE,
            status=status,
            effective_at=effective,
            published_at=None,
            retrieved_at=retrieved_at,
            available_at=available_at,
            available_at_estimated=estimated,
        )


def ensure_iplan_loaded(
    session: Session,
    client: HttpGetClient,
    *,
    lon: float,
    lat: float,
    as_of: datetime,
) -> Limitation | None:
    now = datetime.now(tz=UTC)
    minx, miny, maxx, maxy = _bbox_around(lon, lat)
    cells = cells_for_bbox(minx, miny, maxx, maxy)
    window_start = as_of.replace(year=as_of.year - 5)
    window_end = as_of
    missing = _cells_need_planning_fetch(
        session,
        cells,
        source=IPLAN_SOURCE,
        window_start=window_start,
        window_end=window_end,
        lag_days=IPLAN_LAG_DAYS,
        now=now,
    )
    if not missing:
        return None
    logger.info(
        "coverage missing",
        extra=log_extra(event="coverage.missing", source=IPLAN_SOURCE, cell_count=len(missing)),
    )
    started = time.perf_counter()
    try:
        logger.info(
            "ingestion started",
            extra=log_extra(
                event="ingestion.started",
                source=IPLAN_SOURCE,
                cell_count=len(missing),
            ),
        )
        features = iplan.fetch_polygons_in_bbox(client, minx=minx, miny=miny, maxx=maxx, maxy=maxy)
        retrieved_at = now
        for feature in features:
            attrs = feature.get("attributes", {})
            pl_number = attrs.get("pl_number")
            if not pl_number:
                continue
            wkt = iplan.feature_to_wkt(feature)
            if wkt is None:
                continue
            plan_id = upsert_plan(
                session,
                source=IPLAN_SOURCE,
                pl_number=str(pl_number),
                mp_id=str(attrs["mp_id"]) if attrs.get("mp_id") is not None else None,
                name=str(attrs["pl_name"]) if attrs.get("pl_name") is not None else None,
                wkt=wkt,
            )
            _synthesize_status_events(
                session,
                client,
                pl_number=str(pl_number),
                plan_id=plan_id,
                retrieved_at=retrieved_at,
            )
        for cell in missing:
            upsert_planning_coverage_complete(
                session,
                source=IPLAN_SOURCE,
                cell=cell,
                window_start=window_start,
                window_end=window_end,
                updated_at=now,
            )
        session.flush()
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ingestion completed",
            extra=log_extra(
                event="ingestion.completed",
                source=IPLAN_SOURCE,
                record_count=len(features),
                duration_ms=duration_ms,
            ),
        )
        logger.info(
            "coverage completed",
            extra=log_extra(
                event="coverage.completed",
                source=IPLAN_SOURCE,
                cell_count=len(missing),
            ),
        )
        return None
    except Exception as exc:
        logger.exception(
            "ingestion failed",
            extra=log_extra(event="ingestion.failed", source=IPLAN_SOURCE),
        )
        return Limitation(code=LimitationCode.PROVIDER_FAILED, message=str(exc))


def plans_at_point(
    session: Session,
    client: HttpGetClient,
    query: PlansAtPointQuery,
    *,
    settings: Settings | None = None,
) -> ServiceResult[list[PlanAtPoint]]:
    del settings
    limitation = ensure_iplan_loaded(
        session, client, lon=query.lon, lat=query.lat, as_of=query.as_of
    )
    rows = list_plans_at_point_as_of(session, lon=query.lon, lat=query.lat, as_of=query.as_of)
    data = [
        PlanAtPoint(
            plan_id=str(plan.id),
            pl_number=plan.pl_number,
            status=event.status,
            mp_id=plan.mp_id,
            name=plan.name,
        )
        for plan, event in rows
    ]
    if limitation:
        logger.warning(
            "coverage incomplete",
            extra=log_extra(event="coverage.incomplete", source=IPLAN_SOURCE),
        )
        return ServiceResult(
            data=data,
            coverage_status=CoverageStatus.INCOMPLETE,
            limitation=limitation,
        )
    return ServiceResult(data=data, coverage_status=CoverageStatus.COMPLETE)


def plan_status_history(
    session: Session,
    *,
    plan_id: uuid.UUID,
    as_of: datetime,
) -> ServiceResult[list[PlanStatusEventRecord]]:
    plan = get_plan(session, plan_id)
    events = list_status_events_as_of(session, plan_id, as_of)
    data = [
        PlanStatusEventRecord(
            status=event.status,
            effective_at=event.effective_at,
            published_at=event.published_at,
            available_at=event.available_at,
        )
        for event in events
    ]
    if plan is None:
        return ServiceResult(
            data=data,
            coverage_status=CoverageStatus.INCOMPLETE,
            limitation=Limitation(
                code=LimitationCode.COVERAGE_INCOMPLETE,
                message="Plan is not loaded; empty history is not a complete status record",
            ),
        )
    return ServiceResult(data=data, coverage_status=CoverageStatus.COMPLETE)


def ensure_renewal_loaded(
    session: Session,
    client: HttpGetClient,
    *,
    lon: float,
    lat: float,
    as_of: datetime,
) -> Limitation | None:
    now = datetime.now(tz=UTC)
    minx, miny, maxx, maxy = _bbox_around(lon, lat)
    cells = cells_for_bbox(minx, miny, maxx, maxy)
    window_start = as_of.replace(year=as_of.year - 5)
    window_end = as_of
    missing = _cells_need_planning_fetch(
        session,
        cells,
        source=RENEWAL_SOURCE,
        window_start=window_start,
        window_end=window_end,
        lag_days=RENEWAL_LAG_DAYS,
        now=now,
    )
    if not missing:
        return None
    logger.info(
        "coverage missing",
        extra=log_extra(
            event="coverage.missing",
            source=RENEWAL_SOURCE,
            cell_count=len(missing),
        ),
    )
    started = time.perf_counter()
    try:
        logger.info(
            "ingestion started",
            extra=log_extra(
                event="ingestion.started",
                source=RENEWAL_SOURCE,
                cell_count=len(missing),
            ),
        )
        features = tlv_renewal.fetch_renewal_in_bbox(
            client, minx=minx, miny=miny, maxx=maxx, maxy=maxy
        )
        retrieved_at = now
        for feature in features:
            attrs = feature.get("attributes", {})
            feature_id = attrs.get("OBJECTID")
            if feature_id is None:
                continue
            wkt = tlv_renewal.feature_to_wkt(feature)
            if wkt is None:
                continue
            effective = tlv_renewal.snapshot_effective_at(attrs, retrieved_at=retrieved_at)
            available_at, estimated = compute_available_at(
                effective_at=effective,
                published_at=None,
                lag_days=RENEWAL_LAG_DAYS,
            )
            upsert_renewal_polygon(
                session,
                source=RENEWAL_SOURCE,
                source_feature_id=str(feature_id),
                taba=str(attrs["taba"]) if attrs.get("taba") is not None else None,
                snapshot_status=str(attrs["tr_shinuy_status"])
                if attrs.get("tr_shinuy_status") is not None
                else None,
                wkt=wkt,
                effective_at=effective,
                published_at=None,
                retrieved_at=retrieved_at,
                available_at=available_at,
                available_at_estimated=estimated,
                history_available=False,
            )
        for cell in missing:
            upsert_planning_coverage_complete(
                session,
                source=RENEWAL_SOURCE,
                cell=cell,
                window_start=window_start,
                window_end=window_end,
                updated_at=now,
            )
        session.flush()
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ingestion completed",
            extra=log_extra(
                event="ingestion.completed",
                source=RENEWAL_SOURCE,
                record_count=len(features),
                duration_ms=duration_ms,
            ),
        )
        logger.info(
            "coverage completed",
            extra=log_extra(
                event="coverage.completed",
                source=RENEWAL_SOURCE,
                cell_count=len(missing),
            ),
        )
        return None
    except Exception as exc:
        logger.exception(
            "ingestion failed",
            extra=log_extra(event="ingestion.failed", source=RENEWAL_SOURCE),
        )
        return Limitation(code=LimitationCode.PROVIDER_FAILED, message=str(exc))


def renewal_at_point(
    session: Session,
    client: HttpGetClient,
    query: RenewalAtPointQuery,
    *,
    settings: Settings | None = None,
) -> ServiceResult[list[RenewalAtPoint]]:
    del settings
    limitation = ensure_renewal_loaded(
        session, client, lon=query.lon, lat=query.lat, as_of=query.as_of
    )
    rows = list_renewal_polygons_at_point_as_of(
        session, lon=query.lon, lat=query.lat, as_of=query.as_of
    )
    data = [
        RenewalAtPoint(
            renewal_id=str(row.id),
            source_feature_id=row.source_feature_id,
            taba=row.taba,
            snapshot_status=row.snapshot_status,
        )
        for row in rows
    ]
    if limitation:
        logger.warning(
            "coverage incomplete",
            extra=log_extra(event="coverage.incomplete", source=RENEWAL_SOURCE),
        )
        return ServiceResult(
            data=data,
            coverage_status=CoverageStatus.INCOMPLETE,
            limitation=limitation,
        )
    return ServiceResult(data=data, coverage_status=CoverageStatus.COMPLETE)
