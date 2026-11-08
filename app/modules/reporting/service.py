from __future__ import annotations

from typing import Any

from app.modules.reporting.dto import Report
from app.modules.reporting.renderer import render


def render_report(result_json: dict[str, Any]) -> str:
    report = Report.model_validate(result_json)
    return render(report, report.profile)
