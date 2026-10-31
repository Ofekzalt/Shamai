from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.jobs import queue
from app.jobs.exceptions import IdempotencyConflictError
from app.jobs.models import Job
from app.modules.investigation.dto import CreateAnalysisRequest


def enqueue_analysis(
    session: Session,
    *,
    idempotency_key: str,
    body: CreateAnalysisRequest,
) -> tuple[Job, bool]:
    return queue.enqueue(
        session,
        idempotency_key=idempotency_key,
        request_json=body.to_request_json(),
    )


def get_analysis(session: Session, analysis_id: uuid.UUID) -> Job | None:
    return queue.get_job(session, analysis_id)


__all__ = ["enqueue_analysis", "get_analysis", "IdempotencyConflictError"]
