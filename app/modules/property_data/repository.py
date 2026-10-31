from __future__ import annotations

from datetime import datetime

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.point_in_time import visible_as_of
from app.modules.property_data.constants import TRANSACTION_SOURCE
from app.modules.property_data.coverage import Cell
from app.modules.property_data.dto import ComparableCandidate, GeocodeRecord, TransactionRecord
from app.modules.property_data.models import (
    GeocodeCache,
    StatisticalArea,
    Transaction,
    TransactionAreaCoverage,
)


def list_transactions_as_of(session: Session, as_of: datetime) -> list[Transaction]:
    stmt = visible_as_of(select(Transaction), as_of)
    return list(session.scalars(stmt).all())


def get_transaction_as_of(
    session: Session,
    *,
    source_row_id: str,
    as_of: datetime,
) -> Transaction | None:
    stmt = visible_as_of(
        select(Transaction).where(
            Transaction.source == TRANSACTION_SOURCE,
            Transaction.source_row_id == source_row_id,
        ),
        as_of,
    )
    return session.scalars(stmt).first()


def get_transaction_record_as_of(
    session: Session,
    *,
    source_row_id: str,
    as_of: datetime,
) -> TransactionRecord | None:
    stmt = visible_as_of(
        select(
            Transaction,
            func.ST_X(Transaction.geom),
            func.ST_Y(Transaction.geom),
        ).where(
            Transaction.source == TRANSACTION_SOURCE,
            Transaction.source_row_id == source_row_id,
        ),
        as_of,
    )
    row = session.execute(stmt).first()
    if row is None:
        return None
    transaction, x, y = row
    return TransactionRecord(
        source_row_id=transaction.source_row_id,
        price_agorot=transaction.price_agorot,
        size_sqm=transaction.size_sqm,
        rooms=transaction.rooms,
        floor=transaction.floor,
        neighborhood=transaction.neighborhood,
        lon=float(x),
        lat=float(y),
        effective_at=transaction.effective_at,
        published_at=transaction.published_at,
    )


def _candidate_from_row(
    row: Transaction,
    *,
    distance_m: float,
    cbs_code: str | None,
    lon: float,
    lat: float,
) -> ComparableCandidate:
    return ComparableCandidate(
        source_row_id=row.source_row_id,
        price_agorot=row.price_agorot,
        size_sqm=row.size_sqm,
        rooms=row.rooms,
        floor=row.floor,
        neighborhood=row.neighborhood,
        lon=lon,
        lat=lat,
        distance_m=distance_m,
        effective_at=row.effective_at,
        available_at=row.available_at,
        statistical_area=cbs_code,
    )


def list_geolocated_transactions_as_of(
    session: Session,
    as_of: datetime,
) -> list[ComparableCandidate]:
    stmt = visible_as_of(
        select(
            Transaction,
            StatisticalArea.cbs_code,
            func.ST_X(Transaction.geom),
            func.ST_Y(Transaction.geom),
        ),
        as_of,
    ).outerjoin(StatisticalArea, func.ST_Contains(StatisticalArea.geom, Transaction.geom))
    return [
        _candidate_from_row(row, distance_m=0.0, cbs_code=cbs_code, lon=float(x), lat=float(y))
        for row, cbs_code, x, y in session.execute(stmt).all()
    ]


def list_nearby_transactions_as_of(
    session: Session,
    *,
    lon: float,
    lat: float,
    radius_m: float,
    as_of: datetime,
) -> list[Transaction]:
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    stmt = visible_as_of(select(Transaction), as_of).where(
        func.ST_DWithin(
            func.ST_Transform(Transaction.geom, 2039),
            func.ST_Transform(point, 2039),
            radius_m,
        )
    )
    return list(session.scalars(stmt).all())


