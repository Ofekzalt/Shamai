from __future__ import annotations

import logging
import threading

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_ADVISORY_LOCK_ID = 0x5348_4D41
_process_lock = threading.Lock()
_ready = False


def _psycopg_conn_string(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return database_url


def ensure_checkpointer_ready() -> None:
    global _ready
    with _process_lock:
        if _ready:
            return
        conn_string = _psycopg_conn_string(get_settings().database_url)
        with psycopg.connect(conn_string, autocommit=True) as conn:
            conn.execute("SELECT pg_advisory_lock(%s)", (_ADVISORY_LOCK_ID,))
            try:
                checkpointer = PostgresSaver(conn)
                checkpointer.setup()
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (_ADVISORY_LOCK_ID,))
        _ready = True
        logger.info("langgraph checkpointer ready")
