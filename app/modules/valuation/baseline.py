from __future__ import annotations

from statistics import median

from .dto import CompRow, Subject


def _rate(row: CompRow) -> float | None:
    if row.size_sqm is None or row.size_sqm <= 0 or row.price_agorot <= 0:
        return None
    return row.price_agorot / row.size_sqm


def baseline_value(rows: list[CompRow], subject: Subject) -> int:
    visible = [
        row
        for row in rows
        if row.available_at <= subject.as_of
        and (subject.source_row_id is None or row.source_row_id != subject.source_row_id)
    ]
    hood = [
        row for row in visible if subject.neighborhood and row.neighborhood == subject.neighborhood
    ]
    pool = hood or visible
    rates = [rate for row in pool if (rate := _rate(row)) is not None]
    if not rates:
        return 0
    return int(round(median(rates) * subject.size_sqm))
