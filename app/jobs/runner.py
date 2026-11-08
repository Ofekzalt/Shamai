from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from decimal import Decimal
from typing import TYPE_CHECKING

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import log_extra
from app.infrastructure.gis.http import default_http_client
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.llm.usage import langgraph_config_with_run_id, record_llm_call
from app.jobs import queue
from app.jobs.checkpointer import ensure_checkpointer_ready
from app.modules.investigation.graph.builder import build_graph
from app.modules.investigation.graph.runtime import RUNTIME_KEY, GraphRuntime

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
    session_factory: sessionmaker,
    settings: Settings,
    on_verifying: object | None = None,
    progress: dict | None = None,
) -> dict:
    http = default_http_client()

    def on_usage(model: str, prompt_tokens: int, completion_tokens: int, cost_usd: Decimal) -> None:
        session = session_factory()
        try:
            record_llm_call(
                session,
                run_id=job_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
            )
            session.commit()
        finally:
            session.close()

    llm = LlmClient(settings, on_usage=on_usage) if settings.llm_api_key else None
    runtime = GraphRuntime(
        session_factory=session_factory,
        http=http,
        settings=settings,
        llm=llm,
        owns_sessions=True,
        variant=variant,  # type: ignore[arg-type]
        on_verifying=on_verifying if callable(on_verifying) else None,
    )
    try:
        with PostgresSaver.from_conn_string(conn_string) as checkpointer:
            graph = build_graph(variant, checkpointer=checkpointer)  # type: ignore[arg-type]
            config = langgraph_config_with_run_id(job_id, {RUNTIME_KEY: runtime})
            if progress is not None:
                progress["graph"] = graph
                progress["config"] = config
            initial: dict = {"job_id": str(job_id), "request": request_json}
            final = graph.invoke(initial, config=config)
            result = final.get("result_json")
            if not isinstance(result, dict):
                raise RuntimeError("graph finished without result_json")
            return result
    finally:
        http.close()


def run_job(
    session: Session,
    job_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    variant: str | None = None,
    session_factory: sessionmaker | None = None,
) -> None:
    settings = settings or get_settings()
    variant = variant or settings.variant
    if session_factory is None:
        from app.core.database import get_session_factory

        session_factory = get_session_factory()
    job = queue.get_job(session, job_id)
    if job is None or job.status != "running":
        return

    logger.info(
        "job started",
        extra=log_extra(event="jobs.started", job_id=str(job_id), variant=variant),
    )
    started = time.perf_counter()
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
    pool = ThreadPoolExecutor(max_workers=1)
    timed_out = False
    result_json: dict | None = None
    try:

        def on_verifying() -> None:
            verify_session = session_factory()
            try:
                queue.mark_verifying(verify_session, job_id)
                verify_session.commit()
            finally:
                verify_session.close()

        progress: dict = {}
        future = pool.submit(
            _invoke_graph,
            job_id=job_id,
            request_json=job.request_json,
            conn_string=conn_string,
            variant=variant,
            session_factory=session_factory,
            settings=settings,
            on_verifying=on_verifying,
            progress=progress,
        )
        try:
            result_json = future.result(timeout=settings.run_timeout_seconds)
        except FuturesTimeoutError:
            timed_out = True
            future.cancel()
            partial = job.result_json if isinstance(job.result_json, dict) else None
            graph = progress.get("graph")
            config = progress.get("config")
            if graph is not None and config is not None:
                try:
                    values = graph.get_state(config).values
                    maybe = values.get("result_json")
                    if isinstance(maybe, dict):
                        partial = maybe
                    elif values:
                        from app.modules.investigation.graph.finalize import finalize_node

                        built = finalize_node(values).get("result_json")
                        if isinstance(built, dict):
                            partial = built
                except Exception:
                    logger.exception(
                        "timeout partial report failed",
                        extra=log_extra(event="jobs.timeout_partial", job_id=str(job_id)),
                    )
            queue.mark_incomplete(
                session,
                job_id,
                result_json=partial,
                error="run timeout",
            )
            session.commit()
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "job run timeout",
                extra=log_extra(
                    event="jobs.run_timeout",
                    job_id=str(job_id),
                    duration_ms=duration_ms,
                ),
            )
            return
    except Exception as exc:
        session.rollback()
        queue.fail(session, job_id, str(exc))
        session.commit()
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "job run failed",
            extra=log_extra(
                event="jobs.run_failed",
                job_id=str(job_id),
                duration_ms=duration_ms,
            ),
        )
        return
    finally:
        stop.set()
        heartbeat_thread.join(timeout=2)
        pool.shutdown(wait=not timed_out, cancel_futures=True)

    if result_json is None:
        return
    if not queue.complete(session, job_id, result_json):
        logger.warning(
            "job complete skipped",
            extra=log_extra(event="jobs.complete_skipped", job_id=str(job_id)),
        )
        return
    session.commit()
    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "job completed",
        extra=log_extra(
            event="jobs.completed",
            job_id=str(job_id),
            duration_ms=duration_ms,
        ),
    )