def list_knn_candidates(
    session: Session,
    *,
    lon: float,
    lat: float,
    radius_m: float,
    as_of: datetime,
    limit: int,
) -> list[ComparableCandidate]:
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    point_2039 = func.ST_Transform(point, 2039)
    geom_2039 = func.ST_Transform(Transaction.geom, 2039)
    distance = func.ST_Distance(geom_2039, point_2039)
    stmt = (
        visible_as_of(
            select(
                Transaction,
                distance.label("distance_m"),
                StatisticalArea.cbs_code,
                func.ST_X(Transaction.geom),
                func.ST_Y(Transaction.geom),
            ),
            as_of,
        )
        .outerjoin(StatisticalArea, func.ST_Contains(StatisticalArea.geom, Transaction.geom))
        .where(func.ST_DWithin(geom_2039, point_2039, radius_m))
        .order_by(geom_2039.op("<->")(point_2039))
        .limit(limit)
    )
    return [
        _candidate_from_row(
            row,
            distance_m=float(distance_m),
            cbs_code=cbs_code,
            lon=float(x),
            lat=float(y),
        )
        for row, distance_m, cbs_code, x, y in session.execute(stmt).all()
    ]


def get_geocode(
    session: Session,
    *,
    street: str,
    house_number: str,
) -> GeocodeCache | None:
    stmt = select(GeocodeCache).where(
        GeocodeCache.street == street,
        GeocodeCache.house_number == house_number,
    )
    return session.scalars(stmt).first()


def upsert_geocode(session: Session, record: GeocodeRecord) -> None:
    point = WKTElement(f"POINT({record.lon} {record.lat})", srid=4326)
    stmt = insert(GeocodeCache).values(
        street=record.street,
        house_number=record.house_number,
        lon=record.lon,
        lat=record.lat,
        source=record.source,
        neighborhood=record.neighborhood,
        retrieved_at=record.retrieved_at,
        geom=point,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["street", "house_number"],
        set_={
            "lon": record.lon,
            "lat": record.lat,
            "source": record.source,
            "neighborhood": record.neighborhood,
            "retrieved_at": record.retrieved_at,
            "geom": point,
        },
    )
    session.execute(stmt)


def upsert_transaction(
    session: Session,
    record: TransactionRecord,
    *,
    available_at: datetime,
    available_at_estimated: bool,
    retrieved_at: datetime,
) -> None:
    point = WKTElement(f"POINT({record.lon} {record.lat})", srid=4326)
    stmt = insert(Transaction).values(
        source=TRANSACTION_SOURCE,
        source_row_id=record.source_row_id,
        price_agorot=record.price_agorot,
        size_sqm=record.size_sqm,
        rooms=record.rooms,
        floor=record.floor,
        neighborhood=record.neighborhood,
        geom=point,
        effective_at=record.effective_at,
        published_at=record.published_at,
        retrieved_at=retrieved_at,
        available_at=available_at,
        available_at_estimated=available_at_estimated,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_row_id"],
        set_={
            "price_agorot": record.price_agorot,
            "size_sqm": record.size_sqm,
            "rooms": record.rooms,
            "floor": record.floor,
            "neighborhood": record.neighborhood,
            "geom": point,
            "effective_at": record.effective_at,
            "published_at": record.published_at,
            "retrieved_at": retrieved_at,
            "available_at": available_at,
            "available_at_estimated": available_at_estimated,
        },
    )
    session.execute(stmt)


def get_coverage_cells(
    session: Session,
    *,
    source: str,
    cells: set[Cell],
) -> list[TransactionAreaCoverage]:
    if not cells:
        return []
    stmt = select(TransactionAreaCoverage).where(
        TransactionAreaCoverage.source == source,
        TransactionAreaCoverage.cell_x.in_({c.x for c in cells}),
        TransactionAreaCoverage.cell_y.in_({c.y for c in cells}),
    )
    rows = list(session.scalars(stmt).all())
    cell_set = cells
    return [r for r in rows if Cell(r.cell_x, r.cell_y) in cell_set]


def upsert_coverage_complete(
    session: Session,
    *,
    source: str,
    cell: Cell,
    window_start: datetime,
    window_end: datetime | None,
    updated_at: datetime,
) -> None:
    stmt = insert(TransactionAreaCoverage).values(
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


def upsert_statistical_area(session: Session, *, cbs_code: str, wkt: str) -> None:
    geom = WKTElement(wkt, srid=4326)
    stmt = insert(StatisticalArea).values(cbs_code=cbs_code, geom=geom)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cbs_code"],
        set_={"geom": geom},
    )
    session.execute(stmt)


def get_statistical_area(session: Session, cbs_code: str) -> StatisticalArea | None:
    stmt = select(StatisticalArea).where(StatisticalArea.cbs_code == cbs_code)
    return session.scalars(stmt).first()
