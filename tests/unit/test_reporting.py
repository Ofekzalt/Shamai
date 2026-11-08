from __future__ import annotations

from app.modules.reporting.dto import Report
from app.modules.reporting.renderer import render


def test_investor_template_uses_correlation_language() -> None:
    report = Report(
        profile="investor",
        address="Rothschild 1",
        correlation_not_causation=True,
        compare_around_event={"before_count": 1, "after_count": 1},
        missing_information=["Transaction coverage is incomplete for this as-of window."],
        n_comps=None,
    )
    markdown = render(report, "investor")
    lowered = markdown.lower()
    assert "index-adjusted correlation" in lowered
    assert "not evidence that the plan caused appreciation" in lowered
    assert "0 transactions" not in lowered
