from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.jobs.exceptions import IdempotencyConflictError
from app.modules.investigation import service
from app.modules.investigation.dto import (
    AnalysisCreatedResponse,
    AnalysisReportResponse,
    AnalysisStatusResponse,
    CreateAnalysisRequest,
)

router = APIRouter(tags=["analyses"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/analyses",
    response_model=AnalysisCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis(
    body: CreateAnalysisRequest,
    session: SessionDep,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> AnalysisCreatedResponse:
    if not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key required",
        )
    try:
        job, created = service.enqueue_analysis(
            session,
            idempotency_key=idempotency_key.strip(),
            body=body,
        )
        session.commit()
    except IdempotencyConflictError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key reused with a different request body",
        ) from exc

    if not created:
        response.status_code = status.HTTP_200_OK
    return AnalysisCreatedResponse(id=job.id, status=job.status)


@router.get("/analyses/{analysis_id}", response_model=AnalysisStatusResponse)
def get_analysis_status(
    analysis_id: uuid.UUID,
    session: SessionDep,
) -> AnalysisStatusResponse:
    job = service.get_analysis(session, analysis_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return AnalysisStatusResponse(id=job.id, status=job.status, error=job.error)


@router.get("/analyses/{analysis_id}/report", response_model=AnalysisReportResponse)
def get_analysis_report(
    analysis_id: uuid.UUID,
    session: SessionDep,
) -> AnalysisReportResponse:
    job = service.get_analysis(session, analysis_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if job.result_json is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not ready")
    return AnalysisReportResponse(report=job.result_json)
