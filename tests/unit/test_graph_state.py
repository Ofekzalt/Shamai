from __future__ import annotations

from app.modules.investigation.graph.state import RESET, _add_int, _extend, _extend_unique_followups


def test_extend_reset_replaces_prior_values() -> None:
    assert _extend(["old"], [RESET, "new"]) == ["new"]
    assert _add_int(4, RESET) == 0
    merged = _extend_unique_followups(
        [{"type": "ExplainPricePremium", "source_row_id": "a"}],
        [RESET, {"type": "ExplainPricePremium", "source_row_id": "b"}],
    )
    assert merged == [{"type": "ExplainPricePremium", "source_row_id": "b"}]
