from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import log_extra
from app.core.point_in_time import compute_available_at
from app.core.results import Limitation, LimitationCode, ServiceResult
from app.infrastructure.gis.arcgis import HttpGetClient
from app.modules.property_data.constants import (
    LOAD_RADIUS_M,
    TRANSACTION_LAG_DAYS,
    TRANSACTION_SOURCE,
)
from app.modules.property_data.coverage import (
    Cell,
    cells_for_radius,
    lon_lat_to_cell,
    open_window_stale,
    window_covers,
)
from app.modules.property_data.providers import transactions as tx_provider
from app.modules.property_data.repository import (
    get_coverage_cells,
    upsert_coverage_complete,
    upsert_transaction,
)

COVERAGE_SOURCE = TRANSACTION_SOURCE
logger = logging.getLogger(__name__)


@dataclass
class LoadOutcome:
    limitation: Limitation | None


def _cells_need_fetch(
    session: Session,
    cells: set[Cell],
    *,
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> set[Cell]:
    rows = get_coverage_cells(session, source=COVERAGE_SOURCE, cells=cells)
    existing = {Cell(r.cell_x, r.cell_y): r for r in rows}
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
            lag_days=TRANSACTION_LAG_DAYS,
            now=now,
            requested_end=window_end,
        ):
            missing.add(cell)
    return missing


def ensure_transactions_loaded(
    session: Session,
    client: HttpGetClient,
    *,
    lon: float,
    lat: float,
    window_start: datetime,
    window_end: datetime,
    settings: Settings,
    radius_m: float = 0.0,
) -> LoadOutcome:
    del settings
    now = datetime.now(tz=UTC)
    cells = cells_for_radius(lon, lat, radius_m) if radius_m > 0 else {lon_lat_to_cell(lon, lat)}
    missing = _cells_need_fetch(
        session,
        cells,
        window_start=window_start,
        window_end=window_end,
        now=now,
    )
    if not missing:
        return LoadOutcome(limitation=None)
    logger.info(
        "coverage missing",
        extra=log_extra(
            event="coverage.missing",
            source=COVERAGE_SOURCE,
            cell_count=len(missing),
        ),
    )
    started = time.perf_counter()
    try:
        logger.info(
            "ingestion started",
            extra=log_extra(
                event="ingestion.started",
                source=COVERAGE_SOURCE,
                cell_count=len(missing),
            ),
        )
        offset = 0
        retrieved_at = now
        total_records = 0
        while True:
            records, _total, last_page = tx_provider.fetch_tlv_window(
                client,
                window_start=window_start,
                window_end=window_end,
                offset=offset,
            )
            logger.debug(
                "ingestion page",
                extra=log_extra(
                    event="ingestion.page",
                    source=COVERAGE_SOURCE,
                    offset=offset,
                    record_count=len(records),
                ),
            )
            for raw in records:
                record = tx_provider.normalize_record(raw)
                if record is None:
                    continue
                available_at, estimated = compute_available_at(
                    effective_at=record.effective_at,
                    published_at=record.published_at,
                    lag_days=TRANSACTION_LAG_DAYS,
                )
                upsert_transaction(
                    session,
                    record,
                    available_at=available_at,
                    available_at_estimated=estimated,
                    retrieved_at=retrieved_at,
                )
                total_records += 1
            if last_page:
                break
            offset += len(records)
        for c in missing:
            upsert_coverage_complete(
                session,
                source=COVERAGE_SOURCE,
                cell=c,
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
                source=COVERAGE_SOURCE,
                record_count=total_records,
                duration_ms=duration_ms,
            ),
        )
        logger.info(
            "coverage completed",
            extra=log_extra(
                event="coverage.completed",
                source=COVERAGE_SOURCE,
                cell_count=len(missing),
            ),
        )
        return LoadOutcome(limitation=None)
    except Exception as exc:
        logger.exception(
            "ingestion failed",
            extra=log_extra(event="ingestion.failed", source=COVERAGE_SOURCE),
        )
        return LoadOutcome(
            limitation=Limitation(
                code=LimitationCode.PROVIDER_FAILED,
                message=str(exc),
            )
        )


def load_transactions_for_point(
    session: Session,
    client: HttpGetClient,
    *,
    lon: float,
    lat: float,
    window_start: datetime,
    window_end: datetime,
    settings: Settings,
    radius_m: float = LOAD_RADIUS_M,
) -> ServiceResult[None]:
    outcome = ensure_transactions_loaded(
        session,
        client,
        lon=lon,
        lat=lat,
        window_start=window_start,
        window_end=window_end,
        settings=settings,
        radius_m=radius_m,
    )
    if outcome.limitation:
        return ServiceResult(data=None, limitation=outcome.limitation)
    return ServiceResult(data=None)
