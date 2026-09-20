# PLATFORM #<N> — <Title>

> **Priority:** 🟡 P2 — Medium
> **Status:** 🔄 In Progress
> **Branch:** `platform/<slug>`
> **PR:** #<number> (or — if not yet raised)
> **Created:** YYYY-MM-DD
> **Applied:** — (fill in date when live in cluster)

<!-- On reaching a terminal status, write the release into the Status line itself:
     `> **Status:** 🚀 Applied \`0.14.0\` — live in prod as of YYYY-MM-DD`
     or `(no release)` if the deliverable was cluster config or manifests only, which is
     the common case for platform tasks. -->

---

## Provenance

**Raised by:** <the review, closeout, rollout, incident, or board round that produced this task,
with a date where one applies — e.g. `#047(d) NetworkPolicy gap`, `post-incident 2026-08-21`,
`original backlog`>

**References:**
- [#NNN](NNN-slug.md) — <one line on *why*: dependency, blocked-by, or measurably affected. A bare
  list of numbers is not provenance.>

<!-- This section is what makes the task file readable on its own. TODO.md's Provenance and
     Reference columns are pointers to it, never the copy — when they disagree, this file wins. -->

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

## Rationale [optional]

Why now rather than later, and what cluster work this displaces. Fill this in when the change
competes for capacity or a maintenance window, or was raised by a tenant rather than by a review.
Omit it where the Problem Statement is the whole argument.

---

## Feasibility

| ID | Requirement | Verified by | Result |
|---|---|---|---|
| F-1 | Storage class `fast-ssd` exists in the target cluster | `kubectl get sc fast-ssd` | — |
| F-2 | Namespace quota admits the requested CPU | `kubectl describe quota -n <ns>` | — |

Every row names the command that settles it. Record an unresolved row as an accepted assumption
rather than leaving it blank, per `draft-prd` Phase 2.5.

---

## Platform Design

> *Populated by `/draft-prd`. Output is written into Architecture/Topology, Key Decisions, and Capacity Assessment subsections below. Overwrite placeholder text — do not append.*

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

### Security Posture

RBAC and its escalation closure, network policy, secrets handling, pod security standard, and
tenancy isolation. State the boundary each one enforces, not that it is configured.

| Control | Setting | Boundary it enforces |
|---|---|---|
| RBAC | Namespace-scoped `edit`, no `escalate` | Tenant cannot grant itself cluster read |

### Trade-offs

What each decision costs, stated as the thing given up.

| Decision | Gains | Costs | Accepted because |
|---|---|---|---|
| Dedicated namespace over shared | Hard quota and policy boundary | One more namespace to operate | Tenancy isolation is the requirement |

---

## Implementation Plan

> *Populated by `/draft-prd`. Overwrite placeholder steps below.*

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
- [ ] Relevant tests run post-apply (security tests, integration tests, smoke tests — where they exist)

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

## Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Network policy blocks an egress the workload needs | Medium | High | Staging smoke test exercises every egress | — |

Carry the residual risk explicitly. A register where every risk is mitigated to zero was not
written honestly.

---

## Definition of Done

- [ ] Every Feasibility row resolved or recorded as an accepted assumption
- [ ] Every Goal independently demonstrable against the live cluster
- [ ] Runbook exercised, not only written
- [ ] Alerts fired once in staging and resolved
- [ ] Rollback performed in staging, not just documented
- [ ] Applied release written into the Deployment Log

Distinct from the Implementation Checklist: that tracks steps taken, this states the condition the
change has to satisfy.

---

## Measured facts — measured YYYY-MM-DD, re-derive before applying

Every value someone could otherwise guess, with the command that produced it. Cluster state decays
faster than code; re-derive before each apply.

| Fact | Value | Command | Measured |
|---|---|---|---|
| Allocatable CPU on the target node pool | 96 cores | `kubectl describe node -l pool=general` | YYYY-MM-DD |

---

## Board Review

> *Populated by `/board-review` after the board completes. Do not fill manually.*

**Verdict:** CLEAR TO APPLY | CLEAR WITH WARNINGS | BLOCKED | UNSTABLE
**Date:** YYYY-MM-DD
**Rounds:** N

| Reviewer | Result | Amended | Key findings |
|---|---|---|---|
| codebase-arch-review | — | — | — |
| platform-capacity-review | — | — | — |
| platform-security-review | — | — | — |
| platform-ops-review | — | — | — |
| platform-eng-review | — | — | — |
| doc-review | — | — | — |

**Accepted warnings:** none
**ADRs written:** 0

---

## Deployment Log

> *Appended after each `make apply`. Never overwrite — one entry per apply.*

### Applied YYYY-MM-DD — <description>

**Command:** `KUBECONFIG=~/.kube/contexts/sage/prod make apply`
**Outcome:** ✅ Success | ⚠️ Partial | ❌ Failed
**Pod status:** (paste `kubectl get pods` snippet)
**Verification:** (what was checked — health, tool list, logs, end-to-end test)
**Issues encountered:** none | (description + resolution)
**Rollback taken:** no | yes — rolled back to <sha> because <reason>
**Tests run:** list any test suites executed post-apply and their outcome
