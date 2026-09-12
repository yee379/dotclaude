---
name: twelve-factor-standards
description: Audit and implement the 12-factor app methodology for cloud-native services — codebase, config, dependencies, backing services, build/release/run, processes, port binding, concurrency, disposability, dev/prod parity, logs, and admin processes. Covers modern extensions (API-first, telemetry, auth) and Kubernetes implementations.
license: MIT
compatibility: opencode
---

# Twelve-Factor App

Auditing and implementing the [12-factor methodology](https://12factor.net) in cloud-native
services — all 12 factors, their Kubernetes implementations, common anti-patterns, and the three
modern extensions.

Use for: reviewing a new or existing service for compliance · designing a service from scratch ·
diagnosing why a service is hard to scale, deploy, or operate · auditing config, secrets, or
logging · planning a monolith-to-cloud-native migration.

**Implementation examples for every factor below live in
`references/twelve-factor-examples.md`**, indexed by factor number. Cross-skill depth:
`/python-patterns` (II, VI, XI, XIV), `/k8s-deploy` (II, V, IX, XI, XII), `/security-review`
(III, XV).

## Audit workflow

1. **Read** the codebase structure, Dockerfile, CI config, and Kubernetes manifests
2. **Score** each factor: ✅ compliant / ⚠️ partial / ❌ violation
3. **Report** grouped by severity — violations, then gaps, then improvements
4. **Recommend** the smallest concrete change that fixes each violation

```
## 12-Factor Audit: <service-name>

| # | Factor             | Status | Finding |
|---|--------------------|--------|---------|
| I | Codebase           | ✅     | Single repo, one deployable unit |
| III | Config           | ❌     | DATABASE_URL hardcoded in app.py:14 |

### Critical violations
[Factor III] Config — fix: move DATABASE_URL to env var, validate with Pydantic Settings at startup

### Recommendations
...
```

## Factor → Kubernetes primitive

| # | Factor | K8s / cloud-native implementation |
|---|--------|-----------------------------------|
| I | Codebase | One repo → one OCI image; GitOps repo as "many deploys" |
| II | Dependencies | `Dockerfile` + lockfile; Trivy/Grype CVE scanning in CI |
| III | Config | `ConfigMap` (non-sensitive) + External Secrets Operator (sensitive) |
| IV | Backing Services | K8s `Service` DNS names; Helm/Operators for DBs |
| V | Build/Release/Run | CI pipeline → immutable OCI image → ArgoCD/Flux GitOps |
| VI | Processes | Stateless `Deployment` pods; `StatefulSet` only for stateful services |
| VII | Port Binding | Container `port` + `Service` + Ingress / Gateway API |
| VIII | Concurrency | `Deployment.replicas` + HPA + KEDA |
| IX | Disposability | Liveness/readiness/startup probes + `preStop` hook + PDB |
| X | Dev/Prod Parity | Same OCI image promoted through envs; Kind/k3d locally |
| XI | Logs | stdout → Fluent Bit DaemonSet → Loki/Elastic; OTel Collector |
| XII | Admin Processes | `Job` / `CronJob` / init containers using the same image |

---

## The 12 factors

### I. Codebase — one codebase, many deploys
One version-controlled repo → one deployable service. Environments are deploys of the same
codebase, never separate repos.

**Violations:** separate repos per environment (`api-prod`, `api-staging`) · multiple apps in one
repo with no independent deploy boundaries · deploying from a developer's laptop.

Monorepos (Nx, Turborepo) are fine — each *service* still needs an independently deployable unit.
Trunk-based development with short-lived branches is preferred.

### II. Dependencies — explicit declaration and isolation
All dependencies in a manifest; no reliance on system-installed tools. Isolation is what prevents
"works on my machine".

**Violations:** no lockfile committed (`package-lock.json`, `uv.lock`, `go.sum`) · relying on
globally installed binaries (`curl`, `imagemagick`, `ffmpeg`) absent from the image · base image
on a mutable tag (`FROM python:3.12` — the tag can change).

### III. Config — store config in the environment
Anything that varies between deploys (URLs, credentials, feature flags) lives in the environment —
not in code, not in committed config files.

**Violations:** hardcoded database URLs or API keys · `.env` committed to git · per-environment
config files in the repo (`config/prod.yaml`).

### IV. Backing services — treat as attached resources
Databases, caches, queues, SMTP, S3 are all attached resources reached via a URL from config.
Swapping local Postgres for RDS is a config change, never a code change.

**Violations:** `if env == "local": use sqlite else: use postgres` · hardcoded `localhost` ·
any logic that behaves differently based on whether a service is "local" or "remote".

### V. Build, release, run — strict stage separation
**Build** source → immutable artifact (OCI image). **Release** artifact + environment config →
versioned, immutable release. **Run** launches the release, with no runtime modification.

**Violations:** `git pull && restart` (collapses all three) · rebuilding per environment, so the
dev image ≠ the prod image · baking secrets into the image at build time.

### VI. Processes — stateless, share-nothing
Processes are stateless; persistent data lives in a backing service. No sticky sessions, no
on-disk state between requests, no in-process shared memory as a cache.

**Violations:** in-memory session store (`app.sessions = {}` — lost on restart) · uploads to local
disk (`/tmp/uploads/` — invisible to other pods) · sticky sessions required.

### VII. Port binding — export services via port binding
The app is self-contained and binds a port; the web server library is a declared dependency, not a
pre-installed external server.

**Violations:** requires a separately installed Apache/Nginx on the host · port hardcoded to 80 or
443 (needs root, not configurable) · only works inside one orchestrator's injection mechanism.

In K8s: the container declares `containerPort`, a `Service` routes to it, TLS terminates at
ingress.

### VIII. Concurrency — scale out via the process model
Scale horizontally by running more processes, not by making one bigger. Workload types (web,
worker, scheduler) are separate process types that scale independently.

**Violations:** background threads inside the web process handling async jobs · cron tied to one
server that must always be up · only vertical scaling considered.

### IX. Disposability — fast startup, graceful shutdown
Processes start in seconds and shut down gracefully on `SIGTERM`, finishing in-flight requests.
Workers return unfinished jobs to the queue.

**Violations:** startup takes minutes (loading huge files, running migrations, warming caches
synchronously) · no `SIGTERM` handler, so Kubernetes kills the pod and drops in-flight requests ·
non-idempotent job processing duplicating side effects on restart.

### X. Dev/prod parity — keep environments similar
Minimise three gaps: **time** (deploy frequently), **people** (developers own what they ship),
**tools** (same backing service versions — Postgres in both, not SQLite in dev).

**Violations:** SQLite in dev, Postgres in prod — hides behaviour differences until production ·
months between deploys · developers with no visibility into production behaviour.

### XI. Logs — treat as event streams
The app writes everything to `stdout`/`stderr` — never to files, never managing rotation. The
execution environment captures and routes the stream. In 2026 that means structured logs plus
metrics plus distributed traces.

**Violations:** writing to `/var/log/app.log` inside the container · running `logrotate` in the
app · unstructured plaintext with no correlation ID.

Instrument OpenTelemetry at the framework level (FastAPI middleware, SQLAlchemy events) so traces
propagate across services automatically.

### XII. Admin processes — one-off tasks as first-class processes
Admin tasks (migrations, cache warm-ups, backups, one-off scripts) run in the same environment as
the app — same codebase, config, and image. Not from a laptop against production, and not baked
into app startup.

**Violations:** migrations inside `app.startup` (a race across replicas) · admin scripts on
different dependency versions · hotfixing prod data over SSH from a laptop.

---

## Modern extensions

From Kevin Hoffman's *Beyond the Twelve-Factor App* (O'Reilly, 2016), widely adopted by 2026.
Apply in addition to the original twelve.

