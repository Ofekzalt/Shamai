from __future__ import annotations

import logging
import sys
import time
from contextvars import ContextVar
from typing import Any
from urllib.parse import urlparse

from pythonjsonlogger.json import JsonFormatter

HANDLER_NAME = "shamai"
_LOGGER_NAMES = ("app", "evals")

_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("job_id", default=None)

_handler: logging.Handler | None = None


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _request_id.get()
        job_id = _job_id.get()
        if request_id is not None:
            record.request_id = request_id
        if job_id is not None:
            record.job_id = job_id
        return True


def parse_log_level(level: str) -> int:
    key = level.upper()
    if key not in _LEVELS:
        allowed = ", ".join(sorted(_LEVELS))
        raise ValueError(f"invalid log level {level!r}; expected one of: {allowed}")
    return _LEVELS[key]


def set_log_context(*, request_id: str | None = None, job_id: str | None = None) -> None:
    if request_id is not None:
        _request_id.set(request_id)
    if job_id is not None:
        _job_id.set(job_id)


def clear_log_context() -> None:
    _request_id.set(None)
    _job_id.set(None)


def _build_handler(level: int) -> logging.Handler:
    handler = logging.StreamHandler(sys.stderr)
    handler.name = HANDLER_NAME
    formatter = JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
        timestamp=True,
    )
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    handler.addFilter(_ContextFilter())
    handler.setLevel(level)
    return handler


def configure_logging(level: str = "INFO") -> None:
    global _handler
    numeric = parse_log_level(level)
    if _handler is None:
        _handler = _build_handler(numeric)
    else:
        _handler.setLevel(numeric)
    for name in _LOGGER_NAMES:
        log = logging.getLogger(name)
        log.setLevel(numeric)
        log.propagate = False
        if _handler not in log.handlers:
            log.addHandler(_handler)


def host_from_url(url: str) -> str:
    parsed = urlparse(url.split("?", 1)[0])
    return parsed.netloc or url


def log_extra(**fields: Any) -> dict[str, Any]:
    return {k: v for k, v in fields.items() if v is not None}
