from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.results import CoverageStatus, Limitation, LimitationCode, ServiceResult

__all__ = [
    "CoverageStatus",
    "GeocodeRecord",
    "Limitation",
    "LimitationCode",
    "NearbyTransactionsQuery",
    "ServiceResult",
    "TransactionRecord",
]


class GeocodeRecord(BaseModel):
    street: str
    house_number: str
    lon: float
    lat: float
    source: str
    retrieved_at: datetime
    neighborhood: str | None = None


class TransactionRecord(BaseModel):
    source_row_id: str
    price_agorot: int
    size_sqm: float | None
    rooms: float | None
    floor: int | None
    neighborhood: str | None
    lon: float
    lat: float
    effective_at: datetime
    published_at: datetime | None = None


class NearbyTransactionsQuery(BaseModel):
    lon: float
    lat: float
    radius_m: float = Field(default=500.0, gt=0)
    as_of: datetime
