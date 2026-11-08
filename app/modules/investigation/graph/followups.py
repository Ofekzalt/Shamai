from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter


class ExplainPricePremium(BaseModel):
    type: Literal["ExplainPricePremium"] = "ExplainPricePremium"
    source_row_id: str
    reason: str | None = None


class CompareAroundEvent(BaseModel):
    type: Literal["CompareAroundEvent"] = "CompareAroundEvent"
    event_at: datetime
    radius_m: float = 500.0
    reason: str | None = None


class ResolvePlanConflict(BaseModel):
    type: Literal["ResolvePlanConflict"] = "ResolvePlanConflict"
    plan_ids: list[str]
    reason: str | None = None


FollowUp = Annotated[
    ExplainPricePremium | CompareAroundEvent | ResolvePlanConflict,
    Field(discriminator="type"),
]

_ADAPTER = TypeAdapter(FollowUp)

MARKET_FOLLOWUP_TYPES = frozenset({"ExplainPricePremium", "CompareAroundEvent"})
DEVELOPMENT_FOLLOWUP_TYPES = frozenset({"ResolvePlanConflict"})


def parse_followup(data: dict[str, Any] | FollowUp) -> FollowUp:
    if isinstance(data, (ExplainPricePremium, CompareAroundEvent, ResolvePlanConflict)):
        return data
    return _ADAPTER.validate_python(data)


def followup_identity(item: dict[str, Any] | FollowUp) -> str:
    """Stable dedup key: ignores ``reason``; ``ResolvePlanConflict`` plan ids are sorted."""
    parsed = parse_followup(item)
    payload = parsed.model_dump(mode="json", exclude={"reason"})
    if payload.get("type") == "ResolvePlanConflict":
        payload["plan_ids"] = sorted(payload.get("plan_ids") or [])
    return canonical_followup(payload)


def canonical_followup(payload: dict[str, Any]) -> str:
    from app.modules.evidence.canonical import canonical_params

    return canonical_params(payload)


def followup_dump(item: FollowUp) -> dict[str, Any]:
    return item.model_dump(mode="json")


def specialist_for(item: dict[str, Any] | FollowUp) -> Literal["market", "development"]:
    parsed = parse_followup(item)
    if parsed.type in DEVELOPMENT_FOLLOWUP_TYPES:
        return "development"
    return "market"
