# LinkFlux Technical Specification

**Document version:** 1.0  
**Application version:** 1.0  
**Status:** Implemented and verified  
**Runtime target:** Local Docker Compose on Windows, macOS, or Linux

## 1. Purpose

This document specifies the functional behavior, interfaces, data contracts,
configuration, quality attributes, acceptance criteria, and operational
requirements of LinkFlux. It is the implementation contract for the current
repository. For component relationships and architectural rationale, see the
[Architecture Report](ARCHITECTURE.md).

## 2. Scope

### 2.1 Included

- Browser-based registration and login.
- JWT-authenticated link management.
- HTTP(S) URL shortening using random shortcodes.
- Public redirects and click counting.
- Per-user link listing, analytics, copying, and deletion.
- Redis cache-aside lookup and distributed rate limiting.
- Two load-balanced API replicas.
- Health/readiness reporting.
- Prometheus metrics and Grafana visualization.
- Alembic schema migrations.
- Containerized local execution and automated CI verification.

### 2.2 Excluded

- Password reset and email verification.
- Social login or multi-factor authentication.
- Custom shortcodes and link expiration.
- Link editing, folders, tags, and bulk operations.
- Geographic/device analytics.
- Public cloud hosting, custom domains, and TLS termination.
- Multi-host clustering and highly available databases.

## 3. Technology baseline

| Layer | Technology | Version |
|---|---|---:|
| Frontend runtime | React | 19.2.8 |
| Frontend build | Vite | 8.2.1 |
| Frontend icons | Lucide React | 1.31.0 |
| API framework | FastAPI | 0.116.1 |
| ASGI server | Uvicorn | 0.35.0 |
| Validation | Pydantic | 2.11.7 |
| ORM | SQLAlchemy | 2.0.43 |
| PostgreSQL driver | asyncpg | 0.30.0 |
| Migrations | Alembic | 1.16.5 |
| Authentication | python-jose | 3.5.0 |
| Password hashing | Passlib / Argon2 | 1.7.4 / 25.1.0 |
| Redis client | redis-py asyncio | 6.4.0 |
| Metrics client | prometheus-client | 0.25.0 |
| Database | PostgreSQL Alpine | 17 |
| Cache | Redis Alpine | 8 |
| Gateway/frontend server | Nginx Alpine | 1.29 |
| Metrics server | Prometheus | 3.5.0 |
| Dashboard | Grafana | 12.1.0 |
| API container runtime | Python slim | 3.12 |
| Frontend build runtime | Node Alpine | 22 |

## 4. User roles

| Role | Description | Permissions |
|---|---|---|
| Visitor | Unauthenticated browser or API client | View frontend, inspect health, register, log in, follow valid short links |
| Authenticated user | Visitor with a valid JWT for an existing user | Create links, list own links, view own statistics, delete own links |
| Operator | Person with local Docker/Grafana access | Start/stop services, inspect health and logs, view operational metrics, run migrations/tests |

There is no application-level administrator role.

## 5. Functional requirements

### 5.1 Authentication

| ID | Requirement |
|---|---|
| AUTH-01 | The system shall accept a syntactically valid email and an 8–128 character password for registration. |
| AUTH-02 | Email addresses shall be normalized to lowercase before persistence and lookup. |
| AUTH-03 | The system shall reject a duplicate email with HTTP 409, including concurrent duplicate registration attempts. |
| AUTH-04 | Passwords shall be persisted only as Argon2 hashes. |
| AUTH-05 | Successful registration and login shall return a bearer JWT. |
| AUTH-06 | Invalid credentials shall return HTTP 401 without identifying whether the email or password was incorrect. |
| AUTH-07 | Malformed, expired, or unknown-user tokens shall return HTTP 401. |
| AUTH-08 | The frontend shall store the JWT under `linkflux_token` in browser local storage and attach it as a bearer token. |

### 5.2 Link management

| ID | Requirement |
|---|---|
| LINK-01 | An authenticated user shall create a link from a valid HTTP or HTTPS URL. |
| LINK-02 | The default shortcode shall contain eight characters from `A-Z`, `a-z`, and `0-9`. |
| LINK-03 | Shortcode length shall be configurable between 4 and 32 characters. |
| LINK-04 | The database shall enforce global shortcode uniqueness. |
| LINK-05 | A shortcode conflict shall be retried up to ten times before returning HTTP 503. |
| LINK-06 | Created links shall be returned with identifier, shortcode, public short URL, original URL, and creation timestamp. |
| LINK-07 | Users shall list only links they own, newest first. |
| LINK-08 | Users shall view click counts only for links they own. |
| LINK-09 | Users shall delete only links they own. |
| LINK-10 | Access to another user's link-management resource shall return HTTP 404 to avoid disclosing its existence. |
| LINK-11 | The frontend shall provide create, copy, open, refresh, analytics, and delete controls. |

