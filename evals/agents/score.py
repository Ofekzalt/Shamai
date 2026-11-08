from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evals.agents.expected import PropertyExpectation

SUPPORTED_VERIFY = frozenset({"pass", "qualified"})


@dataclass
class PropertyScore:
    property_id: str
    skipped: bool = False
    skip_reason: str | None = None
    factual_checks: int = 0
    factual_pass: int = 0
    claims_total: int = 0
    claims_supported: int = 0
    completeness_checks: int = 0
    completeness_pass: int = 0
    followups_triggered: int = 0
    latency_ms: int = 0


@dataclass
class VariantScore:
    variant: str
    properties: list[PropertyScore] = field(default_factory=list)
    cost_usd: float = 0.0

    @property
    def evaluated(self) -> list[PropertyScore]:
        return [row for row in self.properties if not row.skipped]

    def accuracy_rate(self) -> float:
        rows = self.evaluated
        if not rows:
            return 0.0
        checks = sum(row.factual_checks for row in rows)
        if checks == 0:
            return 0.0
        return sum(row.factual_pass for row in rows) / checks

    def claim_support_rate(self) -> float:
        rows = self.evaluated
        if not rows:
            return 0.0
        total = sum(row.claims_total for row in rows)
        if total == 0:
            return 0.0
        return sum(row.claims_supported for row in rows) / total

    def completeness_rate(self) -> float:
        rows = self.evaluated
        if not rows:
            return 0.0
        checks = sum(row.completeness_checks for row in rows)
        if checks == 0:
            return 0.0
        return sum(row.completeness_pass for row in rows) / checks

    def followups_total(self) -> int:
        return sum(row.followups_triggered for row in self.evaluated)

    def latency_p50_ms(self) -> int:
        values = sorted(row.latency_ms for row in self.evaluated)
        if not values:
            return 0
        mid = len(values) // 2
        return values[mid]

    def latency_p95_ms(self) -> int:
        values = sorted(row.latency_ms for row in self.evaluated)
        if not values:
            return 0
        idx = min(len(values) - 1, int(len(values) * 0.95))
        return values[idx]


def _coords_close(report: dict[str, Any], expected: PropertyExpectation) -> bool:
    if expected.lon is None or expected.lat is None:
        return False
    lon = report.get("lon")
    lat = report.get("lat")
    if lon is None or lat is None:
        return False
    return abs(float(lon) - expected.lon) < 1e-4 and abs(float(lat) - expected.lat) < 1e-4


def score_property(
    *,
    property_id: str,
    expected: PropertyExpectation,
    report: dict[str, Any] | None,
    followups: list[str],
    latency_ms: int,
    skip_reason: str | None = None,
) -> PropertyScore:
    if skip_reason:
        return PropertyScore(
            property_id=property_id,
            skipped=True,
            skip_reason=skip_reason,
            latency_ms=latency_ms,
        )
    if report is None:
        return PropertyScore(
            property_id=property_id,
            skipped=True,
            skip_reason="no report",
            latency_ms=latency_ms,
        )

    factual_checks = 0
    factual_pass = 0

    if expected.geocoded:
        factual_checks += 1
        if _coords_close(report, expected):
            factual_pass += 1

    factual_checks += 1
    if expected.renewal_present:
        if report.get("in_renewal") is True:
            factual_pass += 1
    elif report.get("in_renewal") in (None, False):
        factual_pass += 1

    if expected.min_comps_met:
        factual_checks += 1
        if report.get("estimate_agorot") is not None and report.get("n_comps") is not None:
            factual_pass += 1
    else:
        factual_checks += 1
        if report.get("estimate_agorot") is None:
            factual_pass += 1

    claims = report.get("claims") or []
    claims_total = len(claims)
    claims_supported = sum(
        1
        for claim in claims
        if isinstance(claim, dict)
        and claim.get("verify_status") in SUPPORTED_VERIFY
        and claim.get("evidence_ids")
    )

    completeness_checks = 2
    completeness_pass = 0
    missing = report.get("missing_information") or []
    if expected.plan_source_conflict:
        conflicts = report.get("conflicts") or []
        if conflicts or any("plan" in str(item).lower() for item in missing):
            completeness_pass += 1
    else:
        completeness_pass += 1
    if not expected.min_comps_met:
        if report.get("estimate_agorot") is None or any(
            "coverage" in str(item).lower() or "comparable" in str(item).lower() for item in missing
        ):
            completeness_pass += 1
    elif report.get("estimate_agorot") is not None:
        completeness_pass += 1

    return PropertyScore(
        property_id=property_id,
        factual_checks=factual_checks,
        factual_pass=factual_pass,
        claims_total=claims_total,
        claims_supported=claims_supported,
        completeness_checks=completeness_checks,
        completeness_pass=completeness_pass,
        followups_triggered=len(followups),
        latency_ms=latency_ms,
    )


def format_variant_summary(score: VariantScore) -> str:
    evaluated = len(score.evaluated)
    skipped = len(score.properties) - evaluated
    return (
        f"variant={score.variant} evaluated={evaluated} skipped={skipped} "
        f"accuracy={score.accuracy_rate():.1%} claim_support={score.claim_support_rate():.1%} "
        f"completeness={score.completeness_rate():.1%} followups={score.followups_total()} "
        f"cost_usd={score.cost_usd:.4f} latency_p50_ms={score.latency_p50_ms()} "
        f"latency_p95_ms={score.latency_p95_ms()}"
    )


def summary_to_markdown(scores: list[VariantScore], *, notes: list[str] | None = None) -> str:
    lines = ["# Agent eval summary", ""]
    for row in scores:
        lines.append(f"- {format_variant_summary(row)}")
    if notes:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in notes)
    lines.append("")
    return "\n".join(lines)
