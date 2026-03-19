---
name: twelve-factor
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

```dockerfile
# BAD — mutable tag, no lockfile guarantee
FROM python:3.12
RUN pip install -r requirements.txt

# GOOD — pinned digest, lockfile, non-root
FROM python:3.12-slim@sha256:a1b2c3...
COPY uv.lock pyproject.toml ./
RUN pip install uv && uv sync --frozen
USER 1001
```

**Checklist:**
- [ ] Lockfile committed and used in CI (`--frozen` / `--ci` flag)
- [ ] Base image pinned to digest, not just tag
- [ ] Vulnerability scan in CI (`trivy image`, `grype`) blocks on CRITICAL/HIGH
- [ ] Automated dependency updates (Dependabot / Renovate)

---

### III. Config — Store config in the environment

**Rule:** Anything that varies between deploys (URLs, credentials, feature flags) lives in the environment — not in code, not in config files committed to the repo.

**Violations:**
- Hardcoded database URLs or API keys in source code
- `.env` files committed to git
- Per-environment config files in the repo (`config/prod.yaml`)
- Secrets stored as plain env vars in CI/CD YAML

```python
# BAD — hardcoded config
DATABASE_URL = "postgresql://user:s3cr3t@db:5432/app"
DEBUG = True

# GOOD — validated at startup, fails fast if missing
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str          # raises at startup if absent
    redis_url: str
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"      # local dev only — never committed

settings = Settings()
```

```yaml
# BAD — secret value in K8s manifest
env:
  - name: DB_PASSWORD
    value: "s3cr3t"

# GOOD — External Secrets Operator syncs from Vault/AWS SM
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: api-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: prod/api/database-url
```

**Checklist:**
- [ ] No secrets or URLs hardcoded in source
- [ ] `.env` in `.gitignore`; never committed
- [ ] Config validated at startup (Pydantic Settings, Viper, Zod)
- [ ] Sensitive values in secrets manager (Vault, AWS SM, Doppler), not plain env vars
- [ ] K8s: `ConfigMap` for non-sensitive, External Secrets Operator for sensitive

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

**Checklist:**
- [ ] No environment-conditional backing service logic in code
- [ ] All service URLs/credentials sourced from config (Factor III)
- [ ] Health check verifies backing service connectivity at startup
- [ ] Circuit breaker / retry logic for transient failures (Resilience4j, tenacity)

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

```
# GOOD pipeline shape
[CI: git push]
    → build: docker build → push ghcr.io/org/api:abc1234   # immutable artifact
    → release: attach values-staging.yaml → ArgoCD syncs   # release = artifact + config
    → run: K8s schedules pods from that release             # never modify running containers
```

**Checklist:**
- [ ] One image built once in CI; same image promoted dev → staging → prod
- [ ] Image tagged with immutable ref (git SHA or semver), never `:latest` in prod
- [ ] No secrets baked into image layers (`docker history` clean)
- [ ] No dependency installation at container startup

---

### VI. Processes — Stateless, share-nothing

**Rule:** Processes are stateless. Persistent data lives in a backing service. No sticky sessions, no on-disk state between requests, no in-process shared memory as a cache.

**Violations:**
- In-memory session store (`app.sessions = {}` — lost on restart)
- Uploading files to local disk (`/tmp/uploads/` — not visible to other pods)
- Sticky sessions required (load balancer must always route user to same pod)
- "Snowflake" servers that have been manually configured and can't be replaced

```python
# BAD — in-process session state
app.sessions = {}

@app.post("/login")
def login(user_id: str):
    app.sessions[user_id] = {"logged_in_at": time.time()}  # lost on pod restart

# GOOD — session stored in Redis backing service
import redis
r = redis.from_url(settings.redis_url)

@app.post("/login")
def login(user_id: str):
    r.setex(f"session:{user_id}", 3600, json.dumps({"logged_in_at": time.time()}))
```

