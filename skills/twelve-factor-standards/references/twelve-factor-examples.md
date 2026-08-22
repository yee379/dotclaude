# 12-Factor Code Examples

Implementation examples for the factors in `SKILL.md`, in factor order. Load only the factor
you are auditing. For deeper language- or platform-specific patterns see `/python-patterns`,
`/k8s-deploy`, and `/security-review`.

---

## Factor II — Dependencies (explicit declaration and isolation)

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

---

## Factor III — Config (store config in the environment)

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

---

## Factor IV — Backing Services (always same code path)

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

## Factor V — Build, Release, Run (strict stage separation)

```
# GOOD pipeline shape
[CI: git push]
    → build: docker build → push ghcr.io/org/api:abc1234   # immutable artifact
    → release: attach values-staging.yaml → ArgoCD syncs   # release = artifact + config
    → run: K8s schedules pods from that release             # never modify running containers
```

---

## Factor VI — Processes (stateless, share-nothing)

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

---

## Factor VII — Port Binding (self-contained service)

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

## Factor VIII — Concurrency (separate process types)

```yaml
# GOOD — separate Deployments per process type, each scales independently
# web: scales on HTTP load (HPA on CPU/RPS)
# worker: scales on queue depth (HPA or KEDA)
```

---

## Factor IX — Disposability (fast startup, graceful shutdown)

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

---

## Factor X — Dev/Prod Parity (same images everywhere)

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

## Factor XI — Logs (treat as event streams)

```python
# GOOD — structured JSON logging with correlation ID
import structlog
logger = structlog.get_logger()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
        logger.info("request", method=request.method, path=request.url.path, status=response.status_code)
    return response
```

---

## Factor XII — Admin Processes (one-off tasks as first-class processes)

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

---

## Factor XIV — Telemetry (health + metrics endpoints)

Minimum implementation. See `/python-patterns` for the full FastAPI lifespan setup.

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
