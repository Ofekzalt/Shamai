from __future__ import annotations

from datetime import UTC, datetime

from app.modules.property_data.providers.transactions import normalize_record


def test_normalize_record_maps_price_and_dates() -> None:
    record = normalize_record(
        {
            "_id": "abc",
            "dealdatetime": "2024-06-01",
            "price": "5000000",
            "lon": 34.78,
            "lat": 32.08,
        }
    )
    assert record is not None
    assert record.source_row_id == "abc"
    assert record.price_agorot == 500_000_000
    assert record.effective_at == datetime(2024, 6, 1, tzinfo=UTC)
