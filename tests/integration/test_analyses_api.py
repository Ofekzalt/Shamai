from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app

VALID_BODY = {
    "address": "רothschild 1, Tel Aviv",
    "asking_price_agorot": 5_000_000_00,
    "size_sqm": 85.0,
    "profile": "homebuyer",
}


@pytest.fixture
def api_client(db_session: Session):
    def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_create_analysis_requires_idempotency_key(api_client: TestClient) -> None:
    response = api_client.post("/analyses", json=VALID_BODY)
    assert response.status_code == 422


def test_create_analysis_validation_error(api_client: TestClient) -> None:
    response = api_client.post(
        "/analyses",
        json={"address": "x", "asking_price_agorot": 0, "size_sqm": 1, "profile": "homebuyer"},
        headers={"Idempotency-Key": "key-validation"},
    )
    assert response.status_code == 422


def test_create_analysis_idempotent(api_client: TestClient) -> None:
    headers = {"Idempotency-Key": "key-idem-1"}
    first = api_client.post("/analyses", json=VALID_BODY, headers=headers)
    assert first.status_code == 202
    body1 = first.json()
    second = api_client.post("/analyses", json=VALID_BODY, headers=headers)
    assert second.status_code == 200
    assert second.json() == body1


def test_create_analysis_idempotency_conflict(api_client: TestClient) -> None:
    key = "key-conflict"
    first = api_client.post(
        "/analyses",
        json=VALID_BODY,
        headers={"Idempotency-Key": key},
    )
    assert first.status_code == 202
    other = {**VALID_BODY, "size_sqm": 90.0}
    conflict = api_client.post(
        "/analyses",
        json=other,
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409


def test_get_analysis_not_found(api_client: TestClient) -> None:
    missing = uuid.uuid4()
    response = api_client.get(f"/analyses/{missing}")
    assert response.status_code == 404


def test_get_report_not_ready(api_client: TestClient) -> None:
    created = api_client.post(
        "/analyses",
        json=VALID_BODY,
        headers={"Idempotency-Key": "key-report-not-ready"},
    )
    analysis_id = created.json()["id"]
    response = api_client.get(f"/analyses/{analysis_id}/report")
    assert response.status_code == 404
