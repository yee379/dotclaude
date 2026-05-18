---
name: codebase-draft
description: Structure outline feature planning and architectural design — user interview, problem framing, user stories, requirements, module design, ADRs, system design, trade-offs, sequencing, and a definition of done before writing any code. Output can be written to the task file and/or submitted as a GitHub issue.
triggers:
  - "plan #\\d+"
  - "plan \\d+"
  - "plan todo #?\\d+"
  - "/codebase-draft"
  - "write a prd"
  - "write-a-prd"
  - "create a prd"
  - "product requirements document"
license: MIT
compatibility: opencode
---

# Plan Draft

A structured approach to planning and outlining features and architectural changes before writing code. Produces a clear spec, design decisions, and delivery sequence.

## When to Trigger

Activate this skill when the user says any of the following:
- `plan <number>` — e.g. "plan 3", "plan 007"
- `plan #<number>` — e.g. "plan #3", "plan #007"
- `plan todo <number>` — e.g. "plan todo 3", "plan todo 007"
- `plan todo #<number>` — e.g. "plan todo #3", "plan todo #007"
- `/codebase-draft` — explicit invocation
- "plan this out", "let's plan", "run codebase-draft" on a task
- `outline <number>` - e.g. "outline 3", "outline 007"
- `structure outline <number>` - e.g. "structure outline 3", "structure outline 007"
- "write a PRD", "create a PRD", "write-a-prd", "product requirements document"

When a task number is given, glob `todo/<number>-*.md` (zero-padded or not) to find the task file before starting.

## Workflow position

```
/codebase-draft            ← YOU ARE HERE: problem framing, requirements, system design, ADRs
      │
      ▼
/codebase-board-review → implementation → /codebase-closeout → /prod-release
```

Use `/codebase-draft` first — before architecture review or implementation. Its output (problem statement, requirements, rough design, ADRs) is the input that `codebase-arch-review` needs to do a meaningful structural review.

Once the plan exists, run `/codebase-board-review` to gate it through the complete review pipeline in one go.

---

## When to Use

- Planning a significant new feature or system change
- Making an architectural decision (database choice, service split, API design)
- Estimating scope and sequencing work
- Creating an RFC or design document for team review
- Deciding between competing technical approaches

---

## Planning Workflow

You may skip steps if they are clearly not necessary for the task at hand.

### Pre-flight: User Interview

Ask the user for a **brief initial description** of the problem and what they have in mind. Keep this opening request short — you'll resolve the details through exploration and follow-up.

Once you have the initial description, do not ask a long list of questions. Instead:

**1. Explore first.**
Read the codebase, existing task file, tests, docs, ADRs, and anything referenced in the description. Check for: existing patterns you should follow or avoid, constraints implied by the current architecture, prior decisions recorded anywhere, and gaps or conflicts between the user's stated intent and the current state of the code. Answer as many questions as you can without involving the user.

**2. Ask about what you cannot determine.**
After exploration, bring targeted questions to the user — only about things genuinely requiring human input: decisions involving preference or priority, trade-offs with no objectively correct answer, conflicting signals you found in the codebase, and unknowns only the user can resolve. Ask one thread at a time. Wait for the answer. If the answer opens new questions or requires more lookups, do them before asking again.

**3. Surface conflicts explicitly.**
If exploration reveals something that conflicts with or complicates the user's stated approach — an existing abstraction, a prior ADR, a coupling that makes the plan harder — surface it directly: *"I found X, which conflicts with Y. How do you want to resolve this?"*

**4. Iterate until shared understanding.**
Keep exploring and asking until you can restate the full plan — goals, scope, approach, constraints, affected users, edge cases, failure modes — and the user confirms it is correct. Do not proceed to Phase 1 until this point is reached. There is no fixed number of rounds; keep going as long as there are genuine unresolved questions.

---

### Pre-flight: Check for an existing task file

Before starting, check whether a task file already exists for this item:

1. **If a task number was given** (e.g. "plan #007"): glob `todo/007-*.md` and read it.
2. **If working from the current branch**: check `TODO.md` for a matching `🔄 In Progress`
   or `⬜ Open` item and read its task file.
3. **If no task file exists**: create one now via `/codebase-workflow` before continuing —
   the task file is the plan's home.

**If a task file already exists** (e.g. created by `/codebase-scout` or added manually):
- Use its **Problem Statement** as Phase 1 input — do not re-derive the problem from scratch.
- Use its **Goals** as the starting point for Phase 2 requirements.
- Check whether a **Design** section is already partially filled — if so, start from there
  rather than a blank slate.
- **Phase 0 research** can usually be skipped unless the Design section is empty *and* the
  technology is unfamiliar. The scout or whoever created the file has already done the
  problem-identification work.

All output from the planning phases below should be written back into the task file's
**Design** and **Implementation Plan** sections — not into a separate document.

