---
name: platform-workflow
description: Institutional knowledge management for Kubernetes platform and infrastructure work. Tracks platform changes, operational health items, and infrastructure decisions as individual markdown files with a PLATFORM.md priority index, linking planning artefacts to git branches, commits, and PRs. Use when asked to "track this platform change", "what platform work is outstanding?", "add this to the platform backlog", or "show me platform status".
---

# Platform Workflow

Maintain a `platform/` directory as a prioritised backlog where every platform change, operational health item, and infrastructure decision is a first-class document. The unit of concern here is **the cluster and its operational state**, not a single application codebase.

Items tracked here include: onboarding a new application to the cluster, infrastructure design changes, capacity upgrades, observability gaps, runbook coverage, security posture improvements, and support model changes.

## When to Activate

- Onboarding a new application or microservice to the cluster
- Planning infrastructure changes (namespace strategy, network policies, storage classes, etc.)
- Tracking operational health work (runbook gaps, monitoring coverage, alert tuning)
- Capacity planning and feasibility assessment
- After running `/platform-draft` or `/platform-board-review` — persist the output
- When picking up platform work started in a previous session
- When asked to "track this platform change", "what platform work is outstanding?", or "show me platform status"

---

## The `platform/` Directory Structure

```
PLATFORM.md                          ← priority index (source of truth)
platform/
├── 001-onboard-auth-service.md
├── 002-namespace-strategy.md
├── 003-observability-coverage-gap.md
└── 004-capacity-upgrade-q2.md
```

### PLATFORM.md — The Priority Index

```markdown
# Platform Tasks

| #   | Title                              | Priority   | Status          | Branch                      | PR   |
|-----|------------------------------------|------------|-----------------|-----------------------------|------|
| [001](platform/001-onboard-auth-service.md) | Onboard auth service | 🔴 P0 | ✅ Applied | platform/onboard-auth | #12 |
| [002](platform/002-namespace-strategy.md)   | Namespace strategy   | 🟠 P1 | 🔄 In Progress | platform/namespace-strategy | — |
| [003](platform/003-observability-gap.md)    | Observability gap    | 🟡 P2 | ⬜ Open | — | — |

**Summary:** 1 applied · 1 in progress · 1 open

## Priority Key
- 🔴 P0 Critical — blocking, do immediately
- 🟠 P1 High — high value, do soon
- 🟡 P2 Medium — worth doing, schedule it
- 🔵 P3 Low — nice to have

## Status Key
- 📋 Preparing — task created, platform-draft not yet run
- ⬜ Open — platform-draft complete, awaiting /platform-board-review
- 🔎 In Review — platform-board-review board is actively running
- 🔍 Reviewed — plan approved by board, ready to implement
- 🔄 In Progress — active work
- 🏁 Implementation Done — complete, PR not yet raised
- 👀 PR Open — PR raised, awaiting review and merge
- ✅ Merged — merged to main, not yet applied to cluster
- 🚀 Applied — live in cluster
- ❌ Won't Do — cancelled, reason noted in task file
```

---

## Task File Format

```markdown
# PLATFORM #<N> — <Title>

> **Priority:** 🟡 P2 — Medium
> **Status:** 🔄 In Progress
> **Branch:** `platform/<slug>`
> **PR:** #<number> (or — if not yet raised)
> **Created:** YYYY-MM-DD
> **Applied:** — (filled when live in cluster)

---

## Problem Statement

What is wrong, missing, or at risk today on the platform?
Don't describe the solution here — describe the pain.

### What fails or is absent today

| Scenario | Current state | Desired state |
|----------|---------------|---------------|
| Auth service onboarded | No namespace, no RBAC | Fully isolated, monitored, runbook exists |

---

## Goals

1. Service runs in dedicated namespace with correct RBAC
2. Network policy restricts ingress/egress to known endpoints
3. Runbook covers all failure modes
4. Monitoring dashboard and alerts configured

## Non-Goals

What this task deliberately does not do.

---

## Platform Design

### Architecture / Topology

```
Namespace: auth
  ├── Deployment: auth-api (2→10 replicas, HPA)
  ├── Service: ClusterIP :8080
  ├── NetworkPolicy: ingress=api-gateway, egress=postgres,vault
  ├── ServiceAccount: auth-api (Vault role: auth-api-prod)
  └── HPA: min:2 max:10 cpu:70%