### 5.3 Redirects and analytics

| ID | Requirement |
|---|---|
| REDIR-01 | A valid shortcode shall return HTTP 307 with the original URL in `Location`. |
| REDIR-02 | An unknown shortcode shall return HTTP 404. |
| REDIR-03 | The system shall attempt to record one click event per redirect request. |
| REDIR-04 | Referrer and user-agent values shall be truncated to 512 characters before persistence. |
| REDIR-05 | A click-recording failure shall not block an already-resolved redirect. |
| REDIR-06 | Deleting a link shall remove its click events through database cascade and invalidate its cache entry. |

### 5.4 Health and status

| ID | Requirement |
|---|---|
| HEALTH-01 | `/health/live` shall return HTTP 200 and `{"status":"ok"}` while the API process can serve requests. |
| HEALTH-02 | `/health/ready` shall test PostgreSQL with `SELECT 1` and Redis with `PING`. |
| HEALTH-03 | Healthy PostgreSQL and Redis shall return HTTP 200 with status `ready`. |
| HEALTH-04 | Healthy PostgreSQL and failed Redis shall return HTTP 200 with status `degraded`. |
| HEALTH-05 | Failed PostgreSQL shall return HTTP 503 with status `not_ready`. |
| HEALTH-06 | The frontend status screen shall refresh automatically every 15 seconds and allow manual refresh. |

## 6. Frontend specification

### 6.1 Routes

The frontend uses hash routing to avoid conflicts with public shortcode paths.

| Browser URL | Screen | Authentication |
|---|---|---|
| `/#/home` or `/` | Landing page | Optional |
| `/#/register` | Registration | No |
| `/#/login` | Login | No |
| `/#/dashboard` | My Links dashboard | Yes |
| `/#/status` | System status | Optional |

If the page hash is absent, authenticated browsers default to the dashboard and
unauthenticated browsers default to the landing page.

### 6.2 Dashboard behavior

- Link and statistics requests are made after dashboard load.
- Total clicks are derived by summing per-link statistics.
- Successful creation inserts the new link at the start of the current list.
- Copy uses the browser Clipboard API and displays temporary confirmation.
- Deletion requires browser confirmation before issuing the request.
- HTTP/API errors are displayed as user-visible messages.
- A 401 response clears the locally stored token.

### 6.3 Responsive behavior

- The primary breakpoint is 760 CSS pixels.
- Desktop navigation becomes a toggleable mobile menu below the breakpoint.
- Feature and service grids collapse to one column.
- Link rows reorganize controls beneath link details.
- Forms and primary actions expand to the available width.

### 6.4 Browser requirements

The browser shall support ES modules, `fetch`, `localStorage`, URL hashes, and
the Clipboard API. Current evergreen Chrome, Edge, Firefox, and Safari releases
are the intended clients.

## 7. HTTP API specification

All request and response bodies use `application/json` except redirects and
empty HTTP 204 responses. Protected endpoints require:

```http
Authorization: Bearer <access_token>
```

### 7.1 Endpoint summary

| Method | Path | Auth | Success | Description |
|---|---|---:|---:|---|
| POST | `/api/auth/register` | No | 201 | Register and issue token |
| POST | `/api/auth/login` | No | 200 | Authenticate and issue token |
| POST | `/api/urls` | Yes | 201 | Create short URL |
| GET | `/api/urls` | Yes | 200 | List owned URLs |
| GET | `/api/urls/{short_code}/stats` | Yes | 200 | Get owned URL click count |
| DELETE | `/api/urls/{short_code}` | Yes | 204 | Delete owned URL |
| GET | `/{short_code}` | No | 307 | Redirect to destination |
| GET | `/health/live` | No | 200 | Process liveness |
| GET | `/health/ready` | No | 200/503 | Dependency readiness |

### 7.2 Registration

```http
POST /api/auth/register
```

Request:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

Response `201 Created`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Errors: `409 Email already registered`, `422 validation error`, `429 rate limit exceeded`.

### 7.3 Login

```http
POST /api/auth/login
```

Request and response use the registration shapes. Errors: `401 Invalid
credentials`, `422 validation error`, `429 rate limit exceeded`.

