## ADR Format — Codebase

```markdown
## ADR-001: Photo storage backend

**Status:** Accepted
**Date:** 2026-03-18

### Context
We need durable, CDN-friendly object storage for user photos.
Current infra uses AWS. Team has no GCP experience.

### Options considered

| Option | Pros | Cons |
|---|---|---|
| S3 + CloudFront | Team knows it, CDN built-in, 99.999% SLA | Cost at scale |
| Cloudflare R2 | Cheaper egress, built-in CDN | Less mature, no team experience |
| Self-hosted MinIO | Full control, no egress cost | Operational burden, no CDN |

### Decision
S3 + CloudFront — team familiarity reduces risk, CDN integration is proven,
cost is acceptable at current scale (< 10M photos).

### Consequences
- Must implement S3 lifecycle rules to delete old photos
- CloudFront distribution needs cache invalidation on photo update
- Cost review if photo volume > 50M
```

---

## ADR Format — Platform

```markdown
## ADR-001: Namespace isolation strategy for auth service

**Status:** Accepted
**Date:** YYYY-MM-DD

### Context
Auth service handles JWTs. Needs strong isolation from other tenants.

### Options considered

| Option | Pros | Cons |
|---|---|---|
| Dedicated namespace | Strong isolation, easy RBAC scoping | More namespaces to manage |
| Shared app namespace | Fewer namespaces | Lateral movement risk |

### Decision
Dedicated namespace — isolation benefit outweighs management overhead.

### Consequences
- Need namespace-scoped RBAC for each service team
- NetworkPolicy required to restrict cross-namespace traffic
```

---

## Module Design Format (Codebase)

```
Module: PhotoResizer
  Responsibility: Accept raw image bytes, return resized image bytes at a target dimension
  Interface: resize(data: bytes, width: int, height: int) → bytes
  Status: New
  Testable in isolation: Yes — no I/O, pure transformation

Module: UserProfileRepository
  Responsibility: Read/write user records including photo_url
  Interface: get_user(id), update_photo_url(id, url)
  Status: Modify (add photo_url field)
  Testable in isolation: Yes — mock the DB connection

Module: PhotoUploadHandler (HTTP layer)
  Responsibility: Validate, orchestrate resize + store + update, return URL
  Interface: POST /users/:id/photo
  Status: New
  Testable in isolation: Partial — integration test covers the full flow
```

---

## System Design Diagram + API Contract (Codebase)

```
Client
  │  POST /users/:id/photo (multipart)
  ▼
API Gateway / Ingress
  │  auth check → rate limit
  ▼
Upload Service (k8s Deployment)
  │  validate (size, type)
  │  resize to 256×256
  │  upload to S3
  │  enqueue deletion of old photo
  │  update user record (photo_url)
  ▼
S3 Bucket ──► CloudFront CDN ──► Client (photo fetch)

Background Worker (k8s Job)
  │  consume deletion queue
  ▼
S3 (delete old photo)
```

Data model:
```sql
ALTER TABLE users ADD COLUMN photo_url TEXT;
ALTER TABLE users ADD COLUMN photo_updated_at TIMESTAMPTZ;
-- backward-compatible: nullable, no default needed
```

API contract:
```
POST /users/:id/photo
  Content-Type: multipart/form-data
  Body: file (required)
  Auth: Bearer token (own profile or admin)

Response 200:
  { "photo_url": "https://cdn.example.com/photos/abc123.jpg" }

Response 400:
  { "error": { "code": "INVALID_FILE", "message": "..." } }
```

---

## Infrastructure Design Diagram (Platform)

```
Namespace: auth
  ├── Deployment: auth-api (2→10 replicas, HPA)
  │     └── Resources: 500m/2000m CPU · 512Mi/2Gi RAM
  ├── Service: auth-api (ClusterIP :8080)
  ├── NetworkPolicy: ingress=api-gateway:8080, egress=postgres:5432,vault:8200,DNS
  ├── ServiceAccount: auth-api (Vault role: auth-api-prod)
  └── HPA: min:2 max:10 cpu:70%

Ingress: nginx → auth-api (path: /auth/*)
```

Helm / manifest changes:
```
- New chart: charts/auth-api/
- New values file: environments/prod/auth-api.yaml
- Modified: namespaces/prod.yaml
```

---

## Trade-off Analysis Format

```
Choice: Synchronous resize on upload (vs. async background job)
  + Simpler: no queue, no worker, no eventual consistency
  + Photo immediately available after upload completes
  - Upload latency increases by ~200ms for resize
  - Upload service needs more CPU; scale separately if resize is expensive
  Decision: Sync for now. Switch to async if p95 upload > 2s.
```

---

## Delivery Slices Format — Codebase

```
Slice 1 (test env, 2d): Storage plumbing
  - S3 bucket + CloudFront distribution provisioned via Terraform
  - Upload endpoint: validate, store, return URL (no resize yet)
  - Unit tests for validation; integration test for upload

Slice 2 (test env, 1d): Resize
  - Add image resize (sharp or Pillow)
  - Update acceptance tests
```

## Delivery Slices Format — Platform

```
Slice 1 (staging, 1d): Namespace + RBAC + network policy
Slice 2 (staging, 1d): Deployment + HPA + Service
Slice 3 (staging, 0.5d): Observability (dashboard + alerts + runbook)
Slice 4 (production, 1d): Promote — smoke test, confirm alerts live
```

---

## Risk Register Format

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| S3 outage | Low | High | CloudFront serves cached photos; upload degrades gracefully |
| Capacity underestimated | Medium | High | Add 20% buffer; monitor 48h post-deploy |
| NetworkPolicy too restrictive | Medium | Medium | Test all egress in staging first |
