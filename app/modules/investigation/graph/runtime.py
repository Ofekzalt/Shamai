from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal

from langgraph.types import RunnableConfig
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.gis.arcgis import HttpGetClient
from app.infrastructure.llm.client import LlmClient

RUNTIME_KEY = "shamai_runtime"


@dataclass
class GraphRuntime:
    session_factory: Callable[[], Session]
    http: HttpGetClient
    settings: Settings
    llm: LlmClient | None = None
    owns_sessions: bool = True
    interpretation_judge: Callable[[Any], bool] | None = None
    variant: Literal["single", "rules", "llm"] = "rules"
    on_verifying: Callable[[], None] | None = None


def get_runtime(config: RunnableConfig) -> GraphRuntime:
    configurable = config.get("configurable") or {}
    runtime = configurable.get(RUNTIME_KEY)
    if not isinstance(runtime, GraphRuntime):
        raise RuntimeError("graph runtime missing from config")
    return runtime


@contextmanager
def node_session(runtime: GraphRuntime) -> Iterator[Session]:
    """Yield a DB session; commit/rollback/close only when ``runtime.owns_sessions``."""
    session = runtime.session_factory()
    try:
        yield session
        if runtime.owns_sessions:
            session.commit()
        else:
            session.flush()
    except Exception:
        if runtime.owns_sessions:
            session.rollback()
        raise
    finally:
        if runtime.owns_sessions:
            session.close()
