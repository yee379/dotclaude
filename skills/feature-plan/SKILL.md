---
name: feature-plan
description: Structured feature planning and architectural design — problem framing, requirements, ADRs, system design, trade-offs, sequencing, and a definition of done before writing any code.
license: MIT
compatibility: opencode
---

# Feature Plan

A structured approach to planning features and architectural changes before writing code. Produces a clear spec, design decisions, and delivery sequence.

## Workflow position

```
/feature-plan          ← YOU ARE HERE: problem framing, requirements, system design, ADRs
      │
      ▼
/full-review → implementation → /plan-closeout → /prod-release
```

Use `/feature-plan` first — before architecture review or implementation. Its output (problem statement, requirements, rough design, ADRs) is the input that `plan-arch-review` needs to do a meaningful structural review.

Once the plan exists, run `/full-review` to gate it through the complete review pipeline in one go.

---

## When to Use

- Planning a significant new feature or system change
- Making an architectural decision (database choice, service split, API design)
- Estimating scope and sequencing work
- Creating an RFC or design document for team review
- Deciding between competing technical approaches

---

## Planning Workflow

### Phase 0 — Research (if needed)

Before framing the problem, check whether there are unknowns that would make the plan speculative.
Run `/deep-research` or `/search-first` if any of the following are true:

- The technology, library, or approach is unfamiliar
- There are competing approaches and you don't know the trade-offs yet
- You're unsure whether something already exists in the codebase or ecosystem
- A regulatory, security, or compliance question needs an answer before design can start

Save findings to `todo/research/<slug>/` and link from the task file's **Design** section.
If everything is well-understood, skip this phase.

---

### Phase 1 — Problem framing

Before designing anything, agree on the actual problem.

**Questions to answer:**
1. What user/system problem does this solve? (not "implement X" — the underlying need)
2. What does success look like? (measurable outcome)
3. What is explicitly out of scope?
4. What are the constraints? (deadline, team size, existing tech, compliance)
5. Who are the stakeholders and what do they care about?

**Output:**
```
Problem: [one sentence — what breaks or is missing today]
Goal: [one sentence — what we want to be true after this ships]
Success metric: [how we'll know it worked]
Out of scope: [what we are NOT doing]
Constraints: [time, tech, team, compliance]
```

---

### Phase 2 — Requirements

Split into functional and non-functional:

**Functional requirements** — what the system must do:
```
FR-1: Users can upload a profile photo (max 5MB, JPEG/PNG/WebP)
FR-2: Photos are resized to 256x256 on upload
FR-3: Old photo is deleted when a new one is uploaded
FR-4: Photo URL is returned in the user profile API response
```

**Non-functional requirements** — how well it must do it:
```
NFR-1: Upload completes in < 3s on a 10 Mbps connection
NFR-2: Photos served from CDN with < 50ms TTFB globally
NFR-3: System handles 100 concurrent uploads without degradation
NFR-4: Photos stored durably (99.999% availability)
```

**Acceptance criteria** — definition of done (testable):
```
AC-1: Given a valid JPEG, when uploaded, then a 256x256 thumbnail is stored and URL returned
AC-2: Given a file > 5MB, when uploaded, then a 400 is returned with a clear error message
AC-3: Given a new upload, when complete, the old photo is removed from storage within 60s
```

---

### Phase 3 — Architecture Decision Records (ADRs)

For each significant technical decision, write a short ADR:

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

### Phase 4 — System design

Diagram the data flow and component interactions:

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

**Data model changes:**

```sql
-- migration
ALTER TABLE users ADD COLUMN photo_url TEXT;
ALTER TABLE users ADD COLUMN photo_updated_at TIMESTAMPTZ;
-- backward-compatible: nullable, no default needed
```

**API contract:**

```
POST /users/:id/photo
  Content-Type: multipart/form-data
  Body: file (required)
  Auth: Bearer token (own profile or admin)

Response 200:
  { "photo_url": "https://cdn.example.com/photos/abc123.jpg" }

Response 400:
  { "error": { "code": "INVALID_FILE", "message": "..." } }

Response 413:
  { "error": { "code": "FILE_TOO_LARGE", "message": "Max 5MB" } }
```

---

### Phase 5 — Trade-off analysis

For each significant choice, explicitly state what you're giving up:

```
Choice: Synchronous resize on upload (vs. async background job)
  + Simpler: no queue, no worker, no eventual consistency
  + Photo immediately available after upload completes
  - Upload latency increases by ~200ms for resize
  - Upload service needs more CPU; scale separately if resize is expensive
  Decision: Sync for now. Switch to async if p95 upload > 2s.

Choice: Single 256×256 thumbnail (vs. multiple sizes)
  + Simple storage, simple invalidation
  - Frontend cannot use different sizes; may look bad on retina displays
  Decision: Ship 256×256. Add 512×512 in follow-up if design requests it.
```

---

### Phase 6 — Sequencing & milestones

Break into shippable slices — each must be deployable and useful on its own:

```
Slice 1 (test env, 2d): Storage plumbing
  - S3 bucket + CloudFront distribution provisioned via Terraform
  - Upload endpoint: validate, store, return URL (no resize yet)
  - Unit tests for validation; integration test for upload

Slice 2 (test env, 1d): Resize
  - Add image resize (sharp or Pillow)
  - Update acceptance tests

Slice 3 (staging, 1d): Deletion
  - Background worker to delete old photos
  - Lifecycle rules on S3 as safety net
  - Load test: 100 concurrent uploads

Slice 4 (production, 0.5d): Promote
  - Prod deploy with feature flag
  - Monitor error rate + upload latency
  - Enable for all users after 24h soak
```

---

### Phase 7 — Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| S3 outage | Low | High | CloudFront serves cached photos; upload degrades gracefully |
| Large files bypass validation | Medium | Medium | Validate at API gateway (body size limit) AND in service |
| Resize OOM on large images | Low | Medium | Cap input resolution before resize; set container memory limit |
| Old photo not deleted | Medium | Low | S3 lifecycle rule auto-deletes after 30d as backstop |

---

### Phase 8 — Definition of Done

A feature is done when ALL of the following are true:

- [ ] All acceptance criteria pass in staging
- [ ] Unit tests cover happy path + all error cases
- [ ] Integration/E2E test covers the full user flow
- [ ] Load test passes NFR targets (latency, concurrency)
- [ ] Security review completed (auth, input validation, no PII leaks)
- [ ] Database migration tested against production-sized dataset
- [ ] Rollback plan documented and tested
- [ ] Monitoring: alerts configured for error rate and latency
- [ ] Runbook updated for on-call
- [ ] API documentation updated
- [ ] Feature flag in place for gradual rollout

---

## Output Template

When planning a feature, produce a document with these sections:

```
# Feature: [Name]

## Problem & Goal
## Requirements (FR + NFR + AC)
## Architecture (diagram + data model + API contract)
## ADRs
## Trade-offs
## Delivery Slices
## Risk Register
## Definition of Done
```

Keep it concise — the goal is alignment, not documentation theatre.
A good plan is one page; a great plan is two pages with diagrams.
