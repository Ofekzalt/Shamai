from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    tool_name: str
    params: dict[str, Any]
    payload: dict[str, Any]
    source: str
    retrieved_at: datetime
    coverage_status: str | None = None
