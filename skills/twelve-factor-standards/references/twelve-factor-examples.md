# 12-Factor Code Examples

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

## Factor VIII — Concurrency (separate process types)

```yaml
# GOOD — separate Deployments per process type, each scales independently
# web: scales on HTTP load (HPA on CPU/RPS)
# worker: scales on queue depth (HPA or KEDA)
```

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
