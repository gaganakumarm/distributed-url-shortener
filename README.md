# Distributed URL Shortener

Frontend brand: **LinkFlux**

A portfolio-ready distributed URL shortener built with FastAPI, PostgreSQL, Redis, Nginx, Docker Compose, JWT authentication, analytics, caching, health checks, and multiple API instances. It includes a responsive React interface for account access, link creation, copying, analytics, deletion, and live infrastructure status.

## Architecture

```text
Client
  |
  v
Nginx Load Balancer
  |
  +-------> FastAPI api1 ----+
  |                          |
  +-------> FastAPI api2 ----+----> PostgreSQL
                             |
                             +----> Redis
```

## Project screenshots

### Interactive API documentation

![Swagger API documentation](docs/images/swagger-api.png)

### Monitoring dashboard

![Grafana dashboard showing traffic and latency](docs/images/grafana-dashboard.png)

### Distributed services

![Docker Compose services and health status](docs/images/docker-services.png)

## Features

- Responsive React frontend and link-management dashboard
- Register/login with JWT
- Password hashing with Argon2
- Create short URLs
- List user-owned URLs
- Delete user-owned URLs
- Redirect short URLs
- Redis cache-aside behavior
- PostgreSQL persistence
- Click analytics
- Nginx load balancing
- Two FastAPI instances
- Liveness/readiness endpoints
- Docker Compose local deployment
- Unit, integration, concurrency, and resilience tests
- Versioned Alembic database migrations
- Redis-backed distributed rate limiting
- Prometheus metrics and a provisioned Grafana dashboard
- Automated GitHub Actions CI

## Requirements

Install:

- Docker Desktop
- Git (optional)
- curl or PowerShell

No local PostgreSQL or Redis installation is required.

## 1. Configure environment

Copy:

```powershell
Copy-Item .env.example .env
```

Open `.env` and change:

```text
SECRET_KEY=change-me-to-a-long-random-secret
```

You can generate one in PowerShell with Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 2. Build and run

From the project folder:

```powershell
docker compose up --build
```

Wait until the Alembic migration job completes and the containers are healthy.

Open:

```text
http://localhost
http://localhost/docs
http://localhost/health/ready
http://localhost:9090
http://localhost:3000
```

Swagger UI is available at:

```text
http://localhost/docs
```

Prometheus is available on port `9090`. Grafana is available on port `3000`;
use `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` from `.env`. The
"Distributed URL Shortener" dashboard is provisioned automatically.

Before sharing or deploying the project, set a unique Grafana password in
`.env` as well as the application `SECRET_KEY`.

## 3. Register

PowerShell:

```powershell
$body = @{
  email = "gagana@example.com"
  password = "StrongPass123!"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost/api/auth/register" `
  -ContentType "application/json" `
  -Body $body
```

Copy the `access_token` returned.

## 4. Store token

```powershell
$token = "PASTE_TOKEN_HERE"
$headers = @{
  Authorization = "Bearer $token"
}
```

## 5. Create short URL

```powershell
$body = @{
  url = "https://www.wikipedia.org/"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost/api/urls" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

Example result:

```json
{
  "id": 1,
  "short_code": "Ab3Xk91Q",
  "short_url": "http://localhost/Ab3Xk91Q",
  "original_url": "https://www.wikipedia.org/",
  "created_at": "..."
}
```

## 6. Test redirect

Open the returned short URL in your browser:

```text
http://localhost/Ab3Xk91Q
```

You should be redirected to Wikipedia.

## 7. List your URLs

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://localhost/api/urls" `
  -Headers $headers
```

## 8. Check analytics

Replace the code:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://localhost/api/urls/Ab3Xk91Q/stats" `
  -Headers $headers
```

## 9. Delete a short URL

```powershell
Invoke-RestMethod `
  -Method Delete `
  -Uri "http://localhost/api/urls/Ab3Xk91Q" `
  -Headers $headers
```

## 10. See distributed instances

Run:

```powershell
docker compose ps
```

You should see:

- postgres
- redis
- api1
- api2
- nginx

Nginx sends incoming traffic to both FastAPI containers.

To watch API logs:

```powershell
docker compose logs -f api1 api2
```

Then make repeated requests and inspect the response header:

```powershell
1..10 | ForEach-Object {
  (Invoke-WebRequest "http://localhost/health/live").Headers["X-API-Instance"]
}
```

You should see `api1` and `api2` appearing across requests.

## 11. Stop

```powershell
docker compose down
```

Preserve database volumes.

To remove everything including data:

```powershell
docker compose down -v
```

## 12. Run tests locally

Create virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

The included unit tests do not require PostgreSQL/Redis.

Run the repeatable black-box functional suite while Docker Compose is running:

```powershell
$env:RUN_LIVE_TESTS = "1"
pytest tests/test_live_system.py
Remove-Item Env:RUN_LIVE_TESTS
```

Run the concurrency, latency, load-balancing, and analytics checks:

```powershell
python tests/nonfunctional_live.py
```

## Database migrations

Docker Compose applies committed migrations automatically before either API
instance starts. After changing SQLAlchemy models, generate and review a new
migration while the database is running:

```powershell
docker compose run --rm migrate alembic revision --autogenerate -m "describe change"
docker compose run --rm migrate alembic upgrade head
```

Commit every new file created under `migrations/versions/`.

## Rate limiting

Authentication, URL creation, and public redirects have independent limits.
Configure them in `.env` with `AUTH_RATE_LIMIT_PER_MINUTE`,
`WRITE_RATE_LIMIT_PER_MINUTE`, and `REDIRECT_RATE_LIMIT_PER_MINUTE`. Limits are
shared by both API instances through Redis. If Redis is unavailable, requests
continue through PostgreSQL and readiness reports `degraded`.

## API summary

| Method | Endpoint | Auth | Purpose |
|---|---|---:|---|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Login |
| POST | `/api/urls` | Yes | Shorten URL |
| GET | `/api/urls` | Yes | List own URLs |
| GET | `/api/urls/{code}/stats` | Yes | Click count |
| DELETE | `/api/urls/{code}` | Yes | Delete own URL |
| GET | `/{code}` | No | Redirect |
| GET | `/health/live` | No | Liveness |
| GET | `/health/ready` | No | Dependency readiness |

## Portfolio demo sequence

1. Show architecture.
2. Run `docker compose ps`.
3. Show api1 and api2.
4. Register/login through Swagger.
5. Create a shortened URL.
6. Open it and demonstrate redirect.
7. Open it several times.
8. Show stats increasing.
9. Show Redis and PostgreSQL containers.
10. Stop Redis and demonstrate redirects still work through PostgreSQL:
   `docker compose stop redis`
11. Check `/health/ready`; Redis becomes false while PostgreSQL remains healthy.
12. Restart Redis:
   `docker compose start redis`
13. Show both API logs to explain load balancing.

## Important design note

This project deliberately prioritizes clarity and interviewability. For true internet-scale operation, click analytics should be moved off the redirect request path into an event queue/background consumer, database schema migrations should be managed with Alembic, and rate limiting/observability should be added.
