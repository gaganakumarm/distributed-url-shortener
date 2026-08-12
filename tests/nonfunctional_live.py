"""Repeatable concurrency, latency, and load-distribution checks."""

from concurrent.futures import ThreadPoolExecutor
import json
import statistics
import time
import uuid

import httpx


BASE_URL = "http://localhost"
CLIENT = httpx.Client(base_url=BASE_URL, timeout=15, follow_redirects=False, limits=httpx.Limits(max_connections=50))


def request(method: str, path: str, **kwargs):
    started = time.perf_counter()
    response = CLIENT.request(method, path, **kwargs)
    return response, (time.perf_counter() - started) * 1000


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def main():
    email = f"load-{uuid.uuid4().hex}@example.com"
    auth, _ = request("POST", "/api/auth/register", json={"email": email, "password": "StrongPass123!"})
    auth.raise_for_status()
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

    with ThreadPoolExecutor(max_workers=20) as pool:
        health_results = list(pool.map(lambda _: request("GET", "/health/live"), range(200)))
    statuses = [response.status_code for response, _ in health_results]
    latencies = [latency for _, latency in health_results]
    instances = {response.headers.get("x-api-instance") for response, _ in health_results}

    with ThreadPoolExecutor(max_workers=15) as pool:
        create_results = list(
            pool.map(
                lambda number: request(
                    "POST", "/api/urls", headers=headers, json={"url": f"https://example.com/{number}"}
                ),
                range(30),
            )
        )
    created = [response.json() for response, _ in create_results if response.status_code == 201]
    codes = [item["short_code"] for item in created]

    target = codes[0]
    with ThreadPoolExecutor(max_workers=20) as pool:
        redirect_results = list(pool.map(lambda _: request("GET", f"/{target}"), range(50)))
    stats, _ = request("GET", f"/api/urls/{target}/stats", headers=headers)

    for code in codes:
        request("DELETE", f"/api/urls/{code}", headers=headers)

    report = {
        "health_requests": len(statuses),
        "health_successes": statuses.count(200),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
        },
        "instances_seen": sorted(instance for instance in instances if instance),
        "concurrent_creates": len(create_results),
        "successful_creates": len(created),
        "unique_codes": len(set(codes)),
        "concurrent_redirects": len(redirect_results),
        "successful_redirects": sum(response.status_code == 307 for response, _ in redirect_results),
        "recorded_clicks": stats.json()["total_clicks"],
    }
    print(json.dumps(report, indent=2))

    assert statuses.count(200) == 200
    assert instances == {"api1", "api2"}
    assert percentile(latencies, 0.95) < 1000
    assert len(created) == 30 and len(set(codes)) == 30
    assert all(response.status_code == 307 for response, _ in redirect_results)
    assert stats.json()["total_clicks"] == 50
    CLIENT.close()


if __name__ == "__main__":
    main()
