from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.point_in_time import PointInTimeMixin


class Transaction(Base, PointInTimeMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("source", "source_row_id", name="uq_transactions_source_row"),
        Index("ix_transactions_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    price_agorot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    size_sqm: Mapped[float | None] = mapped_column(nullable=True)
    rooms: Mapped[float | None] = mapped_column(nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )


class GeocodeCache(Base):
    __tablename__ = "geocode_cache"
    __table_args__ = (UniqueConstraint("street", "house_number", name="uq_geocode_street_house"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    street: Mapped[str] = mapped_column(String(256), nullable=False)
    house_number: Mapped[str] = mapped_column(String(32), nullable=False)
    lon: Mapped[float] = mapped_column(nullable=False)
    lat: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    neighborhood: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )


class StatisticalArea(Base):
    __tablename__ = "statistical_areas"
    __table_args__ = (
        UniqueConstraint("cbs_code", name="uq_statistical_areas_cbs_code"),
        Index("ix_statistical_areas_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cbs_code: Mapped[str] = mapped_column(String(32), nullable=False)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )


class TransactionAreaCoverage(Base):
    __tablename__ = "transaction_area_coverage"
    __table_args__ = (
        UniqueConstraint("source", "cell_x", "cell_y", name="uq_transaction_coverage_cell"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    cell_x: Mapped[int] = mapped_column(Integer, nullable=False)
    cell_y: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    lease_holder: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
