from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.point_in_time import visible_as_of
from app.modules.planning.models import PlanStatusEvent


def list_status_events_as_of(
    session: Session,
    plan_id: uuid.UUID,
    as_of: datetime,
) -> list[PlanStatusEvent]:
    stmt = visible_as_of(
        select(PlanStatusEvent).where(PlanStatusEvent.plan_id == plan_id),
        as_of,
    )
    return list(session.scalars(stmt).all())
