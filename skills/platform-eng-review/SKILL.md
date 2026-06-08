---
name: platform-eng-review
description: Engineering review of platform implementation plans — Helm chart quality, manifest correctness, resource tuning, health probe configuration, HPA settings, rollout strategy, GitOps alignment, and implementation sequencing. Ensures the implementation plan is correct, testable, and complete before cluster changes are made. Use when asked to "review the platform implementation plan", "check the Helm charts", or "engineering review of this platform change".
---

# Platform Engineering Review

## Workflow position

```
/draft-prd
      │
      ▼
/board-review ──── runs these reviewers in parallel ────┐
      │                                                     │
      │   /platform-arch-review                             │
      │   /platform-capacity-review                         │
      │   /platform-security-review                         │
      │   /platform-ops-review                              │
      │   /platform-eng-review  ← YOU ARE HERE              │
      │   /doc-review                              │
      └─────────────────────────────────────────────────────┘
```

**Model routing: `sonnet`.** Engineering review of platform manifests is implementation-correctness work. Use `opus` only if complex failure domain analysis is needed.

Do NOT make cluster changes. Review the implementation plan for correctness, completeness, and quality.

---

## Priority hierarchy

Step 0 > Manifest correctness > Resource tuning > Health probes > Rollout strategy > Upgrade & transition path > Test plan > Everything else.

---

## Engineering instincts for platform work

1. **Explicit over implicit** — every resource request, limit, probe, and policy must be stated explicitly. Kubernetes defaults are often wrong for production.
2. **Boring by default** — use upstream charts before writing custom manifests. Every custom manifest is maintenance burden.
3. **Minimal diff** — achieve the platform goal with the fewest new manifests and least deviation from existing patterns.
4. **Rollout safety** — every deployment change should be safely rollback-able.
5. **Test in staging first** — no change goes to production without passing staging.

---

## Step 0: Scope Challenge

1. **What existing platform patterns already solve part of this?** Base Helm chart, standard values file, or existing operator to reuse?
2. **What is the minimum set of changes?** Flag any manifest work that could be deferred.
3. **Complexity check:** More than 5 new Kubernetes resource types or 3 new Helm charts is a smell.
4. **Implementation sequence:** Is the proposed sequence safe? Can each step be applied independently?

---

## 1. Helm chart and manifest quality

- **Chart structure:** Standard Helm conventions? Templates DRY? Helpers in `_helpers.tpl`?
- **Values file:** Environment-specific values correctly separated? Defaults sensible?
- **Labels:** Standard labels applied (`app.kubernetes.io/name`, `instance`, `version`, `managed-by`)?
- **API versions:** Deprecated API versions used? (Check against target Kubernetes version)
- **Idempotency:** Can the chart be applied multiple times without side effects?

**Checklist:**
- [ ] `helm lint` passes
- [ ] `helm template` renders without errors
- [ ] No deprecated API versions
- [ ] Standard labels on all resources
- [ ] Values file has sensible defaults

**STOP.** One AskUserQuestion per gap.

---

## 2. Resource requests and limits

**Every container must have explicit requests and limits. No exceptions in production.**

| Container | CPU request | CPU limit | Memory request | Memory limit |
|-----------|-------------|-----------|---------------|--------------|

- **Requests = actual expected usage** — not 0, not unlimited
- **Memory limit ≈ memory request** for most workloads — avoids OOM on spikes vs kills on any usage
- **CPU limit caution:** CPU limits cause throttling even when nodes have spare capacity. For latency-sensitive services, consider no CPU limit with a high request.
- **QoS class:** Do resource settings result in the intended QoS class? (Guaranteed = request==limit)

**Checklist:**
- [ ] All containers have explicit CPU and memory requests
- [ ] All containers have explicit CPU and memory limits
- [ ] QoS class is intentional

---

## 3. Health probes

**Every production workload must have liveness, readiness, and (ideally) startup probes.**

