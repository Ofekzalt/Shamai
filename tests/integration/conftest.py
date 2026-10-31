from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.database import get_engine

ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")


@pytest.fixture(scope="session")
def db_engine():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostGIS database not available: {exc}")
    cfg = Config(ALEMBIC_INI)
    command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
