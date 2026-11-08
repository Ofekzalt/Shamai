from __future__ import annotations

from evals.agents.expected import PropertyExpectation
from evals.agents.score import VariantScore, score_property


def test_score_property_skips_when_not_geocoded() -> None:
    row = score_property(
        property_id="x",
        expected=PropertyExpectation(property_id="x", geocoded=False),
        report=None,
        followups=[],
        latency_ms=10,
        skip_reason="address not in geocode cache",
    )
    assert row.skipped
    assert row.skip_reason == "address not in geocode cache"


def test_score_property_claim_support() -> None:
    expected = PropertyExpectation(
        property_id="r",
        geocoded=True,
        lon=34.78,
        lat=32.08,
        min_comps_met=True,
    )
    report = {
        "lon": 34.78,
        "lat": 32.08,
        "estimate_agorot": 4_000_000_00,
        "n_comps": 6,
        "in_renewal": None,
        "claims": [
            {"verify_status": "pass", "evidence_ids": ["00000000-0000-0000-0000-000000000001"]},
            {"verify_status": "reject", "evidence_ids": []},
        ],
        "missing_information": [],
        "conflicts": [],
    }
    row = score_property(
        property_id="r",
        expected=expected,
        report=report,
        followups=["CompareAroundEvent"],
        latency_ms=100,
    )
    assert row.claims_total == 2
    assert row.claims_supported == 1
    assert row.followups_triggered == 1


def test_variant_score_latency_percentiles() -> None:
    minimal_report = {
        "lon": 1.0,
        "lat": 2.0,
        "claims": [],
        "missing_information": [],
        "conflicts": [],
    }
    score = VariantScore(variant="rules")
    score.properties.append(
        score_property(
            property_id="a",
            expected=PropertyExpectation(property_id="a", geocoded=True),
            report=minimal_report,
            followups=[],
            latency_ms=100,
        )
    )
    score.properties[-1].factual_checks = 1
    score.properties[-1].factual_pass = 1
    score.properties.append(
        score_property(
            property_id="b",
            expected=PropertyExpectation(property_id="b", geocoded=True),
            report=minimal_report,
            followups=[],
            latency_ms=500,
        )
    )
    score.properties[-1].factual_checks = 1
    score.properties[-1].factual_pass = 1
    assert score.latency_p50_ms() == 500
    assert score.latency_p95_ms() == 500
