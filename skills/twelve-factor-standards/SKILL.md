---
name: twelve-factor-standards
description: Audit and implement the 12-factor app methodology for cloud-native services — codebase, config, dependencies, backing services, build/release/run, processes, port binding, concurrency, disposability, dev/prod parity, logs, and admin processes. Covers modern extensions (API-first, telemetry, auth) and Kubernetes implementations.
license: MIT
compatibility: opencode
---

# Twelve-Factor App

Practical guidance for auditing and implementing the [12-factor app methodology](https://12factor.net) in modern cloud-native services. Covers all 12 original factors, their Kubernetes implementations, common anti-patterns, and the three modern extensions (API-first, telemetry, auth/authz).

## When to Use

- Reviewing a new or existing service for 12-factor compliance
- Designing a new service from scratch
- Diagnosing why a service is hard to scale, deploy, or operate
- Auditing config, secrets, or logging practices
- Planning a migration from a legacy monolith to cloud-native

---

## Audit Workflow

When asked to audit a service for 12-factor compliance:

1. **Read** the codebase structure, Dockerfile, CI config, and any Kubernetes manifests
2. **Score** each factor: ✅ compliant / ⚠️ partial / ❌ violation
3. **Report** findings grouped by severity — violations first, then gaps, then improvements
4. **Recommend** the smallest concrete change that fixes each violation

Output format:

```
## 12-Factor Audit: <service-name>

| # | Factor             | Status | Finding |
|---|--------------------|--------|---------|
| I | Codebase           | ✅     | Single repo, one deployable unit |
| III | Config           | ❌     | DATABASE_URL hardcoded in app.py:14 |
...

### Critical violations
[Factor III] Config — fix: move DATABASE_URL to env var, validate with Pydantic Settings at startup

### Recommendations
...
```

---

## Quick Reference: Factor → Kubernetes Primitive

| # | Factor | K8s / Cloud-Native Implementation |
|---|--------|-----------------------------------|
| I | Codebase | One repo → one OCI image; GitOps repo as "many deploys" |
| II | Dependencies | `Dockerfile` + lockfile; Trivy/Grype CVE scanning in CI |
| III | Config | `ConfigMap` (non-sensitive) + External Secrets Operator (sensitive) |
| IV | Backing Services | K8s `Service` DNS names; Helm/Operators for DBs |
| V | Build/Release/Run | CI pipeline → immutable OCI image → ArgoCD/Flux GitOps |
| VI | Processes | Stateless `Deployment` pods; `StatefulSet` only for stateful services |
| VII | Port Binding | Container `port` + K8s `Service` + Ingress / Gateway API |
| VIII | Concurrency | `Deployment.replicas` + HPA + KEDA |
| IX | Disposability | Liveness/Readiness/Startup probes + `preStop` hook + PDB |
| X | Dev/Prod Parity | Same OCI image promoted through envs; Kind/k3d for local dev |
| XI | Logs | stdout → Fluent Bit DaemonSet → Loki/Elastic; OTel Collector |
| XII | Admin Processes | `Job` / `CronJob` / init containers using the same image |

---

## The 12 Factors

### I. Codebase — One codebase, many deploys

**Rule:** One version-controlled repo → one deployable service. Many environments (dev/staging/prod) are deploys of the same codebase, never separate repos.

**Violations:**
- Separate repos per environment (`api-prod`, `api-staging`)
- Multiple apps sharing one repo without independent deploy boundaries
- Deploying directly from a developer's laptop

**2026 practice:** Monorepos (Nx, Turborepo) are fine — each *service* must still have an independently deployable unit. Trunk-based development with short-lived branches is preferred.

---

### II. Dependencies — Explicit declaration and isolation

**Rule:** All dependencies declared in a manifest; no reliance on system-installed tools. Isolation prevents "works on my machine."

**Violations:**
- No lockfile committed (`package-lock.json`, `uv.lock`, `go.sum`)
- Relying on globally installed binaries (`curl`, `imagemagick`, `ffmpeg`) not in the image
- Base image pinned to a mutable tag (`FROM python:3.12` — tag can change)

> For implementation examples, see `/python-patterns` or `/k8s-deploy`.

---

### III. Config — Store config in the environment

**Rule:** Anything that varies between deploys (URLs, credentials, feature flags) lives in the environment — not in code, not in config files committed to the repo.

**Violations:**
- Hardcoded database URLs or API keys in source code
- `.env` files committed to git
- Per-environment config files in the repo (`config/prod.yaml`)
- Secrets stored as plain env vars in CI/CD YAML

> For implementation examples, see `/python-patterns` or `/security-review`.

---

### IV. Backing Services — Treat as attached resources

**Rule:** Databases, caches, queues, SMTP, S3 — all are "attached resources" accessed via a URL or config. Swapping local Postgres for AWS RDS requires only a config change, never a code change.

**Violations:**
- `if env == "local": use sqlite else: use postgres` branches in code
- Hardcoded `localhost` for a backing service
- Logic that behaves differently based on whether a service is "local" or "remote"

```python
# BAD — code knows about environment topology
if os.getenv("ENV") == "local":
    db = sqlite3.connect("dev.db")
else:
    db = psycopg2.connect(os.getenv("DATABASE_URL"))

# GOOD — always the same code path, config drives the target
db = psycopg2.connect(settings.database_url)
# In dev: DATABASE_URL=postgresql://localhost/myapp
# In prod: DATABASE_URL=postgresql://rds.amazonaws.com/myapp
```


---

### V. Build, Release, Run — Strict stage separation

**Rule:** Three strictly separated stages:
- **Build**: source → immutable artifact (OCI image)
- **Release**: artifact + environment config → versioned, immutable release
- **Run**: launch the release — no modification allowed at runtime

**Violations:**
- `git pull && restart` deployments (collapses all three stages)
- Rebuilding the image per environment (dev image ≠ prod image)
- Baking secrets into the image at build time
- Running `npm install` or `pip install` at container startup

> For implementation examples, see `/k8s-deploy`.

---

### VI. Processes — Stateless, share-nothing

**Rule:** Processes are stateless. Persistent data lives in a backing service. No sticky sessions, no on-disk state between requests, no in-process shared memory as a cache.

**Violations:**
- In-memory session store (`app.sessions = {}` — lost on restart)
- Uploading files to local disk (`/tmp/uploads/` — not visible to other pods)
- Sticky sessions required (load balancer must always route user to same pod)
- "Snowflake" servers that have been manually configured and can't be replaced

> For implementation examples, see `/python-patterns`.

---

### VII. Port Binding — Export services via port binding

**Rule:** The app is self-contained and exports HTTP (or other protocols) by binding to a port. It does not rely on a pre-installed external web server. The web server library is a declared dependency.

**Violations:**
- App requires a separately installed Apache/Nginx on the host to function
- Port hardcoded to `80` or `443` (requires root; not configurable)
- App only works inside a specific orchestrator's injection mechanism

```python
# GOOD — self-contained, port from config
import uvicorn
from fastapi import FastAPI

app = FastAPI()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
```

K8s: container declares `containerPort`; `Service` routes to it. TLS terminated at ingress (cert-manager), not in the app process.

---

### VIII. Concurrency — Scale out via the process model

**Rule:** Scale horizontally by running more processes, not by making one process bigger. Different workload types run as separate process types (web, worker, scheduler) that scale independently.

**Violations:**
- Background threads spawned inside the web process to handle async jobs
- Cron jobs tied to a specific server that must always be running
- Only vertical scaling (bigger VM) considered

```yaml
# GOOD — separate Deployments per process type, each scales independently
# web: scales on HTTP load (HPA on CPU/RPS)
# worker: scales on queue depth (HPA or KEDA)
```

---

### IX. Disposability — Fast startup, graceful shutdown

**Rule:** Processes start quickly (seconds) and shut down gracefully on `SIGTERM` — finishing in-flight requests before exiting. Workers return unfinished jobs to the queue on shutdown.

**Violations:**
- Startup takes minutes (loads huge files, runs migrations, warms caches synchronously)
- No `SIGTERM` handler — Kubernetes kills the pod and in-flight requests are dropped
- Non-idempotent job processing causes duplicate side-effects on restart

> For implementation examples, see `/k8s-deploy`.

---

### X. Dev/Prod Parity — Keep environments as similar as possible

**Rule:** Minimise three gaps: (1) **time** — deploy frequently; (2) **people** — developers own what they ship; (3) **tools** — same backing service versions in dev and prod (Postgres in both, not SQLite in dev).

**Violations:**
- SQLite in dev, Postgres in prod — hides behaviour differences until production
- Months between deploys (large time gap = large risk)
- Developers have no visibility into production behaviour
- Different OS, library versions, or backing service versions across environments

```yaml
# docker-compose.yml — dev uses same images as prod
services:
  api:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:dev@db:5432/myapp
      REDIS_URL: redis://redis:6379

  db:
    image: postgres:16-alpine    # same major version as production RDS
    environment:
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: myapp

  redis:
    image: redis:7-alpine        # same version as production ElastiCache
```


---

### XI. Logs — Treat as event streams

**Rule:** The app writes all output to `stdout`/`stderr` — never to files, never manages rotation. The execution environment captures and routes the stream. In 2026, this means full observability: structured logs + metrics + distributed traces.

**Violations:**
- Writing to `/var/log/app.log` inside the container
- Managing log rotation (`logrotate`) inside the app
- Unstructured plaintext logs with no correlation ID
- Metrics not exposed; no tracing instrumentation

Use OpenTelemetry for distributed tracing — instrument at the framework level (FastAPI middleware, SQLAlchemy events) so traces propagate automatically across services.

> For implementation examples, see `/python-patterns` or `/k8s-deploy`.

---

### XII. Admin Processes — One-off tasks as first-class processes

**Rule:** Admin tasks (DB migrations, cache warm-ups, data backups, one-off scripts) run in the same environment as the app — same codebase, same config, same image. They are not run from a developer's laptop directly against production, and not baked into app startup.

**Violations:**
- DB migrations run inside `app.startup` (race condition across multiple replicas)
- Admin scripts use different dependency versions than the app
- Hotfixing prod data via SSH from a developer's laptop
- Cron jobs not using the same container image as the app

> For implementation examples, see `/k8s-deploy`.

---

## Modern Extensions (Beyond 12-Factor)

Kevin Hoffman's *Beyond the Twelve-Factor App* (O'Reilly, 2016) adds three factors widely adopted by 2026. Apply these in addition to the original twelve.