```

### Key Decisions

Record every "we chose X over Y because Z".

### Capacity Assessment

| Resource | Current headroom | After this change | Remaining |
|----------|-----------------|-------------------|-----------|
| CPU | 40% | +2 cores | 35% |
| Memory | 55% | +4 GiB | 48% |

### Operational Readiness

- [ ] Runbook written
- [ ] Monitoring dashboard exists
- [ ] Alerts configured
- [ ] On-call rotation updated

---

## Implementation Plan

### Step 1 — Namespace and RBAC
### Step 2 — Helm chart / manifests
### Step 3 — Network policy
### Step 4 — Secrets / Vault integration
### Step 5 — Monitoring and alerts
### Step 6 — Runbook
### Step 7 — Smoke test in staging
### Step 8 — Promote to production

---

## Implementation Checklist

- [ ] Step 1 done
- [ ] ...
- [ ] Runbook reviewed by on-call engineer
- [ ] Smoke test passed in staging
- [ ] Applied to production

---

## Problems & Solutions

### Problem: <description>
**Encountered:** YYYY-MM-DD
**Root cause:** ...
**Solution:** ...
**Lesson:** ...

---

## Open Questions

1. **Should X or Y?** — Recommendation: X, because Z.

---

## Board Review

> *Populated by `/platform-board-review` after the board completes. Do not fill manually.*

**Verdict:** CLEAR TO APPLY | CLEAR WITH WARNINGS | BLOCKED | UNSTABLE
**Date:** YYYY-MM-DD
**Rounds:** N

| Reviewer | Result | Amended | Key findings |
|---|---|---|---|
| platform-arch-review | — | — | — |
| platform-capacity-review | — | — | — |
| platform-security-review | — | — | — |
| platform-ops-review | — | — | — |
| platform-eng-review | — | — | — |
| platform-doc-review | — | — | — |

**Accepted warnings:** none
**ADRs written:** 0
```

---

## Workflow

### Starting a New Task

1. Check `PLATFORM.md` — what's the next available number?
2. Create `platform/<number>-<slug>.md` from the template above
3. Fill in at minimum: Problem Statement and Goals
4. Add a row to `PLATFORM.md` — priority, status `📋 Preparing`
5. Ask: "Shall I run `/platform-draft` now to flesh out the design?"
6. Once `/platform-draft` completes: set status to `⬜ Open`, then ask: "Shall I run `/platform-board-review`?"
7. Only after board gives CLEAR TO APPLY: create branch, begin implementation

### During Work

- After hitting a problem — add a `### Problem:` entry immediately
- Tick checklist items as they complete
- At end of session — update checklist and status

### Closing a Task

When the change is applied to the cluster:

1. Set `**Status:**` to `🚀 Applied` and `**Applied:**` to today's date
2. Update `PLATFORM.md`
3. Commit: `git commit -m "platform: <title> (PLATFORM #<n>)"`

Task files are **never deleted** — they are permanent institutional memory.

---

## Branch Naming

| Task type | Branch prefix | Example |
|-----------|--------------|---------|
| New onboarding | `platform/` | `platform/onboard-auth-service` |
| Infrastructure change | `platform/` | `platform/namespace-strategy` |
| Operational health | `platform/` | `platform/observability-gap` |

---

## Integration with Other Skills

| Skill | How it integrates |
|-------|------------------|
| `/platform-draft` | Run first; output written into task file Design section |
| `/platform-board-review` | Gate the design before applying to cluster |
| `/k8s-deploy` | How-to skill invoked during implementation |
| `/k8s-troubleshooting` | Invoked when an incident needs diagnosis |
| `/research-handbook` | Research findings saved to `platform/research/<slug>/` |
| `/codebase-scout` | May surface platform-level tech debt — log it here |
