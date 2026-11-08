from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.modules.reporting.dto import Report

_TEMPLATES = Path(__file__).resolve().parent / "templates"
_ENV = Environment(
    loader=FileSystemLoader(_TEMPLATES),
    autoescape=select_autoescape(enabled_extensions=("j2", "md")),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(report: Report, profile: str) -> str:
    name = "investor.md.j2" if profile == "investor" else "homebuyer.md.j2"
    template = _ENV.get_template(name)
    return template.render(report=report)
