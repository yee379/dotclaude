---
name: platform-draft
description: Structured platform change planning — feasibility framing, capacity assessment, infrastructure design, operational readiness requirements, security posture, ADRs, and a definition of done before any cluster change is made. Use when planning a new application onboarding, infrastructure change, capacity upgrade, or operational improvement.
---

# Platform Draft

A structured approach to planning platform and infrastructure changes before touching the cluster. Produces a clear design, capacity assessment, operational readiness checklist, and delivery sequence.

## When to Trigger

- `platform <number>` or `platform #<number>` — plan a specific platform task
- `/platform-draft` — explicit invocation
- "plan this platform change", "draft the platform plan", "run platform-draft"
- Before onboarding any new application or microservice to the cluster
- Before any significant infrastructure change (namespace strategy, network topology, storage, etc.)

When a task number is given, glob `todo/<number>-*.md` to find the task file before starting.

## Workflow position

```
/platform-draft        ← YOU ARE HERE
      │
      ├── Phase 0.5: Discovery Interview (ask why, what, who — ALWAYS)
      ├── Phase 0:   Research (if unknowns remain)
      ├── Phase 1–9: Design, capacity, ADRs, security, risk
      │
      ▼
/platform-board-review → implementation → /platform-workflow (close out)
```

**This skill assumes a platform task file already exists** (created by `/platform-workflow`). If not, create one first.

**This skill always begins with a discovery interview** — even when a task file exists. The task file records *what*; the interview surfaces *why*, *for whom*, and *whether the approach is right*.

---

## Pre-flight: Check for an existing task file

1. **If a task number was given**: glob `todo/<number>-*.md` and read it.
2. **If no task file exists**: create one via `/platform-workflow` before continuing.

If a task file already exists, use its Problem Statement and Goals as Phase 1 input — do not re-derive them. Write all output back into the task file's **Platform Design** and **Implementation Plan** sections.

---

## Phase 0.5 — Discovery Interview (REQUIRED before any design work)

**Before writing a single line of design, ask the user these questions.** Do not skip this phase, even if a task file exists — the task file captures *what*, not *why*. This interview surfaces the reasoning, constraints, and applicability that make the difference between a plan that ships safely and one that gets blocked in board review.

Ask all questions in a single message, grouped clearly. Wait for the user's answers before proceeding to Phase 1.

### Questions to ask:

**Purpose & motivation**
1. What is the underlying operational or business problem this change solves? (Not "deploy X" — what breaks, slows down, or becomes risky without this?)
2. Why now? What changed that makes this the right time to do it?
3. Who is asking for this, and what outcome are they expecting?

**Logic & approach**
4. What approach are you proposing, and why that approach over alternatives? Have you ruled out simpler options (e.g. config change, existing operator, a different tool)?
5. Is there prior art — internal or external — for this pattern on this cluster or elsewhere?
6. What is the expected failure mode if this goes wrong, and how would you recover?

**Applicability & scope**
7. Which environments does this apply to (staging only, production, all)? Does the rollout need to be phased?
8. Are there other services, namespaces, or teams that will be affected — even indirectly?
9. Are there compliance, security, or regulatory constraints that shape the design?
10. Is there a hard deadline or dependency on another change?

**Unknowns**
11. What are you least certain about in this plan? What would you want researched or validated before committing?

> **Note:** If the user has already provided clear answers to most of these in the task file or conversation, acknowledge what you already know, ask only for what is still missing, and summarise your understanding before proceeding.

---

## Phase 0 — Research (if needed)

Run `/research-handbook` or `/search-first` if any of the following are true:

- The technology, operator, or pattern is unfamiliar
- There are competing approaches and you don't know the trade-offs
- A security, compliance, or regulatory question needs an answer before design
- You're unsure whether the cluster already has infrastructure that solves this

Save findings to `todo/research/<slug>/` and link from the task file's Design section.

---

## Phase 1 — Problem framing

**Questions to answer:**

