"""CORS tests.

The Next.js web app calls the API directly from the browser (localhost:3000),
so preflight OPTIONS must be answered for the exact web origin and unknown
origins must be rejected.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_cors_preflight_allows_web_origin(client) -> None:
    resp = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": settings.web_origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == settings.web_origin
    assert "POST" in resp.headers["access-control-allow-methods"]


def test_cors_regular_request_carries_allow_origin(client) -> None:
    resp = client.get("/health", headers={"Origin": settings.web_origin})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == settings.web_origin


def test_cors_rejects_unknown_origin(client) -> None:
    resp = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers
