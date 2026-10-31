from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import AddressNotGeocodedError
from app.modules.property_data.service import geocode_address


def test_geocode_uses_cache_on_second_call(db_session) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        payload = {
            "features": [
                {
                    "attributes": {
                        "lon": 34.7818,
                        "lat": 32.0853,
                        "t_shchuna": "לב העיר",
                    }
                }
            ]
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    first = geocode_address(db_session, client, street="Test", house_number="1")
    second = geocode_address(db_session, client, street="Test", house_number="1")
    db_session.flush()

    assert first.lon == second.lon
    assert calls["n"] == 1


def test_geocode_accepts_any_municipal_neighborhood(db_session) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        payload = {
            "features": [
                {
                    "attributes": {
                        "lon": 34.78,
                        "lat": 32.08,
                        "t_shchuna": "שכונה שלא ברשימה",
                    }
                }
            ]
        }
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    record = geocode_address(db_session, client, street="Other", house_number="2")
    assert record.neighborhood == "שכונה שלא ברשימה"


def test_geocode_miss_raises_not_geocoded(db_session) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"features": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(AddressNotGeocodedError):
        geocode_address(db_session, client, street="Missing", house_number="99")
