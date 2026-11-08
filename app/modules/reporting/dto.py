from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Report(BaseModel):
    profile: str
    address: str
    as_of: str | None = None
    lon: float | None = None
    lat: float | None = None
    asking_price_agorot: int | None = None
    size_sqm: float | None = None
    estimate_agorot: int | None = None
    n_comps: int | None = None
    confidence: str | None = None
    claims: list[dict[str, Any]] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    in_renewal: bool | None = None
    correlation_not_causation: bool = False
    compare_around_event: dict[str, Any] | None = None
