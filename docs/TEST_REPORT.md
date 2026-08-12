# LinkFlux Test Report

**Report version:** 1.0  
**Test execution date:** 12 August 2026  
**Tested revision:** `8156a46` plus this documentation-only report change  
**Environment:** Windows host, Docker Desktop, local Docker Compose network  
**Overall result:** **PASS**

## 1. Purpose

This report records the functional and non-functional verification of the
LinkFlux distributed URL shortener. Results are based on fresh automated and
live executions against the current repository and running Docker stack.

Related documents:

- [Architecture Report](ARCHITECTURE.md)
- [Technical Specification](TECHNICAL_SPECIFICATION.md)

## 2. Test objectives

The test campaign verified that:

- Backend modules compile and regression tests pass.
- The React frontend builds into optimized production assets.
- Docker Compose configuration is valid.
- The frontend and API are available through the Nginx gateway.
- Authentication, authorization, URL management, redirects, and analytics work.
- Concurrent requests are handled correctly by both API replicas.
- Performance remains within the documented local acceptance threshold.
- Prometheus can scrape both replicas and Grafana is healthy.
- Internal metrics are not exposed through the public gateway.
- The latest GitHub Actions pipeline completes successfully.

## 3. Test environment

| Item | Test value |
|---|---|
| Host OS | Windows with PowerShell |
| Container runtime | Docker Desktop / Docker Compose |
| API runtime | Python 3.12, FastAPI, Uvicorn |
| Frontend runtime | React 19, Vite 8 build, Nginx serving assets |
| Database | PostgreSQL 17 container |
| Cache | Redis 8 container |
| Gateway | Nginx 1.29 container |
| Monitoring | Prometheus 3.5, Grafana 12.1 |
| Public application | `http://localhost` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

Test data used unique generated email addresses and safe `https://example.com`
destinations. Automated tests removed created short links after verification.

## 4. Test summary

| Test area | Executed | Passed | Failed | Skipped/Not executed | Result |
|---|---:|---:|---:|---:|---|
| Backend unit/regression tests | 13 | 13 | 0 | 7 live tests skipped by default | Pass |
| Live functional tests | 7 | 7 | 0 | 0 | Pass |
| Frontend production build | 1 | 1 | 0 | 0 | Pass |
| Python compilation | 1 | 1 | 0 | 0 | Pass |
| Compose validation | 1 | 1 | 0 | 0 | Pass |
| Non-functional scenarios | 6 groups | 6 | 0 | 0 | Pass |
| Service endpoint checks | 5 | 5 | 0 | 0 | Pass |
| Prometheus target checks | 2 | 2 | 0 | 0 | Pass |
| Latest GitHub CI workflow | 1 | 1 | 0 | 0 | Pass |
| npm vulnerability audit | 0 | 0 | 0 | 1 | Not executed—network endpoint unavailable |

No application defect was found during this execution.

## 5. Automated regression results

### 5.1 Command

```powershell
.venv\Scripts\python.exe -m pytest -q
```

### 5.2 Result

```text
sssssss............. [100%]
13 passed, 7 skipped in 2.19s
```

The seven skipped tests are the intentionally gated live-system suite. They are
executed separately with `RUN_LIVE_TESTS=1` in section 7.

### 5.3 Covered behaviors

| Test module | Coverage |
|---|---|
| `test_shortcodes.py` | Requested shortcode length and random-code variance |
| `test_security_and_validation.py` | JWT round trip, invalid JWT, production secret validation, shortcode bounds, malformed token subject |
| `test_redirects.py` | Header truncation and missing-header handling |
| `test_middleware.py` | Rate-limit route selection, forwarded IP use, HTTP 429 response, Redis fail-open behavior |

## 6. Static, build, and configuration checks

### 6.1 Python compilation

```powershell
.venv\Scripts\python.exe -m compileall -q app tests migrations
```

Result: **Pass**. No Python syntax or bytecode-compilation errors.

### 6.2 Frontend production build

```powershell
Set-Location frontend
npm.cmd run build
```

Result: **Pass**.

```text
1795 modules transformed
dist/index.html                  0.56 kB (gzip 0.34 kB)
dist/assets/index-BtHFwxR5.css   9.97 kB (gzip 2.87 kB)
dist/assets/index-BzGKVO1P.js  207.87 kB (gzip 65.85 kB)
Build time: 682 ms
```

### 6.3 Docker Compose validation

```powershell
docker compose config --quiet
```

Result: **Pass**. The Compose model parsed and interpolated successfully.

