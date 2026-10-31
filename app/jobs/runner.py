from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import TYPE_CHECKING

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import log_extra
from app.infrastructure.llm.usage import langgraph_config_with_run_id
from app.jobs import queue
from app.jobs.checkpointer import ensure_checkpointer_ready
from app.modules.investigation.graph.builder import build_graph

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _psycopg_conn_string(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return database_url


def _invoke_graph(
    *,
    job_id: uuid.UUID,
    request_json: dict,
    conn_string: str,
    variant: str,
) -> dict:
    with PostgresSaver.from_conn_string(conn_string) as checkpointer:
        graph = build_graph(variant, checkpointer=checkpointer)  # type: ignore[arg-type]
        config = langgraph_config_with_run_id(job_id)
        initial: dict = {"job_id": str(job_id), "request": request_json}
        final = graph.invoke(initial, config=config)
        result = final.get("result_json")
        if not isinstance(result, dict):
            raise RuntimeError("graph finished without result_json")
        return result


def run_job(
    session: Session,
    job_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    variant: str = "rules",
    session_factory: sessionmaker | None = None,
) -> None:
    settings = settings or get_settings()
    if session_factory is None:
        from app.core.database import get_session_factory

        session_factory = get_session_factory()
    job = queue.get_job(session, job_id)
    if job is None or job.status != "running":
        return

    conn_string = _psycopg_conn_string(settings.database_url)
    ensure_checkpointer_ready()

    stop = threading.Event()

    def _heartbeat_loop() -> None:
        while not stop.wait(timeout=settings.heartbeat_seconds):
            hb_session = session_factory()
            try:
                queue.heartbeat(hb_session, job_id, settings=settings)
                hb_session.commit()
            finally:
                hb_session.close()

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                _invoke_graph,
                job_id=job_id,
                request_json=job.request_json,
                conn_string=conn_string,
                variant=variant,
            )
            try:
                result_json = future.result(timeout=settings.run_timeout_seconds)
            except FuturesTimeoutError:
                session.rollback()
                partial = job.result_json if isinstance(job.result_json, dict) else None
                queue.mark_incomplete(
                    session,
                    job_id,
                    result_json=partial,
                    error="run timeout",
                )
                session.commit()
                logger.warning(
                    "job run timeout",
                    extra=log_extra(event="jobs.run_timeout", job_id=str(job_id)),
                )
                return
    except Exception as exc:
        session.rollback()
        queue.fail(session, job_id, str(exc))
        session.commit()
        logger.exception(
            "job run failed",
            extra=log_extra(event="jobs.run_failed", job_id=str(job_id)),
        )
        return
    finally:
        stop.set()
        heartbeat_thread.join(timeout=2)

    queue.complete(session, job_id, result_json)
    session.commit()
    logger.info(
        "job completed",
        extra=log_extra(event="jobs.completed", job_id=str(job_id)),
    )
