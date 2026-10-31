from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.modules.evidence import repository
from app.modules.evidence.canonical import canonical_params
from app.modules.evidence.models import Evidence


def evidence_key(*, run_id: uuid.UUID, tool_name: str, params: dict[str, Any]) -> str:
    material = f"{run_id}:{tool_name}:{canonical_params(params)}"
    return hashlib.sha256(material.encode()).hexdigest()


def upsert_evidence(
    session: Session,
    *,
    run_id: uuid.UUID,
    tool_name: str,
    params: dict[str, Any],
    payload: dict[str, Any],
    source: str,
    retrieved_at: datetime,
    coverage_status: str | None = None,
) -> Evidence:
    key = evidence_key(run_id=run_id, tool_name=tool_name, params=params)
    return repository.upsert(
        session,
        key=key,
        run_id=run_id,
        tool_name=tool_name,
        params=params,
        payload=payload,
        source=source,
        retrieved_at=retrieved_at,
        coverage_status=coverage_status,
    )
