from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.point_in_time import PointInTimeMixin


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("source", "pl_number", name="uq_plans_source_pl_number"),
        Index("ix_plans_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    pl_number: Mapped[str] = mapped_column(String(64), nullable=False)
    mp_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )


class PlanStatusEvent(Base, PointInTimeMixin):
    __tablename__ = "plan_status_events"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "status",
            "effective_at",
            "source",
            name="uq_plan_status_events_natural",
        ),
        Index("ix_plan_status_events_plan_id", "plan_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(128), nullable=False)


class RenewalPolygon(Base, PointInTimeMixin):
    __tablename__ = "renewal_polygons"
    __table_args__ = (
        UniqueConstraint("source", "source_feature_id", name="uq_renewal_polygons_source_feature"),
        Index("ix_renewal_polygons_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_feature_id: Mapped[str] = mapped_column(String(128), nullable=False)
    taba: Mapped[str | None] = mapped_column(String(128), nullable=True)
    snapshot_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    history_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )


class PlanningAreaCoverage(Base):
    __tablename__ = "planning_area_coverage"
    __table_args__ = (
        UniqueConstraint("source", "cell_x", "cell_y", name="uq_planning_coverage_cell"),
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