1. What problem does this change solve? (not "deploy X" — the underlying operational need)
2. What does success look like? (measurable outcome)
3. What is explicitly out of scope?
4. What are the constraints? (timeline, existing cluster topology, compliance, team size)
5. Who are the stakeholders? (platform team, application team, security, on-call)

**Output:**
```
Problem: [what is broken, missing, or at risk today]
Goal: [what we want to be true after this applies]
Success metric: [how we'll know it worked]
Out of scope: [what we are NOT doing]
Constraints: [time, topology, compliance, team]
```

---

## Phase 2 — Feasibility and capacity assessment

Before designing anything, answer: **can the cluster handle this?**

### Cluster capacity check

| Resource | Current utilisation | Change adds | Headroom after | Safe? |
|----------|-------------------|-------------|----------------|-------|
| CPU (cluster-wide) | X% | +N cores | Y% | ✅/⚠️/❌ |
| Memory | X% | +N GiB | Y% | ✅/⚠️/❌ |
| Node count | N | +N | — | ✅/⚠️/❌ |
| PVCs / storage | N in use | +N | N remaining | ✅/⚠️/❌ |
| LoadBalancer IPs | N | +N | N remaining | ✅/⚠️/❌ |
| Namespace count | N | +1 | — | ✅/⚠️/❌ |

**Safety thresholds:** Flag any resource above 75% utilisation after the change. Flag any resource above 90% as blocking.

### What else is needed?

Beyond raw compute, answer:

- **Networking:** New ingress rules, CNI config, or load balancer capacity?
- **Storage:** New StorageClasses, CSI drivers, or backup coverage?
- **Identity:** New ServiceAccounts, Vault roles, or OIDC configuration?
- **Observability:** Capacity for new dashboards and alert rules?
- **Secrets management:** New Vault policies, External Secrets paths, key rotation?
- **Compliance:** New data residency, audit logging, or regulatory requirements?
- **Support model:** On-call rotation updates? Runbook gaps?

---

## Phase 3 — Architecture Decision Records (ADRs)

For each significant infrastructure decision, write a short ADR:

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

## Phase 3.5 — Migration & Transition Path

**Only required when the plan includes any of the following:**
- A change to existing cluster topology, namespace structure, or network boundaries
- Replacement, removal, or upgrade of a running operator, CRD, or controller
- A storage class or PVC migration
- A change that affects how running workloads connect to services (DNS, endpoint, mTLS, auth)
- A Kubernetes version upgrade or a dependency with a compatibility break
- Any change that cannot be applied without affecting live traffic or running pods

**If none of the above apply, skip this phase and note: "No migration required — additive change."**

Answer each item below. If an item is not applicable, say so in one line.

```
Migration pattern:
  [ ] Expand-contract (add new resource/path, migrate consumers, remove old)
  [ ] Parallel run (old + new run simultaneously, compare outputs)
  [ ] Rolling replace (drain nodes/pods in waves, no hard cutover)
  [ ] Hard cutover (maintenance window, all-at-once)
  Chosen: ___ — Rationale: ___

Workload impact during transition:
  Which running workloads are affected during the change (not just after)?
    ___
  Will any pods be restarted, drained, or rescheduled as part of this change?
    ___
  Is there a safe apply order that minimises disruption?
    ___

Version skew:
  Can the old and new versions of affected components run simultaneously?  Y / N
  If N — what is the required apply order or maintenance window?
    ___
  Maximum safe skew window (how long both versions can coexist):
    ___

Rollback cost:
  Can the change be fully reversed without data loss or manual intervention?  Y / N
  If N — what is the point of no return and how do we communicate it?
    ___
  Estimated rollback time:  ___
  State at risk if rollback is needed (PVC data, CRD state, etc.):  ___

Deprecation / retirement:
  If replacing an existing resource or interface — when is the old one removed?
    ___
  What depends on the old resource and must be migrated first?
    ___

Traffic / connection migration:
  Is a gradual traffic shift required (canary, weighted routing)?  Y / N
  If Y — tool (Istio weights / NGINX / DNS TTL), initial %, and observation window:
    ___
  DNS or endpoint cutover required?  Y / N
  If Y — TTL reduction plan and rollback DNS path:
    ___
```

