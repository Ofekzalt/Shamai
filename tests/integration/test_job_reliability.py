from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.jobs import queue
from app.jobs.reaper import reap_expired_leases
from app.jobs.runner import run_job


def _request() -> dict:
    return {
        "address": "Test St 1",
        "asking_price_agorot": 1_000_000_00,
        "size_sqm": 70.0,
        "profile": "investor",
    }


def test_complete_is_idempotent(db_session: Session) -> None:
    job, _ = queue.enqueue(db_session, idempotency_key="rel-complete", request_json=_request())
    job.status = "running"
    db_session.flush()
    result = {"stub": True}
    assert queue.complete(db_session, job.id, result) is True
    assert queue.complete(db_session, job.id, result) is True
    db_session.refresh(job)
    assert job.status == "done"
    assert job.result_json == result


def test_reaper_requeues_expired_lease(db_session: Session) -> None:
    job, _ = queue.enqueue(db_session, idempotency_key="rel-reap", request_json=_request())
    job.status = "running"
    job.attempts = 1
    job.lease_expires_at = datetime.now(tz=UTC) - timedelta(seconds=30)
    db_session.flush()

    count = reap_expired_leases(db_session)
    assert count == 1
    db_session.refresh(job)
    assert job.status == "queued"
    assert job.lease_expires_at is None


def test_reaper_fails_when_max_attempts(db_session: Session) -> None:
    job, _ = queue.enqueue(db_session, idempotency_key="rel-max", request_json=_request())
    job.status = "running"
    job.attempts = job.max_attempts
    job.lease_expires_at = datetime.now(tz=UTC) - timedelta(seconds=30)
    db_session.flush()

    reap_expired_leases(db_session)
    db_session.refresh(job)
    assert job.status == "failed"


def test_run_job_completes_with_stub_result(db_session: Session, monkeypatch) -> None:
    def fake_invoke(**_kwargs: object) -> dict:
        return {"stub": True, "claims": []}

    monkeypatch.setattr("app.jobs.runner._invoke_graph", fake_invoke)
    monkeypatch.setattr("app.jobs.runner.ensure_checkpointer_ready", lambda: None)

    job, _ = queue.enqueue(
        db_session,
        idempotency_key=f"rel-run-{uuid.uuid4()}",
        request_json=_request(),
    )
    job.status = "running"
    db_session.flush()

    run_job(db_session, job.id)
    db_session.refresh(job)
    assert job.status == "done"
    assert job.result_json == {"stub": True, "claims": []}
