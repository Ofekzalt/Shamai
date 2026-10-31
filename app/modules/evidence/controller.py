from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.evidence import repository
from app.modules.evidence.dto import EvidenceResponse

router = APIRouter(tags=["evidence"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: uuid.UUID, session: SessionDep) -> EvidenceResponse:
    row = repository.get_by_id(session, evidence_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return EvidenceResponse(
        id=row.id,
        tool_name=row.tool_name,
        params=row.params,
        payload=row.payload,
        source=row.source,
        retrieved_at=row.retrieved_at,
        coverage_status=row.coverage_status,
    )