---

## Phase 4 — Infrastructure design

Diagram the topology and component relationships:

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

**Helm / manifest changes:**
- New chart: `charts/auth-api/`
- New values file: `environments/prod/auth-api.yaml`
- Modified: `namespaces/prod.yaml`

---

## Phase 5 — Operational readiness

| Readiness item | Exists today | Action required |
|----------------|-------------|-----------------|
| Runbook | ❌ | Write |
| Monitoring dashboard | ❌ | Create |
| Latency/error rate alerts | ❌ | Add Prometheus rules |
| Pod restart alert | ❌ | Add alert |
| On-call rotation updated | ❌ | Add to rotation doc |
| Capacity baseline recorded | ❌ | Document in task file |
| Backup policy | ✅ | No action |

---

### Phase 5.5 — Smoke tests, integration tests, and end-to-end tests

**For every platform change, plan the full verification suite before writing any manifests.** "It deployed" is not the same as "it works." Scripted tests are mandatory — manual curl-and-eyeball is not acceptable as a gate.

Answer each item. If an item does not apply, say so in one line.

#### Pre-change baseline (run before applying anything)

Document the current healthy state so regressions are detectable:

```
Dependency health pre-check:
  All upstream dependencies confirmed healthy before applying:
  - Database:       ___  (healthy / degraded / unknown)
  - Cache:          ___
  - External APIs:  ___
  - Message queues: ___
  - Other services: ___
  If any dependency is degraded: STOP — do not deploy into a degraded environment.
  Deploying into degraded dependencies causes misattributed incidents.

Metric baseline snapshot (record immediately before applying):
  Error rate:    ___  (e.g. 0.03%)
  p95 latency:   ___  (e.g. 42ms)
  RPS:           ___  (e.g. 1200 req/s)
  Pod count:     ___  (e.g. 4 running / 4 desired)
  CPU usage:     ___  (e.g. 34% of request)
  Memory usage:  ___  (e.g. 61% of request)
  Recorded at:   ___  (timestamp + where stored: task file / runbook / CI artifact)

Baseline smoke test:
  Script:  ___  (must be a repeatable script, not a manual step)
  Asserts: ___  (e.g. HTTP 200 on /healthz, pod count N, secret present)
  Result recorded at: ___

Existing integration/E2E tests that must still pass after the change:
  - ___  (test suite name / script path)
  - ___
```

#### Post-change verification (run immediately after each slice applies)

For each delivery slice, define what must pass before the next slice begins:

```
Slice N — smoke test:
  Script:  ___
  Asserts: ___  (what does "working" look like for this slice specifically?)
  Timing:  run immediately after apply, before proceeding

Metric delta comparison (compare against baseline snapshot, not absolute thresholds):
  Error rate:    before ___ / after ___  — delta acceptable?  Y / N
  p95 latency:   before ___ / after ___  — delta acceptable?  Y / N
  RPS:           before ___ / after ___  — unexpected drop?   Y / N
  Pod count:     before ___ / after ___  — all desired pods running?  Y / N
  CPU usage:     before ___ / after ___  — unexpected spike?  Y / N
  Memory usage:  before ___ / after ___  — unexpected spike?  Y / N
  Rollback if: error rate delta > +1%, latency delta > 2×, RPS drops > 20%, or any
               metric change cannot be explained by the change itself.

End-to-end test (full user/system flow, not just health checks):
  Script/suite:  ___
  Covers:  ___  (which user-visible or system-level behaviours are exercised?)
  Must pass before: production promotion / next slice / flag enable

Integration tests (cross-service or cross-namespace correctness):
  Script/suite:  ___
  Covers:  ___  (which service interactions does this verify?)
  Must pass before: ___
```

