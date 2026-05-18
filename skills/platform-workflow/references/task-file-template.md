# PLATFORM #<N> — <Title>

> **Priority:** 🟡 P2 — Medium
> **Status:** 🔄 In Progress
> **Branch:** `platform/<slug>`
> **PR:** #<number> (or — if not yet raised)
> **Created:** YYYY-MM-DD
> **Applied:** — (fill in date when live in cluster)

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

> *Populated by `/platform-draft-prd`. Output is written into Architecture/Topology, Key Decisions, and Capacity Assessment subsections below. Overwrite placeholder text — do not append.*

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

> *Populated by `/platform-draft-prd`. Overwrite placeholder steps below.*

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

## Board Review

> *Populated by `/platform-board-review` after the board completes. Do not fill manually.*

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