| Probe | Type | Path/Command | Initial delay | Period | Failure threshold |
|-------|------|-------------|---------------|--------|------------------|
| Liveness | | | | | |
| Readiness | | | | | |
| Startup | | | | | |

- **Liveness:** Checks app is alive — does NOT check dependencies (dependency failure should not kill the pod)
- **Readiness:** Checks app is ready to serve — DOES check dependencies
- **Startup:** Present for slow-starting apps (prevents liveness killing a pod still initialising)
- **Timeouts:** Appropriate for the application's expected response time?

**Checklist:**
- [ ] Liveness probe configured (no dependency checks)
- [ ] Readiness probe configured (with dependency checks)
- [ ] Startup probe for slow-starting applications
- [ ] Probe timeouts appropriate

---

## 4. HPA and scaling

- **HPA metrics:** Scaling on the right metric? (CPU is a proxy — request rate or queue depth often better)
- **Min/max replicas:** Minimum sufficient for availability SLO? Maximum safe for cluster capacity?
- **Scale-down stabilisation:** Long enough to avoid flapping?
- **PodDisruptionBudget:** Ensures enough replicas stay available during node drains and rolling updates?

```yaml
# PDB — required for any replicated workload
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: auth-api
```

**Checklist:**
- [ ] HPA with appropriate min/max
- [ ] HPA scaling metric is meaningful
- [ ] PDB configured
- [ ] Scale-down stabilisation window set

---

## 5. Rollout strategy and upgrade/transition path

### 5a. Rollout strategy

- **Rolling update settings:** `maxSurge` and `maxUnavailable` set explicitly? (default 25%/25% often wrong)
- **Rollback:** Rollback procedure documented in runbook?
- **Zero-downtime:** Correct readiness probe + PDB + preStop hook?
- **GitOps sync wave:** If using Argo CD, is wave ordering correct? (namespaces before workloads, CRDs before CRs)

**Checklist:**
- [ ] `maxSurge` and `maxUnavailable` set explicitly
- [ ] Zero-downtime rollout verified
- [ ] Rollback tested in staging
- [ ] GitOps sync wave ordering correct (if applicable)

---

#### 5b. Upgrade & transition path

- [ ] Migration pattern stated (rolling / blue-green / canary / hard cutover)
- [ ] Workload impact during migration quantified (disruption window, affected services)
- [ ] Version skew handled (API compatibility during transition confirmed)
- [ ] Rollback cost assessed (time, state loss, data migration reversal)
- [ ] Deprecated APIs or resources identified and migration path documented
- [ ] Traffic migration strategy defined if applicable (weight shifting, DNS cutover)

> For detailed migration planning templates, see `/draft-prd` Phase 3.5.

---

## 6. Test plan

### 6a. Automated vs manual — the baseline rule

**Automated tests are the bar. Manual verification is not a substitute.**

| Test type | Must be automated? | Rationale |
|---|---|---|
| Regression tests | ✅ Yes — must run in CI on every future deploy | Manual regression erodes immediately |
| Positive feature tests | ✅ Yes — must run in CI | Proves the feature works repeatably, not just on the day |
| Negative / security tests | ✅ Yes — must run in CI | A security control with no automated test is untested in practice |
| Smoke tests (post-deploy) | ✅ Yes — must be a script, not manual curl + eyeball | Must gate the rollout, not follow it |
| Alert firing verification | ⚠️ One-time manual acceptable | Synthetic failure is hard to automate; document the result |

Flag as **blocking** if any test is manual-only with no automation path. "I will check it" is not a test plan.

---

### 6b. Minimum coverage standard — per change type

Every plan must meet the minimum bar for its change type. Use this table to assess coverage:

