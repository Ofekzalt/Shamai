from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.types import RunnableConfig

from app.core.logging import log_extra
from app.modules.evidence.claims import CalculatedClaim, InterpretationClaim, ObservedClaim
from app.modules.evidence.store import list_run_evidence
from app.modules.evidence.verifier import EvidenceView, VerifyStatus, verify_claim
from app.modules.investigation.graph.runtime import get_runtime, node_session
from app.modules.investigation.graph.state import RunState

MAX_REWRITES = 2

logger = logging.getLogger(__name__)


def _parse_claim(raw: dict[str, Any]):
    kind = raw.get("kind")
    if kind == "observed":
        return ObservedClaim.model_validate(raw)
    if kind == "calculated":
        return CalculatedClaim.model_validate(raw)
    return InterpretationClaim.model_validate(raw)


def verify_node(state: RunState, config: RunnableConfig) -> dict[str, Any]:
    runtime = get_runtime(config)
    judge = runtime.interpretation_judge or (lambda _claim: True)
    run_id = uuid.UUID(state["job_id"])
    with node_session(runtime) as session:
        rows = list_run_evidence(session, run_id)
        evidence = {
            row.id: EvidenceView(payload=row.payload, coverage_status=row.coverage_status)
            for row in rows
        }
    kept: list[dict[str, Any]] = []
    rejected_claims: list[dict[str, Any]] = []
    uncertainty = list(state.get("uncertainty") or [])
    rejected_count = 0
    qualified_count = 0
    for raw in state.get("claims") or []:
        claim = _parse_claim(raw)
        outcome = verify_claim(claim, evidence, judge=judge)
        dumped = claim.model_dump(mode="json")
        dumped["verify_status"] = outcome.status.value
        if outcome.status == VerifyStatus.REJECT:
            rejected_count += 1
            paths = []
            if isinstance(claim, ObservedClaim):
                paths = [field.path for field in claim.fields]
            rejected_claims.extend(
                {"path": path, "reason": outcome.reason or "claim failed verification"}
                for path in (paths or ["_claim"])
            )
            uncertainty.append(outcome.reason or "claim failed verification")
            continue
        if outcome.status == VerifyStatus.QUALIFIED:
            qualified_count += 1
            dumped["text"] = f"Qualified: {dumped.get('text')}"
            uncertainty.append(outcome.reason or "interpretation qualified")
        kept.append(dumped)
    rewrite_count = int(state.get("rewrite_count") or 0)
    if rejected_count or qualified_count:
        logger.warning(
            "claims verification issues",
            extra=log_extra(
                event="investigation.verification",
                rejected_count=rejected_count,
                qualified_count=qualified_count,
                rewrite_count=rewrite_count,
            ),
        )
    if rejected_claims and rewrite_count < MAX_REWRITES:
        return {
            "claims": kept,
            "rejected_claims": rejected_claims,
            "rewrite_count": rewrite_count + 1,
            "uncertainty": uncertainty,
            "phase": "rewrite",
        }
    return {
        "claims": kept,
        "rejected_claims": rejected_claims,
        "uncertainty": uncertainty,
        "phase": "finalize",
    }


def route_after_verify(state: RunState) -> str:
    if state.get("phase") == "rewrite":
        return "writer"
    return "finalize"
