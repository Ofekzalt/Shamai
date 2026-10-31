from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.results import CoverageStatus
from app.modules.evidence.claims import (
    CalculatedClaim,
    InterpretationClaim,
    ObservedClaim,
    ObservedField,
)
from app.modules.evidence.verifier import EvidenceView, VerifyStatus, verify_claim


def test_observed_rejects_missing_evidence() -> None:
    claim = ObservedClaim(
        text="price",
        evidence_ids=[uuid.uuid4()],
        fields=[ObservedField(path="price_agorot", value=1)],
    )
    outcome = verify_claim(claim, {})
    assert outcome.status == VerifyStatus.REJECT
    assert outcome.reason == "missing evidence id"


def test_observed_rejects_field_mismatch() -> None:
    evidence_id = uuid.uuid4()
    claim = ObservedClaim(
        text="price",
        evidence_ids=[evidence_id],
        fields=[ObservedField(path="price_agorot", value=100)],
    )
    evidence = {
        evidence_id: EvidenceView(payload={"price_agorot": 99}, coverage_status="complete"),
    }
    outcome = verify_claim(claim, evidence)
    assert outcome.status == VerifyStatus.REJECT


def test_empty_assertion_requires_complete_coverage_and_zero_count() -> None:
    evidence_id = uuid.uuid4()
    incomplete = ObservedClaim(
        text="no sales",
        evidence_ids=[evidence_id],
        fields=[ObservedField(path="candidate_count", value=0)],
        empty_assertion="transactions",
    )
    outcome = verify_claim(
        incomplete,
        {
            evidence_id: EvidenceView(
                payload={"candidate_count": 0},
                coverage_status=CoverageStatus.INCOMPLETE,
            ),
        },
    )
    assert outcome.status == VerifyStatus.REJECT

    non_zero = ObservedClaim(
        text="no sales",
        evidence_ids=[evidence_id],
        fields=[ObservedField(path="candidate_count", value=3)],
        empty_assertion="transactions",
    )
    outcome = verify_claim(
        non_zero,
        {
            evidence_id: EvidenceView(
                payload={"candidate_count": 3},
                coverage_status=CoverageStatus.COMPLETE,
            ),
        },
    )
    assert outcome.status == VerifyStatus.REJECT


def test_calculated_recomputes_estimate_value() -> None:
    as_of = datetime(2024, 6, 1, tzinfo=UTC)
    sale = datetime(2024, 3, 1, tzinfo=UTC)
    row = {
        "source_row_id": "a",
        "price_agorot": 4_000_000_00,
        "size_sqm": 80.0,
        "floor": 2,
        "rooms": 3.0,
        "lon": 34.78,
        "lat": 32.08,
        "distance_m": 100.0,
        "effective_at": sale.isoformat(),
        "available_at": sale.isoformat(),
        "neighborhood": "test",
        "statistical_area": "SA1",
    }
    subject = {
        "lon": 34.7818,
        "lat": 32.0853,
        "size_sqm": 80.0,
        "as_of": as_of.isoformat(),
        "floor": 2,
        "rooms": 3.0,
        "neighborhood": "test",
        "source_row_id": None,
    }
    index_points = [
        {
            "period_end": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
            "nis_per_sqm": 50_000.0,
            "statistical_area": "SA1",
        },
        {
            "period_end": datetime(2024, 6, 1, tzinfo=UTC).isoformat(),
            "nis_per_sqm": 52_000.0,
            "statistical_area": "SA1",
        },
    ]
    inputs = {"rows": [row], "subject": subject, "index_points": index_points}
    from app.modules.evidence.calculations import run_calculation

    expected = run_calculation("estimate_value", inputs)
    claim = CalculatedClaim(
        text="estimate",
        function="estimate_value",
        inputs=inputs,
        expected=expected,
    )
    outcome = verify_claim(claim, {})
    assert outcome.status == VerifyStatus.PASS

    mismatched = CalculatedClaim(
        text="estimate",
        function="estimate_value",
        inputs=inputs,
        expected=expected + 1,
    )
    reject = verify_claim(mismatched, {})
    assert reject.status == VerifyStatus.REJECT


def test_interpretation_qualifies_when_judge_fails() -> None:
    claim = InterpretationClaim(text="likely premium", evidence_ids=[])
    outcome = verify_claim(claim, {}, judge=lambda _c: False)
    assert outcome.status == VerifyStatus.QUALIFIED
