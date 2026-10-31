from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.modules.valuation.baseline import baseline_value
from app.modules.valuation.dto import CompRow, IndexPoint, Subject
from app.modules.valuation.estimate import estimate_value
from app.modules.valuation.price_index import time_factor

CalculationFn = Callable[[dict[str, Any]], int | float]

_REGISTRY: dict[str, CalculationFn] = {}


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _comp_row(data: dict[str, Any]) -> CompRow:
    return CompRow(
        source_row_id=data["source_row_id"],
        price_agorot=int(data["price_agorot"]),
        size_sqm=data.get("size_sqm"),
        floor=data.get("floor"),
        rooms=data.get("rooms"),
        lon=float(data["lon"]),
        lat=float(data["lat"]),
        distance_m=float(data["distance_m"]),
        effective_at=_parse_dt(data["effective_at"]),
        available_at=_parse_dt(data["available_at"]),
        neighborhood=data.get("neighborhood"),
        statistical_area=data.get("statistical_area"),
    )


def _subject(data: dict[str, Any]) -> Subject:
    return Subject(
        lon=float(data["lon"]),
        lat=float(data["lat"]),
        size_sqm=float(data["size_sqm"]),
        as_of=_parse_dt(data["as_of"]),
        floor=data.get("floor"),
        rooms=data.get("rooms"),
        neighborhood=data.get("neighborhood"),
        source_row_id=data.get("source_row_id"),
    )


def _index_point(data: dict[str, Any]) -> IndexPoint:
    return IndexPoint(
        period_end=_parse_dt(data["period_end"]),
        nis_per_sqm=float(data["nis_per_sqm"]),
        statistical_area=data["statistical_area"],
    )


def _run_estimate_value(inputs: dict[str, Any]) -> int:
    rows = [_comp_row(item) for item in inputs["rows"]]
    subject = _subject(inputs["subject"])
    index_points = [_index_point(item) for item in inputs.get("index_points", [])]
    return estimate_value(
        rows,
        subject,
        index_points=index_points,
        widen=bool(inputs.get("widen", True)),
        radius_m=inputs.get("radius_m"),
    ).value_agorot


def _run_time_factor(inputs: dict[str, Any]) -> float:
    series = [_index_point(item) for item in inputs["index_points"]]
    factor, _ok = time_factor(
        series,
        as_of=_parse_dt(inputs["as_of"]),
        sale_at=_parse_dt(inputs["sale_at"]),
    )
    return factor


def _run_baseline_value(inputs: dict[str, Any]) -> int:
    rows = [_comp_row(item) for item in inputs["rows"]]
    subject = _subject(inputs["subject"])
    return baseline_value(rows, subject)


_REGISTRY["estimate_value"] = _run_estimate_value
_REGISTRY["time_factor"] = _run_time_factor
_REGISTRY["baseline_value"] = _run_baseline_value


def run_calculation(name: str, inputs: dict[str, Any]) -> int | float:
    fn = _REGISTRY.get(name)
    if fn is None:
        raise KeyError(name)
    return fn(inputs)


def registered_functions() -> frozenset[str]:
    return frozenset(_REGISTRY)
