from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.results import ServiceResult

PlanServiceResult = ServiceResult[list["PlanAtPoint"]]


class PlanAtPoint(BaseModel):
    plan_id: str
    pl_number: str
    status: str
    mp_id: str | None = None
    name: str | None = None


class RenewalAtPoint(BaseModel):
    renewal_id: str
    source_feature_id: str
    taba: str | None
    snapshot_status: str | None


class PlansAtPointQuery(BaseModel):
    lon: float
    lat: float
    as_of: datetime


class RenewalAtPointQuery(BaseModel):
    lon: float
    lat: float
    as_of: datetime
