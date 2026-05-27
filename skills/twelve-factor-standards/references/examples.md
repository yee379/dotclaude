# Implementation Examples

Code examples removed from the main SKILL.md to reduce duplication with `/python-patterns`, `/security-review`, and `/k8s-deploy`. Organised by factor.

---

## Factor II — Dependencies

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

## Factor III — Config

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

## Factor V — Build, Release, Run

```
# GOOD pipeline shape
[CI: git push]
    → build: docker build → push ghcr.io/org/api:abc1234   # immutable artifact
    → release: attach values-staging.yaml → ArgoCD syncs   # release = artifact + config
    → run: K8s schedules pods from that release             # never modify running containers
```

---

## Factor VI — Processes

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

## Factor IX — Disposability

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

## Factor XI — Logs

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

## Factor XII — Admin Processes

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
