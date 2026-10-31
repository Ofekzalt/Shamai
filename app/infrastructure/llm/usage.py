from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.llm.models import LlmCall


def record_llm_call(
    session: Session,
    *,
    run_id: uuid.UUID,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: Decimal | float,
) -> None:
    session.add(
        LlmCall(
            id=uuid.uuid4(),
            run_id=run_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=Decimal(str(cost_usd)),
            created_at=datetime.now(tz=UTC),
        )
    )


def langgraph_config_with_run_id(run_id: uuid.UUID) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(run_id)}}