| Change type | Required test coverage |
|---|---|
| New feature / new service | ✅ Positive test per new capability<br>✅ Negative test if any access control is involved<br>✅ Smoke test post-deploy<br>✅ Regression suite still passes |
| Configuration change (routing, values, flags) | ✅ Positive test: intended behaviour still works<br>✅ Regression suite still passes |
| Security control (NetworkPolicy, ipAllowList, RBAC, JWT gate) | ✅ Negative test: blocked traffic/request returns expected rejection<br>✅ Positive test: permitted traffic/request still works<br>✅ Both must be automated |
| Infrastructure change (resource tuning, HPA, probes) | ✅ Smoke test: service responds after apply<br>✅ Regression suite still passes |
| Rollback / restore | ✅ Rollback tested in staging: previous version restores cleanly |

A plan that lists fewer tests than its change type requires is **incomplete** — flag as blocking.

---

### 6c. Evaluate existing verification steps in the plan

Before writing the test plan template, assess whether the plan already has adequate verification:

**Negative-path tests** — does the plan verify that the security/access controls actually block what they should?
- e.g. for an ipAllowList change: is there a test that an external request to a blocked path returns 403?
- e.g. for a NetworkPolicy: is there a test that denied pod-to-pod traffic is actually blocked?

**Positive-path tests** — does the plan verify that legitimate traffic still works after the change?
- e.g. for a routing change: is there a test that a valid request reaches the backend?
- e.g. for a JWT gate: is there a test that a valid token returns 200, not just that an invalid token returns 401?

**New feature tests** — does the plan verify that new functionality actually works as expected?
- Every new capability must have at least one automated positive test that proves it works.
- "It deployed successfully" is not evidence the feature works.

**Regression tests** — does the plan identify existing tests that must still pass?
- What test suites already exist for the affected component?
- Are they listed as a required gate in the DoD / Implementation Checklist?
- Are they wired into CI so they run on every future deploy, not just this one?

**Smoke tests** — are they scripted, not manual?
- A smoke test must be a repeatable script (e.g. `./test/smoke-test.sh`) that asserts specific responses.
- "I curled the endpoint and it looked fine" is not a smoke test.

**Test execution timing** — are tests positioned at the right point in the implementation sequence?
- Tests must run **immediately after apply**, not deferred to "later" or left as optional manual verification.
- If a test requires a credential (e.g. `TEST_JWT`), the plan should specify how to obtain it and what to do if it's unavailable (skip gracefully, flag for manual follow-up).

Flag as **blocking** if:
- Any required test for the change type (see 6b) is missing
- Any test is manual-only with no automation path
- A security control has no automated test verifying it works (positive or negative path)
- Existing test suites are not listed as a required gate
- Tests are not wired into CI for future deploys

Flag as **warning** if:
- Test execution timing is ambiguous ("verify after apply" without specifying when, by whom, or with what script)
- A smoke test exists but is described as a manual step rather than a scripted gate

---

### 6d. Write the test plan into the task file

See `references/test-plan-template.md` for the test plan fill-in template.

---

## 7. Implementation sequencing

Safe and correct order:

1. Namespace + ResourceQuota + LimitRange
2. RBAC (ServiceAccount, Role, RoleBinding)
3. NetworkPolicy (default-deny first)
4. Secrets / Vault config
5. ConfigMaps
6. Workloads (Deployment, StatefulSet)
7. HPA + PDB
8. Ingress / Service
9. Monitoring (ServiceMonitor, PrometheusRule, Grafana dashboard)

Is the proposed sequence consistent with this order?

---

## Completion summary

```
Platform Engineering Review complete
─────────────────────────────────────────────────────
Step 0:               scope assessed
Manifest quality:     N issues found
Resource tuning:      N issues found
Health probes:        N issues found
HPA / scaling:        N issues found
Rollout strategy:     N issues found
Upgrade/transition:   N gaps found (or: skipped — additive change)
Test plan:            written
─────────────────────────────────────────────────────
Blocking gaps:        N
Warnings:             N
─────────────────────────────────────────────────────
Status: clean | issues_open
```
