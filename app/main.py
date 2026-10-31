from __future__ import annotations

import uuid

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging import clear_log_context, configure_logging, set_log_context
from app.modules.evidence.controller import router as evidence_router
from app.modules.investigation.controller import router as investigation_router

configure_logging(get_settings().log_level)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_log_context(request_id=request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_log_context()


app = FastAPI()
app.add_middleware(RequestIdMiddleware)

app.include_router(investigation_router)
app.include_router(evidence_router)
