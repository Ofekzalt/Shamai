from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisProfile(StrEnum):
    homebuyer = "homebuyer"
    investor = "investor"


class CreateAnalysisRequest(BaseModel):
    address: str = Field(min_length=1, max_length=512)
    asking_price_agorot: int = Field(gt=0)
    size_sqm: float = Field(gt=0)
    profile: AnalysisProfile
    rooms: float | None = Field(default=None, gt=0)
    floor: int | None = None
    year_built: int | None = Field(default=None, ge=1800, le=2100)
    as_of: date | None = None

    def to_request_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class AnalysisCreatedResponse(BaseModel):
    id: uuid.UUID
    status: str


class AnalysisStatusResponse(BaseModel):
    id: uuid.UUID
    status: Literal["queued", "running", "verifying", "done", "failed", "incomplete"]
    error: str | None = None


class AnalysisReportResponse(BaseModel):
    report: dict[str, Any]
