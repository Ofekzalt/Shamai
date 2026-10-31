from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.evidence.models import Evidence


def get_by_id(session: Session, evidence_id: uuid.UUID) -> Evidence | None:
    return session.get(Evidence, evidence_id)


def get_by_key(session: Session, key: str) -> Evidence | None:
    stmt = select(Evidence).where(Evidence.key == key)
    return session.scalars(stmt).first()


def upsert(
    session: Session,
    *,
    key: str,
    run_id: uuid.UUID,
    tool_name: str,
    params: dict[str, Any],
    payload: dict[str, Any],
    source: str,
    retrieved_at: datetime,
    coverage_status: str | None,
) -> Evidence:
    stmt = insert(Evidence).values(
        key=key,
        run_id=run_id,
        tool_name=tool_name,
        params=params,
        payload=payload,
        source=source,
        retrieved_at=retrieved_at,
        coverage_status=coverage_status,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={
            "payload": payload,
            "source": source,
            "retrieved_at": retrieved_at,
            "coverage_status": coverage_status,
        },
    )
    session.execute(stmt)
    session.flush()
    row = get_by_key(session, key)
    assert row is not None
    return row
