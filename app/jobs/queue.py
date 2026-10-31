from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.jobs.canonical import canonical_request_json
from app.jobs.exceptions import IdempotencyConflictError
from app.jobs.models import Job

TERMINAL_STATUSES = frozenset({"done", "failed", "incomplete"})


def _now() -> datetime:
    return datetime.now(tz=UTC)


def enqueue(
    session: Session,
    *,
    idempotency_key: str,
    request_json: dict[str, Any],
) -> tuple[Job, bool]:
    canonical = canonical_request_json(request_json)
    existing = session.execute(
        select(Job).where(Job.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing is not None:
        if canonical_request_json(existing.request_json) != canonical:
            raise IdempotencyConflictError
        return existing, False

    now = _now()
    job = Job(
        id=uuid.uuid4(),
        status="queued",
        idempotency_key=idempotency_key,
        attempts=0,
        max_attempts=3,
        lease_expires_at=None,
        heartbeat_at=None,
        error=None,
        request_json=request_json,
        result_json=None,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.flush()
    return job, True


def claim_one(session: Session, *, settings: Settings | None = None) -> Job | None:
    settings = settings or get_settings()
    now = _now()
    lease_until = now + timedelta(seconds=settings.lease_seconds)
    stmt = (
        select(Job)
        .where(Job.status == "queued")
        .order_by(Job.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = session.execute(stmt).scalar_one_or_none()
    if job is None:
        return None

    job.status = "running"
    job.attempts += 1
    job.lease_expires_at = lease_until
    job.heartbeat_at = now
    job.updated_at = now
    session.flush()
    return job


def heartbeat(session: Session, job_id: uuid.UUID, *, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    now = _now()
    lease_until = now + timedelta(seconds=settings.lease_seconds)
    result = session.execute(
        update(Job)
        .where(
            Job.id == job_id,
            Job.status == "running",
        )
        .values(
            heartbeat_at=now,
            lease_expires_at=lease_until,
            updated_at=now,
        )
    )
    return result.rowcount == 1  # type: ignore[attr-defined]


def complete(
    session: Session,
    job_id: uuid.UUID,
    result_json: dict[str, Any],
) -> bool:
    now = _now()
    job = session.get(Job, job_id)
    if job is None:
        return False
    if job.status == "done":
        return True
    job.status = "done"
    job.result_json = result_json
    job.lease_expires_at = None
    job.error = None
    job.updated_at = now
    session.flush()
    return True


def fail(session: Session, job_id: uuid.UUID, error: str) -> bool:
    now = _now()
    job = session.get(Job, job_id)
    if job is None:
        return False
    if job.status in TERMINAL_STATUSES:
        return job.status == "failed"
    job.status = "failed"
    job.error = error
    job.lease_expires_at = None
    job.updated_at = now
    session.flush()
    return True


def mark_incomplete(
    session: Session,
    job_id: uuid.UUID,
    *,
    result_json: dict[str, Any] | None,
    error: str | None = None,
) -> bool:
    now = _now()
    job = session.get(Job, job_id)
    if job is None:
        return False
    if job.status == "incomplete":
        return True
    job.status = "incomplete"
    if result_json is not None:
        job.result_json = result_json
    job.error = error
    job.lease_expires_at = None
    job.updated_at = now
    session.flush()
    return True


def requeue_expired_leases(session: Session) -> int:
    now = _now()
    expired = session.execute(
        select(Job).where(
            Job.status == "running",
            Job.lease_expires_at.is_not(None),
            Job.lease_expires_at < now,
        )
    ).scalars()
    count = 0
    for job in expired:
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.error = job.error or "lease expired; max attempts reached"
            job.lease_expires_at = None
        else:
            job.status = "queued"
            job.lease_expires_at = None
        job.updated_at = now
        count += 1
    if count:
        session.flush()
    return count


def get_job(session: Session, job_id: uuid.UUID) -> Job | None:
    return session.get(Job, job_id)
