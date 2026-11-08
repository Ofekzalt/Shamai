from __future__ import annotations

import uuid

from app.core.config import Settings
from app.modules.investigation.graph.finalize import finalize_node
from app.modules.investigation.graph.runtime import RUNTIME_KEY, GraphRuntime
from app.modules.investigation.graph.writer import writer_node


def _config() -> dict:
    runtime = GraphRuntime(
        session_factory=lambda: None,  # type: ignore[arg-type, return-value]
        http=None,  # type: ignore[arg-type]
        settings=Settings(),
    )
    return {"configurable": {RUNTIME_KEY: runtime}}


def test_writer_omits_numeric_claims_when_coverage_incomplete() -> None:
    evidence_id = uuid.uuid4()
    state = {
        "request": {"profile": "homebuyer", "asking_price_agorot": 1},
        "agent_results": [
            {
                "agent": "market",
                "findings": {
                    "n_comps": 3,
                    "estimate_agorot": 9_000_000_00,
                    "coverage_status": "incomplete",
                    "limitation": {"code": "coverage_incomplete", "message": "secret boom"},
                },
            }
        ],
        "tool_calls": [{"tool": "find_comparables", "evidence_ids": [str(evidence_id)]}],
        "followup_queue": [],
        "dispatched_followups": [],
    }
    out = writer_node(state, _config())
    paths = [field["path"] for claim in out["claims"] for field in claim.get("fields") or []]
    assert "estimate.value_agorot" not in paths
    assert "selected_count" not in paths
    joined = " ".join(out["missing_information"])
    assert "incomplete" in joined.lower()
    assert "secret boom" not in joined


def test_writer_skips_rejected_paths_on_rewrite() -> None:
    evidence_id = uuid.uuid4()
    state = {
        "request": {},
        "agent_results": [
            {
                "agent": "market",
                "findings": {
                    "n_comps": 5,
                    "estimate_agorot": 4_000_000_00,
                    "coverage_status": "complete",
                },
            }
        ],
        "tool_calls": [{"tool": "find_comparables", "evidence_ids": [str(evidence_id)]}],
        "rejected_claims": [{"path": "estimate.value_agorot", "reason": "mismatch"}],
        "rewrite_count": 1,
        "followup_queue": [],
        "dispatched_followups": [],
    }
    out = writer_node(state, _config())
    paths = [field["path"] for claim in out["claims"] for field in claim.get("fields") or []]
    assert "estimate.value_agorot" not in paths
    assert "selected_count" in paths


def test_finalize_nulls_in_renewal_when_coverage_incomplete() -> None:
    state = {
        "request": {"address": "Rothschild 1", "profile": "homebuyer"},
        "agent_results": [
            {
                "agent": "development",
                "findings": {
                    "renewals": [],
                    "renewal_coverage_status": "incomplete",
                },
            }
        ],
        "claims": [],
        "missing_information": [],
        "uncertainty": [],
        "conflicts": [],
    }
    report = finalize_node(state)["result_json"]
    assert report["in_renewal"] is None
    assert report["n_comps"] is None
    assert report["estimate_agorot"] is None
