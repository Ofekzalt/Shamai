from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.gis.arcgis import HttpGetClient
from app.modules.evidence.store import upsert_evidence
from app.modules.investigation.tools._helpers import coverage_value, dt_param, limitation_payload
from app.modules.planning import service as planning_service
from app.modules.planning.constants import IPLAN_SOURCE, RENEWAL_SOURCE
from app.modules.planning.dto import PlansAtPointQuery, RenewalAtPointQuery


class PlansAtLocationResult(BaseModel):
    plans: list[dict]
    evidence_ids: list[uuid.UUID]


class PlanStatusHistoryResult(BaseModel):
    events: list[dict]
    evidence_ids: list[uuid.UUID]


class RenewalAreasResult(BaseModel):
    renewals: list[dict]
    evidence_ids: list[uuid.UUID]


def plans_at_location(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    lon: float,
    lat: float,
    as_of: datetime,
) -> PlansAtLocationResult:
    query = PlansAtPointQuery(lon=lon, lat=lat, as_of=as_of)
    service_result = planning_service.plans_at_point(session, client, query)
    plans = [
        {
            "plan_id": plan.plan_id,
            "pl_number": plan.pl_number,
            "status": plan.status,
            "mp_id": plan.mp_id,
            "name": plan.name,
        }
        for plan in service_result.data
    ]
    retrieved_at = datetime.now(tz=UTC)
    params = {"lon": lon, "lat": lat, "as_of": dt_param(as_of)}
    payload = {
        "plans": plans,
        "plan_count": len(plans),
        "limitation": limitation_payload(service_result.limitation),
        "coverage_status": coverage_value(service_result.coverage_status),
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="plans_at_location",
        params=params,
        payload=payload,
        source=IPLAN_SOURCE,
        retrieved_at=retrieved_at,
        coverage_status=coverage_value(service_result.coverage_status),
    )
    return PlansAtLocationResult(plans=plans, evidence_ids=[evidence.id])


def plan_status_history(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    plan_id: uuid.UUID,
    as_of: datetime,
) -> PlanStatusHistoryResult:
    del client
    service_result = planning_service.plan_status_history(session, plan_id=plan_id, as_of=as_of)
    serialized = [
        {
            "status": event.status,
            "effective_at": dt_param(event.effective_at),
            "published_at": dt_param(event.published_at) if event.published_at else None,
            "available_at": dt_param(event.available_at),
        }
        for event in service_result.data
    ]
    retrieved_at = datetime.now(tz=UTC)
    params = {"plan_id": str(plan_id), "as_of": dt_param(as_of)}
    payload = {
        "events": serialized,
        "event_count": len(serialized),
        "limitation": limitation_payload(service_result.limitation),
        "coverage_status": coverage_value(service_result.coverage_status),
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="plan_status_history",
        params=params,
        payload=payload,
        source=IPLAN_SOURCE,
        retrieved_at=retrieved_at,
        coverage_status=coverage_value(service_result.coverage_status),
    )
    return PlanStatusHistoryResult(events=serialized, evidence_ids=[evidence.id])


def renewal_areas(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    lon: float,
    lat: float,
    as_of: datetime,
) -> RenewalAreasResult:
    query = RenewalAtPointQuery(lon=lon, lat=lat, as_of=as_of)
    service_result = planning_service.renewal_at_point(session, client, query)
    renewals = [
        {
            "renewal_id": row.renewal_id,
            "source_feature_id": row.source_feature_id,
            "taba": row.taba,
            "snapshot_status": row.snapshot_status,
        }
        for row in service_result.data
    ]
    retrieved_at = datetime.now(tz=UTC)
    params = {"lon": lon, "lat": lat, "as_of": dt_param(as_of)}
    payload = {
        "renewals": renewals,
        "renewal_count": len(renewals),
        "limitation": limitation_payload(service_result.limitation),
        "coverage_status": coverage_value(service_result.coverage_status),
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="renewal_areas",
        params=params,
        payload=payload,
        source=RENEWAL_SOURCE,
        retrieved_at=retrieved_at,
        coverage_status=coverage_value(service_result.coverage_status),
    )
    return RenewalAreasResult(renewals=renewals, evidence_ids=[evidence.id])
