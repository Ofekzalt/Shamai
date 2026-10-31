from __future__ import annotations

import logging
import sys
from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.logging import configure_logging, log_extra
from app.modules.property_data.repository import (
    list_geolocated_transactions_as_of,
    list_knn_candidates,
)
from app.modules.valuation.baseline import baseline_value
from app.modules.valuation.constants import KNN_FETCH, RADIUS_M
from app.modules.valuation.dto import CompRow, Subject
from app.modules.valuation.estimate import estimate_value
from app.modules.valuation.price_index import build_index
from evals.valuation.metrics import MetricSet, format_metrics, score, size_band
from evals.valuation.splits import temporal_holdout

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _to_comp(row, *, distance_m: float | None = None) -> CompRow:
    return CompRow(
        source_row_id=row.source_row_id,
        price_agorot=row.price_agorot,
        size_sqm=row.size_sqm,
        floor=row.floor,
        rooms=row.rooms,
        lon=row.lon,
        lat=row.lat,
        distance_m=row.distance_m if distance_m is None else distance_m,
        effective_at=row.effective_at,
        available_at=row.available_at,
        neighborhood=row.neighborhood,
        statistical_area=row.statistical_area,
    )


def _exclude_subject(rows: list[CompRow], source_row_id: str) -> list[CompRow]:
    return [row for row in rows if row.source_row_id != source_row_id]


def _print_segments(title: str, groups: dict[str, tuple[list[int], list[int]]]) -> None:
    print(title)
    for name, (actuals, preds) in sorted(groups.items()):
        print("  " + format_metrics(name, score(actuals, preds)))


def run(*, now: datetime | None = None, session: Session | None = None) -> int:
    as_of = now or datetime.now(tz=UTC)
    if session is not None:
        return _run_with_session(session, as_of=as_of)
    session_factory = get_session_factory()
    with session_factory() as owned:
        return _run_with_session(owned, as_of=as_of)


def _run_with_session(session: Session, *, as_of: datetime) -> int:
    sales = list_geolocated_transactions_as_of(session, as_of)
    if not sales:
        logger.warning(
            "valuation insufficient comps",
            extra=log_extra(event="valuation.insufficient_comps", record_count=0),
        )
        print("no transactions loaded; run a property_data load first", file=sys.stderr)
        return 1
    _, test = temporal_holdout(sales, as_of=as_of)
    if not test:
        logger.warning(
            "valuation insufficient comps",
            extra=log_extra(event="valuation.insufficient_comps", record_count=0),
        )
        print("no holdout sales in the last year", file=sys.stderr)
        return 1
    engine_actuals: list[int] = []
    engine_preds: list[int] = []
    base_preds: list[int] = []
    by_hood: dict[str, tuple[list[int], list[int]]] = defaultdict(lambda: ([], []))
    by_size: dict[str, tuple[list[int], list[int]]] = defaultdict(lambda: ([], []))
    base_hood: dict[str, tuple[list[int], list[int]]] = defaultdict(lambda: ([], []))
    base_size: dict[str, tuple[list[int], list[int]]] = defaultdict(lambda: ([], []))
    for sale in test:
        if sale.size_sqm is None or sale.size_sqm <= 0:
            continue
        subject = Subject(
            lon=sale.lon,
            lat=sale.lat,
            size_sqm=sale.size_sqm,
            floor=sale.floor,
            rooms=sale.rooms,
            as_of=sale.available_at,
            neighborhood=sale.neighborhood,
            source_row_id=sale.source_row_id,
        )
        knn_rows = [
            _to_comp(c)
            for c in list_knn_candidates(
                session,
                lon=sale.lon,
                lat=sale.lat,
                radius_m=RADIUS_M[-1],
                as_of=sale.available_at,
                limit=KNN_FETCH,
            )
        ]
        universe = [
            _to_comp(r, distance_m=0.0)
            for r in list_geolocated_transactions_as_of(session, sale.available_at)
        ]
        universe = _exclude_subject(universe, sale.source_row_id)
        area = sale.statistical_area or ""
        index = (
            build_index(universe, as_of=sale.available_at, statistical_area=area) if area else []
        )
        estimate = estimate_value(knn_rows, subject, index_points=index)
        baseline = baseline_value(universe, subject)
        if estimate.n_comps == 0 or estimate.value_agorot <= 0 or baseline <= 0:
            continue
        engine_actuals.append(sale.price_agorot)
        engine_preds.append(estimate.value_agorot)
        base_preds.append(baseline)
        hood = sale.neighborhood or "unknown"
        band = size_band(sale.size_sqm)
        by_hood[hood][0].append(sale.price_agorot)
        by_hood[hood][1].append(estimate.value_agorot)
        by_size[band][0].append(sale.price_agorot)
        by_size[band][1].append(estimate.value_agorot)
        base_hood[hood][0].append(sale.price_agorot)
        base_hood[hood][1].append(baseline)
        base_size[band][0].append(sale.price_agorot)
        base_size[band][1].append(baseline)
    if not engine_actuals:
        logger.warning(
            "valuation insufficient comps",
            extra=log_extra(event="valuation.insufficient_comps", record_count=len(test)),
        )
        print("holdout produced no scorable estimates", file=sys.stderr)
        return 1
    engine: MetricSet = score(engine_actuals, engine_preds)
    baseline_metrics = score(engine_actuals, base_preds)
    print(format_metrics("comps", engine))
    print(format_metrics("baseline", baseline_metrics))
    _print_segments("comps by neighborhood", by_hood)
    _print_segments("baseline by neighborhood", base_hood)
    _print_segments("comps by size", by_size)
    _print_segments("baseline by size", base_size)
    logger.info(
        "valuation completed",
        extra=log_extra(event="valuation.completed", record_count=len(engine_actuals)),
    )
    return 0


def main() -> int:
    configure_logging(get_settings().log_level)
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
