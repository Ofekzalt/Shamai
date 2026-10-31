from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSet:
    n: int
    mae_agorot: float
    mape: float
    within_10: float


def size_band(size_sqm: float | None) -> str:
    if size_sqm is None:
        return "unknown"
    if size_sqm < 60:
        return "<60"
    if size_sqm <= 90:
        return "60-90"
    return ">90"


def score(actuals: list[int], preds: list[int]) -> MetricSet:
    if not actuals:
        return MetricSet(n=0, mae_agorot=0.0, mape=0.0, within_10=0.0)
    abs_err = [abs(a - p) for a, p in zip(actuals, preds, strict=True)]
    pct = [e / a for a, e in zip(actuals, abs_err, strict=True) if a > 0]
    within = sum(1 for p in pct if p <= 0.10)
    return MetricSet(
        n=len(actuals),
        mae_agorot=sum(abs_err) / len(abs_err),
        mape=(sum(pct) / len(pct)) if pct else 0.0,
        within_10=(within / len(pct)) if pct else 0.0,
    )


def format_metrics(label: str, metrics: MetricSet) -> str:
    return (
        f"{label}: n={metrics.n} MAE={metrics.mae_agorot:.0f} agorot "
        f"MAPE={metrics.mape:.1%} within_10={metrics.within_10:.1%}"
    )
