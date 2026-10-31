from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class CoverageStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class LimitationCode(StrEnum):
    COVERAGE_INCOMPLETE = "coverage_incomplete"
    PROVIDER_FAILED = "provider_failed"


class Limitation(BaseModel):
    code: LimitationCode
    message: str


class ServiceResult[T](BaseModel):
    data: T
    coverage_status: CoverageStatus | None = None
    limitation: Limitation | None = None
