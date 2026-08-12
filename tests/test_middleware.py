from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from app.core.middleware import client_ip, enforce_rate_limit, rate_limit_for


def make_request(path="/api/auth/login", method="POST", headers=None):
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": raw_headers,
            "client": ("127.0.0.1", 1234),
            "server": ("test", 80),
            "scheme": "http",
        }
    )


def test_rate_limit_routes_are_scoped():
    assert rate_limit_for(make_request()) is not None
    assert rate_limit_for(make_request("/api/urls", "POST")) is not None
    assert rate_limit_for(make_request("/abc123", "GET")) is not None
    assert rate_limit_for(make_request("/health/live", "GET")) is None


def test_forwarded_client_ip_is_used():
    assert client_ip(make_request(headers={"X-Forwarded-For": "203.0.113.5"})) == "203.0.113.5"


@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_limit():
    request = make_request()
    with patch("app.core.middleware.redis_client.eval", new=AsyncMock(return_value=31)):
        response = await enforce_rate_limit(request)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


@pytest.mark.asyncio
async def test_rate_limit_fails_open_when_redis_is_unavailable():
    request = make_request()
    with patch("app.core.middleware.redis_client.eval", new=AsyncMock(side_effect=ConnectionError)):
        assert await enforce_rate_limit(request) is None
