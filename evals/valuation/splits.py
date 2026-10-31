from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.property_data.dto import ComparableCandidate

HOLDOUT_DAYS = 365


def temporal_holdout(
    sales: list[ComparableCandidate],
    *,
    as_of: datetime,
    holdout_days: int = HOLDOUT_DAYS,
) -> tuple[list[ComparableCandidate], list[ComparableCandidate]]:
    cut = as_of - timedelta(days=holdout_days)
    train = [row for row in sales if row.available_at <= cut]
    test = [row for row in sales if cut < row.available_at <= as_of]
    return train, test