### 7.4 Create URL

```http
POST /api/urls
```

Request:

```json
{
  "url": "https://example.com/path"
}
```

Response `201 Created`:

```json
{
  "id": 1,
  "short_code": "Ab3Xk91Q",
  "short_url": "http://localhost/Ab3Xk91Q",
  "original_url": "https://example.com/path",
  "created_at": "2026-08-12T12:00:00Z"
}
```

Errors: `401`, `422`, `429`, `503 Could not generate unique short code`.

### 7.5 List URLs

```http
GET /api/urls
```

Response `200 OK`: JSON array of URL response objects. An account with no links
receives `[]`.

### 7.6 URL statistics

```http
GET /api/urls/{short_code}/stats
```

Response:

```json
{
  "short_code": "Ab3Xk91Q",
  "total_clicks": 5
}
```

Errors: `401`, `404 URL not found`.

### 7.7 Delete URL

```http
DELETE /api/urls/{short_code}
```

Response: `204 No Content` with no body. Errors: `401`, `404 URL not found`.

### 7.8 Public redirect

```http
GET /{short_code}
```

Response: `307 Temporary Redirect` and a `Location` header. Errors: `404 Short
URL not found`, `429 Rate limit exceeded`.

## 8. Common error contract

Application errors follow FastAPI's detail format:

```json
{
  "detail": "Human-readable message"
}
```

Validation errors return HTTP 422 with a structured `detail` array containing
field locations, messages, and validation types. Rate-limited responses include:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

## 9. Data specification

### 9.1 `users`

| Column | Type | Null | Constraint |
|---|---|---:|---|
| `id` | integer | No | Primary key |
| `email` | varchar(320) | No | Unique indexed |
| `password_hash` | varchar(255) | No | Argon2 encoded hash |
| `created_at` | timestamptz | No | Server default `now()` |

### 9.2 `short_urls`

| Column | Type | Null | Constraint |
|---|---|---:|---|
| `id` | integer | No | Primary key |
| `short_code` | varchar(32) | No | Unique indexed |
| `original_url` | text | No | Validated HTTP(S) URL at creation |
| `owner_id` | integer | No | Indexed FK to `users.id`, cascade delete |
| `created_at` | timestamptz | No | Server default `now()` |

### 9.3 `click_events`

| Column | Type | Null | Constraint |
|---|---|---:|---|
| `id` | integer | No | Primary key |
| `url_id` | integer | No | Indexed FK to `short_urls.id`, cascade delete |
| `referrer` | varchar(512) | Yes | Truncated at ingestion |
| `user_agent` | varchar(512) | Yes | Truncated at ingestion |
| `clicked_at` | timestamptz | No | Server default `now()` |

## 10. Redis key specification

| Key pattern | Value | TTL | Purpose |
|---|---|---:|---|
| `url:{short_code}` | JSON `{url_id, original_url}` | `CACHE_TTL_SECONDS` | Redirect lookup cache |
| `rate:{client_ip}:auth:{minute}` | Integer counter | 60 seconds | Registration/login rate limit |
| `rate:{client_ip}:write:{minute}` | Integer counter | 60 seconds | Link-creation rate limit |
| `rate:{client_ip}:redirect:{minute}` | Integer counter | 60 seconds | Public redirect rate limit |

Cache operations and rate-limit evaluation shall not propagate Redis connection
errors to callers.

## 11. Configuration specification

| Variable | Default/example | Requirement |
|---|---|---|
| `APP_NAME` | `Distributed URL Shortener` | FastAPI title |
| `ENVIRONMENT` | `development` | Use `production`/`prod` to enforce secret validation |
| `SECRET_KEY` | example placeholder | Unique minimum 32 characters in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime |
| `POSTGRES_USER` | `urluser` | Local PostgreSQL initialization |
| `POSTGRES_PASSWORD` | `urlpass` | Local PostgreSQL initialization |
| `POSTGRES_DB` | `urldb` | Local PostgreSQL initialization |
| `DATABASE_URL` | asyncpg URL | SQLAlchemy asynchronous connection URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `CACHE_TTL_SECONDS` | `3600` | Redirect cache duration |
| `BASE_URL` | `http://localhost` | Prefix returned for generated short URLs |
| `SHORT_CODE_LENGTH` | `8` | Integer from 4 through 32 |
| `API_INSTANCE` | assigned by Compose | Response/metrics replica label |
| `AUTH_RATE_LIMIT_PER_MINUTE` | `30` | Shared per-IP authentication limit |
| `WRITE_RATE_LIMIT_PER_MINUTE` | `120` | Shared per-IP creation limit |
| `REDIRECT_RATE_LIMIT_PER_MINUTE` | `600` | Shared per-IP redirect limit |
| `GRAFANA_ADMIN_USER` | `admin` | Local Grafana administrator |
| `GRAFANA_ADMIN_PASSWORD` | example placeholder | Must be changed by the operator |