### XIII. API First

**Rule:** Design the API contract *before* writing implementation code. The OpenAPI spec, Protobuf definition, or AsyncAPI schema is the source of truth — enables parallel team development and clear service boundaries.

**Practice:**
- Commit `openapi.yaml` / `.proto` to the repo before any implementation
- Generate server stubs and client SDKs from the contract
- Consumer-driven contract testing (Pact) so service changes don't silently break consumers
- GraphQL: introspection disabled in production

---

### XIV. Telemetry

**Rule:** Apps emit structured observability data as a first-class concern — not an afterthought. "Logs to stdout" (Factor XI) is necessary but insufficient. Full observability = logs + metrics + traces.

**The three pillars:**

| Pillar | Tool | What it answers |
|--------|------|----------------|
| Logs | structlog → Loki / Elastic | "What happened and when?" |
| Metrics | Prometheus client → Grafana | "How is the system performing?" |
| Traces | OpenTelemetry → Tempo / Jaeger | "Why is this request slow?" |

**Minimum implementation:**
```python
# Health endpoints — required by Kubernetes probes and monitoring
@app.get("/healthz")    # liveness: "am I alive?"
async def healthz():
    return {"status": "ok"}

@app.get("/readyz")     # readiness: "am I ready for traffic?"
async def readyz():
    await db.ping()     # verify backing services
    return {"status": "ok"}

# Prometheus metrics endpoint
from prometheus_client import make_asgi_app, Counter, Histogram

REQUEST_COUNT = Counter("http_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])
```

