from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.point_in_time import compute_available_at
from app.core.results import Limitation, LimitationCode, ServiceResult
from app.infrastructure.gis.arcgis import HttpGetClient
from app.modules.property_data.constants import TRANSACTION_LAG_DAYS, TRANSACTION_SOURCE
from app.modules.property_data.coverage import (
    Cell,
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
        if open_window_stale(window_end=row.window_end, lag_days=TRANSACTION_LAG_DAYS, now=now):
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
) -> LoadOutcome:
    del settings
    now = datetime.now(tz=UTC)
    cell = lon_lat_to_cell(lon, lat)
    cells = {cell}
    missing = _cells_need_fetch(
        session,
        cells,
        window_start=window_start,
        window_end=window_end,
        now=now,
    )
    if not missing:
        return LoadOutcome(limitation=None)
    try:
        offset = 0
        retrieved_at = now
        while True:
            records, _total, last_page = tx_provider.fetch_tlv_window(
                client,
                window_start=window_start,
                window_end=window_end,
                offset=offset,
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
        return LoadOutcome(limitation=None)
    except Exception as exc:
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
) -> ServiceResult[None]:
    outcome = ensure_transactions_loaded(
        session,
        client,
        lon=lon,
        lat=lat,
        window_start=window_start,
        window_end=window_end,
        settings=settings,
    )
    if outcome.limitation:
        return ServiceResult(data=None, limitation=outcome.limitation)
    return ServiceResult(data=None)