The `.env` file shall not be committed. `.env.example` defines required names
without containing deployable secrets.

## 12. Rate-limit specification

| Category | Requests included | Default/minute/IP |
|---|---|---:|
| Authentication | `/api/auth/*` | 30 |
| Write | `POST /api/urls` | 120 |
| Redirect | Public GET paths excluding API, health, metrics, docs, and OpenAPI | 600 |

Fixed-window counters use the Unix minute as a bucket. Nginx overwrites
`X-Forwarded-For` with the direct client address so caller-supplied forwarding
chains cannot select arbitrary rate-limit identities.

## 13. Security requirements

| ID | Requirement |
|---|---|
| SEC-01 | Production shall use a unique JWT secret of at least 32 characters. |
| SEC-02 | Passwords shall never appear in responses, logs, screenshots, or committed configuration. |
| SEC-03 | Management endpoints shall enforce bearer authentication and ownership. |
| SEC-04 | The public gateway shall return 404 for `/metrics` and descendants. |
| SEC-05 | API responses shall include `nosniff`, frame denial, no-referrer, and restrictive permissions headers. |
| SEC-06 | The API container shall execute as a non-root system user. |
| SEC-07 | Only Nginx shall expose the user-facing application port. |
| SEC-08 | Public deployments shall use HTTPS before accepting real user credentials. |

## 14. Observability specification

### 14.1 Metrics

| Metric | Type | Labels |
|---|---|---|
| `url_shortener_http_requests_total` | Counter | `instance`, `method`, `route`, `status` |
| `url_shortener_http_request_duration_seconds` | Histogram | `instance`, `method`, `route` |

Prometheus shall scrape `api1:8000/metrics/` and `api2:8000/metrics/` every 15
seconds. Grafana shall provision the Prometheus datasource automatically.

### 14.2 Dashboard panels

- Requests per second by API instance.
- p95 request latency by route.
- HTTP 4xx/5xx error rate by status.

### 14.3 Instance tracing

Every API response shall include:

```http
X-API-Instance: api1
```

or `api2`, according to the serving replica.

## 15. Non-functional requirements

### 15.1 Availability and resilience

| ID | Requirement |
|---|---|
| NFR-AV-01 | Loss of Redis shall not prevent URL resolution through PostgreSQL. |
| NFR-AV-02 | Loss of one API replica shall allow Nginx to use the remaining healthy replica after failure detection/recovery configuration. |
| NFR-AV-03 | Failed schema migration shall prevent API startup. |
| NFR-AV-04 | Nginx shall wait for healthy frontend and API containers during normal Compose startup. |

### 15.2 Performance targets

These are local acceptance targets, not public SLAs:

| ID | Target |
|---|---|
| NFR-PERF-01 | 200 concurrent pooled health requests complete with 100% HTTP 200 responses. |
| NFR-PERF-02 | Local p95 health latency remains below 1,000 ms. |
| NFR-PERF-03 | 30 concurrent link creations produce 30 successful, distinct shortcodes. |
| NFR-PERF-04 | 50 concurrent redirect requests return HTTP 307 and produce 50 recorded clicks. |

The latest measured local run completed 200/200 health requests with p95 below
200 ms; machine load and Docker resources can affect repeated measurements.

### 15.3 Maintainability

- Backend concerns shall remain separated into API, core, database, models,
  schemas, and services packages.
- Schema changes shall be delivered through reviewed Alembic revisions.
- Runtime dependencies shall be version-pinned.
- Frontend production assets shall be reproducible through `npm ci` and
  `npm run build`.
- CI shall run on pushes and pull requests.

## 16. Container and network specification

| Service | Host port | Health criterion | Persistence |
|---|---:|---|---|
| `nginx` | 80 | Container running and dependencies healthy | None |
| `frontend` | None | HTTP 200 from `127.0.0.1/` | Immutable image |
| `api1` | None | HTTP success from `/health/ready` | Stateless |
| `api2` | None | HTTP success from `/health/ready` | Stateless |
| `migrate` | None | Exit code 0 | Alembic revision table in PostgreSQL |
| `postgres` | None | `pg_isready` | `postgres_data` |
| `redis` | None | `redis-cli ping` | `redis_data` with AOF |
| `prometheus` | 9090 | Prometheus health | `prometheus_data` |
| `grafana` | 3000 | Grafana process health | `grafana_data` |

