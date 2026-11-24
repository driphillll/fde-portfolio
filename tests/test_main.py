"""Baseline tests demonstrating pytest + FastAPI TestClient.

Run: pytest -q
Note: no network / no Docker needed — this validates the app wiring.
"""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

client = TestClient(create_app(Settings(environment="test")))


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "FDE Portfolio Service"
    assert body["environment"] == "test"
    assert "version" in body


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ready():
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


def test_echo():
    payload = {"message": "hello", "n": 1}
    res = client.post("/v1/echo", json=payload)
    assert res.status_code == 200
    assert res.json()["received"] == payload
    assert res.json()["count"] == 2


def test_request_id_header():
    res = client.get("/health", headers={"x-request-id": "test-123"})
    assert res.headers["x-request-id"] == "test-123"


def test_unknown_route():
    assert client.get("/does-not-exist").status_code == 404