**Checklist:**
- [ ] No in-process session or user state (use Redis/Memcached)
- [ ] File uploads go to object storage (S3, GCS), not local disk
- [ ] App can be killed and restarted without data loss or user impact
- [ ] No sticky sessions required — any pod can serve any request
- [ ] K8s: `Deployment` (stateless), `StatefulSet` only for genuinely stateful services

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

```yaml
# K8s: container declares its port; Service routes to it
containers:
  - name: api
    image: ghcr.io/org/api:1.2.3
    ports:
      - containerPort: 8080
    env:
      - name: PORT
        value: "8080"
---
apiVersion: v1
kind: Service
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 8080
```

**Checklist:**
- [ ] Port configurable via `PORT` env var (not hardcoded)
- [ ] Web server is a declared dependency, not a host assumption
- [ ] TLS terminated at ingress layer (cert-manager), not in the app process

---

### VIII. Concurrency — Scale out via the process model

**Rule:** Scale horizontally by running more processes, not by making one process bigger. Different workload types run as separate process types (web, worker, scheduler) that scale independently.

**Violations:**
- Background threads spawned inside the web process to handle async jobs
- Cron jobs tied to a specific server that must always be running
- Only vertical scaling (bigger VM) considered

```yaml
# GOOD — separate Deployments per process type, each scales independently
# web process
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-web
spec:
  replicas: 3        # scales on HTTP load

# worker process
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-worker
spec:
  replicas: 5        # scales on queue depth
```

```yaml
# KEDA — scale workers based on queue depth, not just CPU
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: api-worker-scaler
spec:
  scaleTargetRef:
    name: api-worker
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
    - type: rabbitmq
      metadata:
        queueName: jobs
        value: "10"   # scale up when >10 messages per replica
```

**Checklist:**
- [ ] Web and worker process types are separate Deployments
- [ ] Each process type scales on its own relevant metric (HTTP RPS vs queue depth)
- [ ] HPA configured; consider KEDA for event-driven workloads
- [ ] Worker processes are idempotent (safe to process the same message twice)

---

### IX. Disposability — Fast startup, graceful shutdown

**Rule:** Processes start quickly (seconds) and shut down gracefully on `SIGTERM` — finishing in-flight requests before exiting. Workers return unfinished jobs to the queue on shutdown.

**Violations:**
- Startup takes minutes (loads huge files, runs migrations, warms caches synchronously)
- No `SIGTERM` handler — Kubernetes kills the pod and in-flight requests are dropped
- Non-idempotent job processing causes duplicate side-effects on restart

```python
# GOOD — graceful shutdown handler
import signal, sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await db.connect()
    yield
    # shutdown — called on SIGTERM
    await db.disconnect()

app = FastAPI(lifespan=lifespan)
```

```yaml
# K8s — tuned for zero-drop shutdown
spec:
  terminationGracePeriodSeconds: 60    # must be > longest expected request
  containers:
    - name: api
      lifecycle:
        preStop:
          exec:
            command: ["sleep", "5"]    # wait for load balancer to stop routing
      readinessProbe:
        httpGet:
          path: /readyz
          port: 8080
        periodSeconds: 5
        failureThreshold: 2
      livenessProbe:
        httpGet:
          path: /healthz
          port: 8080
        periodSeconds: 30
        failureThreshold: 3
      startupProbe:
        httpGet:
          path: /healthz
          port: 8080
        periodSeconds: 5
        failureThreshold: 30           # 150s max startup budget
```

**Checklist:**
- [ ] `SIGTERM` handler drains in-flight requests before exiting
- [ ] `preStop` sleep (5–15s) gives load balancer time to stop routing
- [ ] `terminationGracePeriodSeconds` ≥ longest expected request duration
- [ ] Readiness probe removes pod from rotation before it shuts down
- [ ] Worker: unacked messages returned to queue on shutdown
- [ ] `PodDisruptionBudget` keeps minimum replicas alive during node drains

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

**Checklist:**
- [ ] Same database engine and major version in dev and prod
- [ ] Docker Compose (or Testcontainers) for local backing services
- [ ] Same OCI image promoted through environments — never rebuild per environment
- [ ] Ephemeral preview environments for every PR (ArgoCD, Vercel, Railway)
- [ ] Feature flags (LaunchDarkly, Unleash) to decouple deploy from release

