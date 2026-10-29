from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.point_in_time import visible_as_of
from app.modules.property_data.models import GeocodeCache, StatisticalArea, Transaction


def list_transactions_as_of(session: Session, as_of: datetime) -> list[Transaction]:
    stmt = visible_as_of(select(Transaction), as_of)
    return list(session.scalars(stmt).all())


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


def get_statistical_area(session: Session, cbs_code: str) -> StatisticalArea | None:
    stmt = select(StatisticalArea).where(StatisticalArea.cbs_code == cbs_code)
    return session.scalars(stmt).first()