All containers join the bridge network `urlnet` and resolve each other by
Compose service name.

## 17. Startup dependencies

1. PostgreSQL and Redis start and pass health checks.
2. The `migrate` service waits for PostgreSQL and runs `alembic upgrade head`.
3. API replicas wait for PostgreSQL, Redis, and successful migration completion.
4. The frontend starts and passes its HTTP health check.
5. Nginx waits for both API replicas and the frontend to become healthy.
6. Prometheus waits for API health; Grafana waits for Prometheus startup.

## 18. Build specification

### 18.1 Backend image

- Base: `python:3.12-slim`.
- Installs pinned `requirements.txt` packages.
- Copies API application and Alembic configuration.
- Executes as the non-root `app` user.
- Starts Uvicorn on `0.0.0.0:8000`.

### 18.2 Frontend image

- Stage 1 uses `node:22-alpine`, installs from the lockfile/package manifest,
  and creates a Vite production build.
- Stage 2 uses `nginx:1.29-alpine` and serves immutable built assets.
- Unknown frontend paths fall back to `index.html`.

## 19. Test and acceptance specification

### 19.1 Local test suite

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Acceptance: all non-live tests pass; live tests may be skipped unless explicitly
enabled.

### 19.2 Frontend build

```powershell
Set-Location frontend
npm ci
npm run build
```

Acceptance: build exits with code 0 and creates `frontend/dist`.

### 19.3 Live functional suite

```powershell
docker compose up -d --build --wait
$env:RUN_LIVE_TESTS = "1"
.venv\Scripts\python.exe -m pytest tests\test_live_system.py -q
Remove-Item Env:RUN_LIVE_TESTS
```

Acceptance includes frontend delivery, healthy dependencies, authentication,
duplicate handling, validation, ownership isolation, URL lifecycle, redirects,
click counting, oversized headers, and controlled concurrent registration.

### 19.4 Non-functional suite

```powershell
.venv\Scripts\python.exe tests\nonfunctional_live.py
```

Acceptance uses the targets in section 15.2 and verifies that traffic reaches
both API instances.

### 19.5 CI acceptance

Both GitHub Actions jobs, `test` and `integration`, shall conclude successfully
for a commit to be considered verified.

## 20. Migration specification

- Current head revision: `20260812_0001`.
- Compose applies all pending revisions before API startup.
- New model changes require an autogenerated revision that is manually reviewed.
- Migration files under `migrations/versions` shall be committed with the model
  change.
- Downgrades are supported by revision functions but must be tested before use
  against valuable data.

## 21. Operational procedures

### Start

```powershell
docker compose up -d --build --wait
```

### Verify

```powershell
docker compose ps
Invoke-RestMethod http://localhost/health/ready
```

Expected readiness:

```json
{"status":"ready","postgres":true,"redis":true}
```

### Stop without deleting data

```powershell
docker compose down
```

### Destructive reset

```powershell
docker compose down -v
```

The reset command permanently removes all Compose-managed PostgreSQL, Redis,
Prometheus, and Grafana volumes.

## 22. Known constraints

- Local HTTP is appropriate only for development and demonstration.
- JWT logout is client-side; issued tokens are not centrally revoked.
- Local storage is accessible to JavaScript and therefore depends on preventing
  cross-site scripting.
- Analytics insertion is synchronous and can increase redirect latency.
- Click counts perform an aggregate database query per link.
- The dashboard loads statistics with one request per link.
- The fixed-window limiter can allow bursts at minute boundaries.
- Redis failure intentionally disables rate limiting.
- Single PostgreSQL, Redis, Nginx, Prometheus, and Grafana containers remain
  local single points of failure.

## 23. Completion criteria

The current release is complete when all of the following are true:

- All Compose services start successfully and required services are healthy.
- Alembic reports revision `20260812_0001` at head.
- Registration, login, creation, copy, redirect, statistics, and deletion work.
- Both API instances appear in response headers under repeated traffic.
- Redis outage produces degraded readiness while redirects remain functional.
- Prometheus reports both API scrape targets up.
- Grafana loads the provisioned dashboard.
- Backend tests, frontend build, live tests, and both CI jobs pass.
- No `.env`, password, token, or private connection string is tracked by Git.
