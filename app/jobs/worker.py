from __future__ import annotations

import logging
import signal
import time

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.logging import configure_logging, log_extra
from app.jobs import queue
from app.jobs.checkpointer import ensure_checkpointer_ready
from app.jobs.reaper import reap_expired_leases
from app.jobs.runner import run_job

logger = logging.getLogger(__name__)

_stop = False


def _handle_stop(*_args: object) -> None:
    global _stop
    _stop = True


def main() -> None:
    configure_logging(get_settings().log_level)
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    session_factory = get_session_factory()
    settings = get_settings()
    poll_seconds = 1.0

    ensure_checkpointer_ready()
    logger.info("worker started", extra=log_extra(event="jobs.worker_started"))

    while not _stop:
        session = session_factory()
        try:
            reap_expired_leases(session)
            job = queue.claim_one(session, settings=settings)
            if job is None:
                session.commit()
                time.sleep(poll_seconds)
                continue
            job_id = job.id
            session.commit()
        except Exception:
            session.rollback()
            logger.exception(
                "worker claim failed",
                extra=log_extra(event="jobs.claim_failed"),
            )
            time.sleep(poll_seconds)
            continue
        finally:
            session.close()

        run_session = session_factory()
        try:
            run_job(
                run_session,
                job_id,
                settings=settings,
                session_factory=session_factory,
            )
        except Exception:
            run_session.rollback()
            logger.exception(
                "worker run failed",
                extra=log_extra(event="jobs.run_failed", job_id=str(job_id)),
            )
        finally:
            run_session.close()

    logger.info("worker stopped", extra=log_extra(event="jobs.worker_stopped"))


if __name__ == "__main__":
    main()
