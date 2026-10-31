from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Select
from sqlalchemy.orm import Mapped, mapped_column


class PointInTimeMixin:
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    available_at_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


def _mapped_class(entity: Any) -> type[Any]:
    if isinstance(entity, type):
        return entity
    return entity.class_


def visible_as_of[T](stmt: Select[tuple[T]], as_of: datetime) -> Select[tuple[T]]:
    entity = stmt.column_descriptions[0]["entity"]
    mapped = _mapped_class(entity)
    return stmt.where(mapped.available_at <= as_of)


def compute_available_at(
    *,
    effective_at: datetime,
    published_at: datetime | None,
    lag_days: int,
) -> tuple[datetime, bool]:
    if published_at is not None:
        return published_at, False
    return effective_at + timedelta(days=lag_days), True
