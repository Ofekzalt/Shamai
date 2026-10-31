from __future__ import annotations

from sqlalchemy.orm import Session

from app.jobs import queue


def reap_expired_leases(session: Session) -> int:
    return queue.requeue_expired_leases(session)