The local Docker command emitted a sandbox-only warning about reading the host
Docker client configuration. It did not affect Compose validation or the running
stack and is not an application defect.

### 6.4 Dependency vulnerability audit

`npm audit --audit-level=high` could not reach npm's advisory endpoint from the
restricted execution environment. The check is recorded as **not executed**, not
failed. The production build and package installation succeeded, and GitHub may
be used for Dependabot/security advisory monitoring.

## 7. Live functional test results

### 7.1 Command

```powershell
$env:RUN_LIVE_TESTS = "1"
.venv\Scripts\python.exe -m pytest tests\test_live_system.py -q
Remove-Item Env:RUN_LIVE_TESTS
```

### 7.2 Result

```text
....... [100%]
7 passed in 7.18s
```

### 7.3 Functional test cases

| ID | Scenario | Expected result | Actual result |
|---|---|---|---|
| FT-01 | Liveness, readiness, and instance header | HTTP 200; dependencies true; instance is api1/api2 | Pass |
| FT-02 | React frontend at `/` | HTTP 200 with LinkFlux production document/assets | Pass |
| FT-03 | Registration/login lifecycle | Registration 201, duplicate 409, bad login 401, valid login 200 | Pass |
| FT-04 | URL lifecycle and ownership | Validation, create, list, redirect, stats, ownership isolation, delete | Pass |
| FT-05 | Unknown shortcode | HTTP 404 | Pass |
| FT-06 | Oversized tracking headers | Redirect succeeds; click recorded | Pass |
| FT-07 | Concurrent duplicate registration | Exactly one 201 and nine controlled 409 responses | Pass |

### 7.4 Functional requirements verified

- Email normalization is case-insensitive.
- Invalid bearer tokens are rejected.
- Invalid URLs return validation errors.
- Users cannot inspect or delete other users' links.
- Created links appear in the authenticated list.
- Redirects return HTTP 307 with the correct destination.
- Click statistics increment after redirects.
- Deleted links and their statistics become unavailable.
- Long referrer/user-agent values do not break redirects.
- Registration uniqueness remains controlled under concurrency.

## 8. Non-functional test results

### 8.1 Command

```powershell
.venv\Scripts\python.exe tests\nonfunctional_live.py
```

### 8.2 Measured results

| Metric | Target | Measured | Result |
|---|---:|---:|---|
| Concurrent health requests | 200 | 200 | Pass |
| Successful health responses | 200 | 200 | Pass |
| Mean health latency | Informational | 37.52 ms | Pass |
| p50 health latency | Informational | 35.39 ms | Pass |
| p95 health latency | < 1,000 ms | 69.86 ms | Pass |
| p99 health latency | Informational | 95.65 ms | Pass |
| API replicas observed | api1 and api2 | api1 and api2 | Pass |
| Concurrent creates | 30 | 30 | Pass |
| Successful creates | 30 | 30 | Pass |
| Unique shortcodes | 30 | 30 | Pass |
| Concurrent redirects | 50 | 50 | Pass |
| Successful HTTP 307 redirects | 50 | 50 | Pass |
| Recorded clicks | 50 | 50 | Pass |

### 8.3 Interpretation

- The measured p95 latency used only 6.99% of the 1,000 ms acceptance ceiling.
- Both replicas served requests, confirming Nginx distribution.
- No shortcode collision or failed transaction occurred during concurrent writes.
- Redirect and analytics counts remained consistent under concurrent traffic.

These measurements describe this local machine and are not a public service SLA.

## 9. Service and security endpoint checks

| Check | Expected | Actual | Result |
|---|---:|---:|---|
| LinkFlux frontend `/` | 200 | 200 | Pass |
| API readiness `/health/ready` | 200 | 200 | Pass |
| Prometheus health `:9090/-/healthy` | 200 | 200 | Pass |
| Grafana health `:3000/api/health` | 200 | 200 | Pass |
| Public gateway `/metrics/` | 404 | 404 | Pass |

The metrics check confirms that Prometheus data remains available internally to
the monitoring stack but is not exposed through the application gateway.

## 10. Monitoring verification

Prometheus API target inspection returned:

| Target | Health | Last error | Result |
|---|---|---|---|
| `api1:8000` | up | None | Pass |
| `api2:8000` | up | None | Pass |

The provisioned Grafana dashboard had previously been visually verified to show
requests per second, p95 latency, and HTTP errors. Evidence is stored at
[`docs/images/grafana-dashboard.png`](images/grafana-dashboard.png).

## 11. Resilience testing

The Redis degradation scenario was executed during the prior full non-functional
campaign and remains covered by automated middleware tests.

