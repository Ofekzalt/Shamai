from __future__ import annotations

from app.modules.investigation.graph.address import parse_address


def test_parse_address_splits_house_number() -> None:
    assert parse_address("Rothschild 1") == ("Rothschild", "1")
    assert parse_address("Test St, 12") == ("Test St", "12")
