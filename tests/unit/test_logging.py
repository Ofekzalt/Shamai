from __future__ import annotations

import io
import json
import logging

import pytest

import app.core.logging as logging_module
from app.core.logging import (
    _LOGGER_NAMES,
    HANDLER_NAME,
    clear_log_context,
    configure_logging,
    parse_log_level,
    set_log_context,
)


def _reset_logging() -> None:
    logging_module._handler = None
    for name in _LOGGER_NAMES:
        logging.getLogger(name).handlers.clear()


def _shamai_handler() -> logging.Handler:
    log = logging.getLogger("app")
    handlers = [h for h in log.handlers if getattr(h, "name", None) == HANDLER_NAME]
    assert len(handlers) == 1
    return handlers[0]


def test_configure_logging_is_idempotent() -> None:
    _reset_logging()
    configure_logging("DEBUG")
    first = len(logging.getLogger("app").handlers)
    configure_logging("INFO")
    assert len(logging.getLogger("app").handlers) == first
    assert _shamai_handler().level == logging.INFO
    assert logging.getLogger("app").level == logging.INFO


def test_invalid_log_level_raises() -> None:
    with pytest.raises(ValueError, match="invalid log level"):
        parse_log_level("verbose")


def test_json_log_contains_fields_and_extras() -> None:
    _reset_logging()
    configure_logging("INFO")
    handler = _shamai_handler()
    buffer = io.StringIO()
    old_stream = handler.stream
    handler.stream = buffer
    try:
        set_log_context(job_id="job-abc")
        logging.getLogger("app.test").info(
            "ingestion started",
            extra={"event": "ingestion.started", "source": "odata_nadlan"},
        )
        payload = json.loads(buffer.getvalue().strip())
        assert payload["message"] == "ingestion started"
        assert payload["level"] == "INFO"
        assert payload["name"] == "app.test"
        assert "timestamp" in payload
        assert payload["event"] == "ingestion.started"
        assert payload["source"] == "odata_nadlan"
        assert payload["job_id"] == "job-abc"
    finally:
        handler.stream = old_stream
        clear_log_context()
