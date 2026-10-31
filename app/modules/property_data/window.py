from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.property_data.constants import LOAD_LOOKBACK_DAYS


def transaction_window_start(as_of: datetime) -> datetime:
    return as_of - timedelta(days=LOAD_LOOKBACK_DAYS)
