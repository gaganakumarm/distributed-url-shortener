import time

from fastapi import Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram

from app.core.config import settings
from app.services.cache import redis_client


REQUESTS = Counter(
    "url_shortener_http_requests_total",
    "HTTP requests handled by the API",
    ("instance", "method", "route", "status"),
)
LATENCY = Histogram(
    "url_shortener_http_request_duration_seconds",
    "HTTP request duration",
    ("instance", "method", "route"),
)

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return current
"""


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_for(request: Request) -> int | None:
    path = request.url.path
    if path.startswith("/api/auth/"):
        return settings.auth_rate_limit_per_minute
    if path == "/api/urls" and request.method == "POST":
        return settings.write_rate_limit_per_minute
    if request.method == "GET" and not path.startswith(("/api/", "/health", "/metrics", "/docs", "/openapi")):
        return settings.redirect_rate_limit_per_minute
    return None


async def enforce_rate_limit(request: Request):
    limit = rate_limit_for(request)
    if limit is None:
        return None
    bucket = int(time.time() // 60)
    category = "auth" if request.url.path.startswith("/api/auth/") else "write" if request.url.path == "/api/urls" else "redirect"
    key = f"rate:{client_ip(request)}:{category}:{bucket}"
    try:
        count = await redis_client.eval(RATE_LIMIT_SCRIPT, 1, key, 60)
    except Exception:
        return None
    if int(count) > limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60"},
        )
    return None


async def operational_middleware(request: Request, call_next):
    started = time.perf_counter()
    limited = await enforce_rate_limit(request)
    response = limited if limited is not None else await call_next(request)
    route = request.scope.get("route")
    route_name = getattr(route, "path", request.url.path)
    REQUESTS.labels(settings.api_instance, request.method, route_name, response.status_code).inc()
    LATENCY.labels(settings.api_instance, request.method, route_name).observe(time.perf_counter() - started)
    response.headers["X-API-Instance"] = settings.api_instance
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response
