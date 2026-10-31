from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.results import CoverageStatus
from app.modules.evidence.calculations import run_calculation
from app.modules.evidence.claims import (
    CalculatedClaim,
    Claim,
    InterpretationClaim,
    ObservedClaim,
)


class VerifyStatus(StrEnum):
    PASS = "pass"
    REJECT = "reject"
    QUALIFIED = "qualified"


@dataclass(frozen=True)
class EvidenceView:
    payload: dict[str, Any]
    coverage_status: str | None


@dataclass(frozen=True)
class VerifyOutcome:
    status: VerifyStatus
    reason: str | None = None


InterpretationJudge = Callable[[InterpretationClaim], bool]


def _resolve_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _values_match(expected: Any, actual: Any) -> bool:
    if expected is None and actual is None:
        return True
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual
    if isinstance(expected, int) and isinstance(actual, int):
        return expected == actual
    if isinstance(expected, int) and isinstance(actual, float):
        return float(expected) == actual
    if isinstance(expected, float) or isinstance(actual, float):
        if expected == 0 and actual == 0:
            return True
        denom = max(abs(float(expected)), abs(float(actual)), 1.0)
        return abs(float(expected) - float(actual)) / denom <= 1e-6
    return expected == actual


def verify_observed(
    claim: ObservedClaim,
    evidence: dict[uuid.UUID, EvidenceView],
) -> VerifyOutcome:
    for evidence_id in claim.evidence_ids:
        if evidence_id not in evidence:
            return VerifyOutcome(VerifyStatus.REJECT, "missing evidence id")
    if claim.empty_assertion is not None:
        empty_paths = {
            "transactions": ("candidate_count", "selected_count"),
            "plans": ("plan_count",),
        }
        for evidence_id in claim.evidence_ids:
            row = evidence[evidence_id]
            if row.coverage_status != CoverageStatus.COMPLETE:
                return VerifyOutcome(
                    VerifyStatus.REJECT,
                    f"empty {claim.empty_assertion} assertion requires complete coverage",
                )
            paths = empty_paths[claim.empty_assertion]
            if not any(_resolve_path(row.payload, path) == 0 for path in paths):
                return VerifyOutcome(
                    VerifyStatus.REJECT,
                    f"empty {claim.empty_assertion} assertion requires a zero count",
                )
    for evidence_id in claim.evidence_ids:
        payload = evidence[evidence_id].payload
        for field in claim.fields:
            actual = _resolve_path(payload, field.path)
            if not _values_match(field.value, actual):
                return VerifyOutcome(VerifyStatus.REJECT, f"field mismatch at {field.path}")
    return VerifyOutcome(VerifyStatus.PASS)


def verify_calculated(claim: CalculatedClaim) -> VerifyOutcome:
    try:
        computed = run_calculation(claim.function, claim.inputs)
    except (KeyError, TypeError, ValueError) as exc:
        return VerifyOutcome(VerifyStatus.REJECT, str(exc))
    if not _values_match(claim.expected, computed):
        return VerifyOutcome(VerifyStatus.REJECT, "calculated value mismatch")
    return VerifyOutcome(VerifyStatus.PASS)


def verify_interpretation(
    claim: InterpretationClaim,
    judge: InterpretationJudge,
) -> VerifyOutcome:
    if not judge(claim):
        return VerifyOutcome(VerifyStatus.QUALIFIED, "interpretation not supported")
    return VerifyOutcome(VerifyStatus.PASS)


def verify_claim(
    claim: Claim,
    evidence: dict[uuid.UUID, EvidenceView],
    *,
    judge: InterpretationJudge | None = None,
) -> VerifyOutcome:
    if isinstance(claim, ObservedClaim):
        return verify_observed(claim, evidence)
    if isinstance(claim, CalculatedClaim):
        return verify_calculated(claim)
    if judge is None:
        return VerifyOutcome(VerifyStatus.REJECT, "interpretation judge required")
    return verify_interpretation(claim, judge)