---

### Phase 0 — Research & Codebase Exploration

This phase runs in parallel with the Pre-flight interview, not after it. Every round of exploration is an opportunity to answer questions before asking the user.

**What to explore:**
- Relevant source files, tests, and existing similar features
- Prior ADRs, design docs, or task files that touch this area
- Library docs, changelogs, or migration guides if an external dependency is involved
- Whether something solving this already exists in the codebase or ecosystem

**When to run `/research-handbook` or `/search-first`:**
- The technology, library, or approach is unfamiliar
- There are competing approaches and the trade-offs are unclear
- A regulatory, security, or compliance question must be resolved before design can start

Save findings to `todo/research/<slug>/` and link from the task file's **Design** section. Feed discoveries back into the interview loop — new findings may resolve open questions or open new ones. Continue until no meaningful unknowns remain.

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

### Phase 1.5 — User Stories

Write a long, numbered list covering all actors and all aspects of the feature. Every user story must follow this format:

```
As a <actor>, I want <feature>, so that <benefit>
```

Example:
```
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
2. As a mobile bank customer, I want to upload a profile photo, so that my account feels personalised
3. As an admin, I want to remove user photos, so that I can enforce content policy
```

The list should be **extremely extensive** and cover all aspects of the feature — happy paths, error paths, edge cases, admin flows, and any other actor that interacts with it. Check this list with the user before proceeding.

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

For each significant technical decision, write a short ADR. Use the format from `~/.claude/skills/codebase-arch-review/references/adr-template.md`. Example:

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

### Phase 3.5 — Module Design

Sketch out the major modules you will need to **build or modify** to complete the implementation. Actively look for opportunities to extract **deep modules**.

> A **deep module** (as opposed to a shallow module) is one that encapsulates a lot of functionality behind a **simple, testable interface** that rarely changes. Prefer these over shallow wrappers that just pass data through.

For each module, describe:
- **Name** and responsibility
- **Interface** (what goes in, what comes out) — not the file path or internal details
- **Whether it is new or a modification** of something existing
- **Testability** — can it be tested in isolation?

Example:
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

Check this module list with the user before continuing. Ask which modules they want tests written for.

---

**Only required when the plan includes any of the following:**
- A schema or data model change affecting live data
- A breaking or backward-incompatible API change
- Replacement or removal of a running service or component
- A change to how consumers discover or connect to a service (endpoint, protocol, auth)
- A dependency upgrade with a compatibility break

**If none of the above apply, skip this phase and note: "No migration required — additive change."**

Answer each item below. If an item is not applicable, say so in one line.

```
Migration pattern:
  [ ] Expand-contract (add new path, migrate consumers, remove old path)
  [ ] Strangler fig (route % of traffic to new, drain old)
  [ ] Parallel run (run old + new simultaneously, compare outputs)
  [ ] Hard cutover (maintenance window, all-at-once)
  Chosen: ___ — Rationale: ___

Backward compatibility window:
  Which existing consumers/clients must still work after the change ships?
    ___
  Until when must the old interface/schema remain available?
    ___
  How will we know all consumers have migrated?
    ___

Version skew:
  Can the old and new versions run simultaneously during rollout?  Y / N
  If N — what is the required deployment order or downtime window?
    ___
  Maximum safe skew window (time both versions can coexist):
    ___

Rollback cost:
  Can the migration be reversed without data loss?  Y / N
  If N — what is the point of no return and how do we signal it?
    ___
  Estimated rollback time:  ___
  Data at risk if rollback is needed:  ___

Deprecation timeline:
  When is the old interface/schema/service retired?
    ___
  What is the communication plan for consumers?
    ___
  Who is responsible for tracking and enforcing the cutover?
    ___

Traffic migration:
  Feature flag required?  Y / N
  If Y — flag name, initial %, and rollout stages:
    ___
  Canary required before full rollout?  Y / N
  If Y — canary size and observation window:
    ___
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

### Status update on completion

When `/codebase-draft` finishes writing the plan into the task file, **immediately**:

1. Set `**Status:**` in the task file to `⬜ Open`
2. Update the matching row in `TODO.md` to `⬜ Open`
3. Do **not** set status to `🔍 Reviewed` — that is reserved for after `/codebase-board-review` passes.

Then prompt the user:

> "Plan written and status set to ⬜ Open. Ready to run `/codebase-board-review` to gate this through
> the board before implementation?"

---

## Output Template

When planning a feature, produce a document with these sections:

```
# Feature: [Name]

## Problem & Goal
## User Stories
## Requirements (FR + NFR + AC)
## Module Design
## Architecture (diagram + data model + API contract)
## ADRs
## Trade-offs
## Delivery Slices
## Risk Register
## Definition of Done
```

Keep it concise — the goal is alignment, not documentation theatre.
A good plan is one page; a great plan is two pages with diagrams.
