"""Black-box tests for a running Docker Compose stack.

Run with: ``$env:RUN_LIVE_TESTS=1; pytest tests/test_live_system.py``
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 to test the live stack",
)

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost")


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10, follow_redirects=False) as value:
        yield value


def new_account(client: httpx.Client):
    email = f"test-{uuid.uuid4().hex}@example.com"
    password = "StrongPass123!"
    response = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201
    return email, password, {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_and_instance_header(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "postgres": True, "redis": True}
    assert ready.headers["x-api-instance"] in {"api1", "api2"}


def test_authentication_lifecycle(client):
    email, password, headers = new_account(client)
    assert client.post("/api/auth/register", json={"email": email.upper(), "password": password}).status_code == 409
    assert client.post("/api/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401
    login = client.post("/api/auth/login", json={"email": email.upper(), "password": password})
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert client.get("/api/urls", headers=headers).status_code == 200
    assert client.get("/api/urls", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_url_lifecycle_ownership_and_validation(client):
    _, _, owner_headers = new_account(client)
    _, _, other_headers = new_account(client)

    assert client.post("/api/urls", json={"url": "not-a-url"}, headers=owner_headers).status_code == 422
    created = client.post("/api/urls", json={"url": "https://example.com/path"}, headers=owner_headers)
    assert created.status_code == 201
    payload = created.json()
    code = payload["short_code"]
    assert payload["short_url"].endswith(f"/{code}")

    listed = client.get("/api/urls", headers=owner_headers)
    assert listed.status_code == 200
    assert code in {item["short_code"] for item in listed.json()}
    assert client.get(f"/api/urls/{code}/stats", headers=other_headers).status_code == 404
    assert client.delete(f"/api/urls/{code}", headers=other_headers).status_code == 404

    redirected = client.get(f"/{code}")
    assert redirected.status_code == 307
    assert redirected.headers["location"] == "https://example.com/path"
    stats = client.get(f"/api/urls/{code}/stats", headers=owner_headers)
    assert stats.status_code == 200
    assert stats.json()["total_clicks"] == 1

    assert client.delete(f"/api/urls/{code}", headers=owner_headers).status_code == 204
    assert client.get(f"/{code}").status_code == 404
    assert client.get(f"/api/urls/{code}/stats", headers=owner_headers).status_code == 404


def test_unknown_shortcode_returns_404(client):
    assert client.get(f"/missing-{uuid.uuid4().hex}").status_code == 404


def test_long_tracking_headers_do_not_break_redirect(client):
    _, _, headers = new_account(client)
    created = client.post("/api/urls", json={"url": "https://example.com/headers"}, headers=headers).json()
    code = created["short_code"]
    response = client.get(f"/{code}", headers={"Referer": "r" * 600, "User-Agent": "u" * 600})
    assert response.status_code == 307
    assert client.get(f"/api/urls/{code}/stats", headers=headers).json()["total_clicks"] == 1
    assert client.delete(f"/api/urls/{code}", headers=headers).status_code == 204


def test_concurrent_duplicate_registration_is_controlled(client):
    email = f"race-{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "StrongPass123!"}

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(lambda _: client.post("/api/auth/register", json=payload).status_code, range(10)))

    assert statuses.count(201) == 1
    assert statuses.count(409) == 9
