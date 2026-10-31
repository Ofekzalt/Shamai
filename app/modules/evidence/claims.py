from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

ClaimKind = Literal["observed", "calculated", "interpretation"]
EmptyAssertion = Literal["transactions", "plans"]


class ObservedField(BaseModel):
    path: str
    value: Any


class ObservedClaim(BaseModel):
    kind: Literal["observed"] = "observed"
    text: str
    evidence_ids: list[uuid.UUID] = Field(min_length=1)
    fields: list[ObservedField] = Field(min_length=1)
    empty_assertion: EmptyAssertion | None = None


class CalculatedClaim(BaseModel):
    kind: Literal["calculated"] = "calculated"
    text: str
    function: str
    inputs: dict[str, Any]
    expected: int | float
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class InterpretationClaim(BaseModel):
    kind: Literal["interpretation"] = "interpretation"
    text: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    supporting_claim_indices: list[int] = Field(default_factory=list)


Claim = ObservedClaim | CalculatedClaim | InterpretationClaim