### XIII. API first
Design the contract *before* the implementation. The OpenAPI spec, Protobuf definition, or
AsyncAPI schema is the source of truth — which is what enables parallel team development and clear
service boundaries.

Commit `openapi.yaml` / `.proto` before any implementation · generate server stubs and client SDKs
from the contract · consumer-driven contract testing (Pact) so changes don't silently break
consumers · GraphQL introspection disabled in production.

### XIV. Telemetry
Structured observability data is a first-class concern. "Logs to stdout" (Factor XI) is necessary
but insufficient.

| Pillar | Tool | What it answers |
|--------|------|----------------|
| Logs | structlog → Loki / Elastic | "What happened and when?" |
| Metrics | Prometheus client → Grafana | "How is the system performing?" |
| Traces | OpenTelemetry → Tempo / Jaeger | "Why is this request slow?" |

Minimum: `/healthz` (liveness — no dependency checks), `/readyz` (readiness — checks backing
services), `/metrics` (Prometheus). FastAPI lifespan pattern: `/python-patterns`.

### XV. Auth & authz
Every service treats authentication and authorisation as a built-in design concern. In a
microservices world every inter-service call has identity. Zero trust: never trust, always verify.

Workload identity via SPIFFE/SPIRE or service mesh mTLS, not network-level trust · JWT/OIDC for
user identity, verified on **every** request rather than only at the gateway · OPA or Casbin for
fine-grained policy decisions.

---

## Pre-ship compliance checklist

- [ ] **I** Single repo, one deployable unit; no env-specific repos
- [ ] **II** Lockfile committed; base image pinned to digest; CVE scan in CI
- [ ] **III** No hardcoded secrets; config validated at startup; ESO or vault for sensitive values
- [ ] **IV** No env-conditional backing service logic; all services reached by URL from config
- [ ] **V** Image built once in CI and promoted unchanged; no runtime `pip install`
- [ ] **VI** Stateless processes; sessions in Redis; uploads in object storage
- [ ] **VII** Port configurable via env var; web server is a dependency
- [ ] **VIII** Web and worker processes separate; HPA/KEDA configured
- [ ] **IX** SIGTERM handler; `preStop` sleep; `terminationGracePeriodSeconds` tuned; PDB set
- [ ] **X** Same DB engine and version in dev and prod; same image across environments
- [ ] **XI** Structured JSON to stdout; no PII; OTel tracing; Prometheus metrics
- [ ] **XII** Migrations as K8s Jobs, not at startup; admin tasks use the same image and config
- [ ] **XIII** API contract written before implementation
- [ ] **XIV** `/healthz`, `/readyz`, `/metrics` present
- [ ] **XV** Auth verified per-request in the service layer, not only at the gateway