#### Negative-path tests (things that should be blocked)

For changes involving NetworkPolicy, RBAC, auth, or access controls:

```
What should be blocked after this change?
  - ___  (e.g. pod in namespace X cannot reach namespace Y)
Negative test script:  ___  (verifies the block is in place)
```

#### Rollback verification

```
Rollback smoke test:
  After rolling back, what must pass to confirm the cluster is back to baseline?
  Script:  ___
  Asserts: ___
```

#### Test ownership and execution

```
Who runs the tests?        ___  (platform team / CI pipeline / both)
When are they run?         ___  (automated on every apply / manual gate / both)
Where are results stored?  ___  (CI artifact / task file / runbook)
What happens on failure?   ___  (block promotion / alert on-call / rollback immediately)
```

---

## Phase 6 — Security posture

| Security concern | Action |
|-----------------|--------|
| RBAC | Define Role + RoleBinding, namespace-scoped |
| Network policy | Write NetworkPolicy (default-deny + explicit allow) |
| Secrets injection | Configure Vault role + policy |
| Image scanning | Verify CI pipeline scans on push |
| Pod security | Add securityContext (nonRoot, readOnly, drop ALL) |
| mTLS | Verify PeerAuthentication in namespace |

---

## Phase 7 — Trade-off analysis

```
Choice: Dedicated namespace vs. shared app namespace
  + Strong isolation, independent RBAC, easier blast-radius scoping
  - More namespaces to manage; more NetworkPolicies needed
  Decision: Dedicated. Security requirement justifies overhead.

Choice: Vault Agent sidecar vs. External Secrets Operator
  + Sidecar: familiar to team, already in use
  - ESO: more modern, declarative, no sidecar overhead
  Decision: Vault sidecar for now. Migrate to ESO in follow-up.
```

---

## Phase 8 — Delivery slices

```
Slice 1 (staging, 1d): Namespace + RBAC + network policy
Slice 2 (staging, 1d): Deployment + HPA + Service
Slice 3 (staging, 0.5d): Observability (dashboard + alerts + runbook)
Slice 4 (production, 1d): Promote — smoke test, confirm alerts live
```

---

## Phase 9 — Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Capacity underestimated | Medium | High | Add 20% buffer; monitor 48h post-deploy |
| NetworkPolicy too restrictive | Medium | Medium | Test all egress in staging first |
| Vault role misconfigured | Low | High | Test secret injection in staging before prod |

---

## Phase 10 — Definition of Done

- [ ] All acceptance criteria pass in staging
- [ ] Capacity headroom verified post-deploy (no resource above 80%)
- [ ] NetworkPolicy tested — permitted traffic works, denied traffic blocked
- [ ] **Pre-change baseline recorded** — smoke test run and result documented before any apply
- [ ] **Smoke tests pass** after each slice applies in staging (scripted, not manual)
- [ ] **Integration tests pass** — cross-service and cross-namespace interactions verified
- [ ] **End-to-end tests pass** — full system flow exercised, not just health checks
- [ ] **Negative-path tests pass** — blocked traffic/access confirmed blocked (if applicable)
- [ ] **Rollback smoke test defined and tested** — cluster confirmed back to baseline after rollback
- [ ] Runbook written and reviewed by at least one on-call engineer
- [ ] Monitoring dashboard live and correct
- [ ] Alerts configured and tested
- [ ] On-call rotation updated if applicable
- [ ] Security review passed
- [ ] Rollback plan documented and tested
- [ ] ADRs written for significant decisions

---

## Status update on completion

When `/platform-draft` finishes, immediately:

1. Set `**Status:**` in the task file to `⬜ Open`
2. Update the matching row in `TODO.md` to `⬜ Open`

Then prompt:

> "Plan written and status set to ⬜ Open. Ready to run `/platform-board-review` to gate this through the board before applying to the cluster?"