| Scenario | Expected | Observed | Result |
|---|---|---|---|
| Stop Redis while PostgreSQL remains healthy | Readiness status becomes `degraded` | `degraded` | Pass |
| Resolve a short URL with Redis stopped | PostgreSQL fallback returns 307 | 307 | Pass |
| Restart Redis | Cache service becomes healthy | Healthy | Pass |
| Rate limiter cannot reach Redis | Request continues through fail-open policy | Continued | Pass |

PostgreSQL destructive/failover testing was not performed because it would make
the application intentionally unavailable and offers no failover replica in the
current local topology.

## 12. CI/CD verification

GitHub Actions run `31576470994`, triggered by commit `8156a46` (**Add
comprehensive technical specification**), completed with conclusion **success**
on 12 August 2026.

The four preceding workflows for frontend delivery, LinkFlux branding,
screenshots, and architecture documentation also concluded successfully.

The pipeline verifies:

- Python dependency installation and tests.
- Python compilation.
- Deterministic frontend dependency installation and build.
- Docker Compose validation.
- Docker image builds.
- Full Compose startup with health waiting.
- Live black-box tests.
- Diagnostic log capture and test-volume cleanup.

## 13. Manual UI verification

The following screens were manually exercised and captured:

| Screen | Verified behavior | Evidence |
|---|---|---|
| Landing page | LinkFlux branding, navigation, system overview | [frontend-home.png](images/frontend-home.png) |
| My Links | Create field, two links, click totals, copy/delete controls | [frontend-dashboard.png](images/frontend-dashboard.png) |
| System status | API gateway, replicas, PostgreSQL, and Redis operational | [frontend-status.png](images/frontend-status.png) |
| Swagger | Auth, URL, and health API documentation | [swagger-api.png](images/swagger-api.png) |
| Docker services | Running distributed service topology | [docker-services.png](images/docker-services.png) |

## 14. Defect summary

### 14.1 Open defects

No confirmed functional defect is open from this test campaign.

### 14.2 Test-environment issues

| ID | Issue | Impact | Disposition |
|---|---|---|---|
| ENV-01 | npm audit endpoint unavailable from restricted environment | Vulnerability query not executed | Use GitHub dependency alerts or rerun from an unrestricted network |
| ENV-02 | Sandbox account cannot read the user's Docker config or pipe without elevation | Some diagnostic commands require approved execution | Not a repository/runtime defect |

### 14.3 Known product constraints

The following are documented limitations rather than defects:

- Local HTTP without public TLS.
- Client-side JWT logout without server-side revocation.
- Synchronous click-event persistence.
- N+1 statistics requests from the current frontend dashboard.
- Fixed-window rate limiting with fail-open behavior during Redis outages.
- Single-host Compose and single PostgreSQL/Redis instances.

## 15. Requirements traceability

| Requirement group | Primary verification |
|---|---|
| AUTH-01 through AUTH-08 | Regression tests, FT-03, FT-07 |
| LINK-01 through LINK-11 | FT-04, non-functional concurrent creates, manual dashboard |
| REDIR-01 through REDIR-06 | FT-04 through FT-06, concurrent redirects |
| HEALTH-01 through HEALTH-06 | FT-01, endpoint checks, manual status page |
| Security requirements | Token tests, ownership tests, public metrics 404, header tests |
| Availability requirements | Health checks, Redis resilience test, Compose startup |
| Performance requirements | Non-functional measured results |
| Maintainability requirements | Compilation, pinned builds, migrations, successful CI |

## 16. Exit criteria evaluation

| Exit criterion | Status |
|---|---|
| Required containers start and report healthy | Met |
| Backend automated tests pass | Met |
| Frontend production build passes | Met |
| Live authentication and URL lifecycle pass | Met |
| Both API replicas serve traffic | Met |
| Concurrent writes and redirects remain consistent | Met |
| p95 latency remains below local target | Met |
| Monitoring targets are up | Met |
| Public metrics remain blocked | Met |
| Latest GitHub Actions workflow succeeds | Met |
| No critical open application defect | Met |

## 17. Conclusion

LinkFlux satisfies the tested functional and non-functional requirements for its
documented local Docker Compose scope. All executed application tests passed,
both API replicas participated under load, persistence and analytics remained
consistent, and the monitoring stack observed both replicas. The release is
suitable for local portfolio demonstration and continued development.

Public deployment readiness remains conditional on production HTTPS, unique
secrets, external persistence strategy, and the deployment limitations listed in
the technical specification.