---

### XV. Auth & Authz

**Rule:** Every service handles authentication and authorisation as a built-in design concern. In a microservices world, every inter-service call has identity. Zero-trust: never trust, always verify.

**Practice:**
- Workload identity via SPIFFE/SPIRE or service mesh mTLS (not network-level trust)
- JWT/OIDC for user identity; verified on every request, not just at the gateway
- OPA (Open Policy Agent) or Casbin for fine-grained policy decisions
- See `security-review` skill for full auth/authz implementation patterns

---

## Compliance Checklist

Use this for a rapid pre-ship audit. Each item maps to a factor above.

### Codebase & Dependencies
- [ ] I: Single repo, one deployable unit; no env-specific repos
- [ ] II: Lockfile committed; base image pinned to digest; CVE scan in CI

### Config & Secrets
- [ ] III: No hardcoded secrets; config validated at startup; ESO or vault for sensitive values

### Architecture
- [ ] IV: No env-conditional backing service logic; all services accessed by URL from config
- [ ] V: Image built once in CI, promoted unchanged; no runtime `pip install`
- [ ] VI: Stateless processes; sessions in Redis; uploads in object storage
- [ ] VII: Port configurable via env var; web server is a dependency
- [ ] VIII: Web and worker processes separate; HPA/KEDA configured

### Operations
- [ ] IX: SIGTERM handler; `preStop` sleep; `terminationGracePeriodSeconds` tuned; PDB set
- [ ] X: Same DB engine/version in dev and prod; same image across environments
- [ ] XI: Structured JSON to stdout; no PII in logs; OTel tracing; Prometheus metrics
- [ ] XII: Migrations as K8s Jobs (not at startup); admin tasks use same image + config

### Modern Extensions
- [ ] XIII: API contract (OpenAPI/Protobuf) written before implementation
- [ ] XIV: `/healthz`, `/readyz`, `/metrics` endpoints present
- [ ] XV: Auth verified per-request in service layer, not only at gateway

---

## Common Anti-Patterns at a Glance

| Anti-pattern | Factor violated | Fix |
|---|---|---|
| `DATABASE_URL` hardcoded in source | III | Move to env var; validate with Pydantic Settings |
| `.env` committed to git | III | Add to `.gitignore`; use ESO / Vault |
| `if env == "local": sqlite` | IV | Same DB engine everywhere; Docker Compose for dev |
| `npm install` in container `CMD` | V | Run at build time in `Dockerfile` |
| In-memory session (`app.sessions = {}`) | VI | Use Redis |
| File uploads to `/tmp` on pod | VI | Use S3 / GCS |
| Migrations inside `app.startup()` | XII | Run as K8s Job before deployment |
| Plaintext logs to `/var/log/app.log` | XI | stdout + structured JSON |
| No SIGTERM handler | IX | Add graceful shutdown; tune `terminationGracePeriodSeconds` |
| SQLite in dev / Postgres in prod | X | Postgres everywhere; Docker Compose for local |