---

### XI. Logs — Treat as event streams

**Rule:** The app writes all output to `stdout`/`stderr` — never to files, never manages rotation. The execution environment captures and routes the stream. In 2026, this means full observability: structured logs + metrics + distributed traces.

**Violations:**
- Writing to `/var/log/app.log` inside the container
- Managing log rotation (`logrotate`) inside the app
- Unstructured plaintext logs with no correlation ID
- Metrics not exposed; no tracing instrumentation

```python
# GOOD — structured JSON logging with correlation ID
import structlog

logger = structlog.get_logger()

# Middleware injects trace context into every log line
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
    return response
```

```python
# GOOD — OpenTelemetry instrumentation (logs + traces + metrics unified)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer = trace.get_tracer(__name__)

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    with tracer.start_as_current_span("get_order") as span:
        span.set_attribute("order.id", order_id)
        order = await db.get_order(order_id)
        return order
```

**Checklist:**
- [ ] All output to `stdout`/`stderr` — no file logging in the container
- [ ] Structured JSON logs (structlog, Pino, zerolog, logback)
- [ ] Correlation / trace ID on every log line
- [ ] No PII or secrets in log output
- [ ] `GET /metrics` Prometheus endpoint exposed
- [ ] OpenTelemetry instrumentation for distributed tracing
- [ ] Log aggregation: Fluent Bit DaemonSet → Loki or Elastic

---

### XII. Admin Processes — One-off tasks as first-class processes

**Rule:** Admin tasks (DB migrations, cache warm-ups, data backups, one-off scripts) run in the same environment as the app — same codebase, same config, same image. They are not run from a developer's laptop directly against production, and not baked into app startup.

**Violations:**
- DB migrations run inside `app.startup` (race condition across multiple replicas)
- Admin scripts use different dependency versions than the app
- Hotfixing prod data via SSH from a developer's laptop
- Cron jobs not using the same container image as the app

```yaml
# GOOD — migration as a K8s Job (runs before the new Deployment rolls out)
apiVersion: batch/v1
kind: Job
metadata:
  name: api-migrate-v1-4-0
spec:
  ttlSecondsAfterFinished: 300
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: ghcr.io/org/api:1.4.0    # same image as the app
          command: ["python", "-m", "alembic", "upgrade", "head"]
          envFrom:
            - secretRef:
                name: api-secrets         # same config as the app
```

```yaml
# GOOD — scheduled task as CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: api-cleanup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: cleanup
              image: ghcr.io/org/api:1.4.0
              command: ["python", "-m", "tasks.cleanup_expired_sessions"]
              envFrom:
                - secretRef:
                    name: api-secrets
```

**Checklist:**
- [ ] Migrations run as a K8s Job or init container, not at app startup
- [ ] Migrations are idempotent and backward-compatible with the previous app version
- [ ] Admin tasks use the same container image and config as the app
- [ ] No direct prod access from developer laptops; use `kubectl exec` with RBAC
- [ ] Jobs have `ttlSecondsAfterFinished` to auto-clean completed objects

---

## Modern Extensions (Beyond 12-Factor)

Kevin Hoffman's *Beyond the Twelve-Factor App* (O'Reilly, 2016) adds three factors widely adopted by 2026. Apply these in addition to the original twelve.

### XIII. API First

**Rule:** Design the API contract *before* writing implementation code. The OpenAPI spec, Protobuf definition, or AsyncAPI schema is the source of truth. This enables parallel team development and clear service boundaries.

**Practice:**
- Write the OpenAPI spec first; generate server stubs and client SDKs from it
- Use consumer-driven contract testing (Pact) so service changes don't silently break consumers
- Introspection disabled in production GraphQL (security + performance)

```yaml
# openapi.yaml committed to repo before any implementation
openapi: "3.1.0"
info:
  title: Orders API
  version: "1.0.0"
paths:
  /orders/{id}:
    get:
      operationId: getOrder
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Order found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Order"
```

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

