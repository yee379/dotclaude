---
name: platform-eng-review
description: Engineering review of platform implementation plans — Helm chart quality, manifest correctness, resource tuning, health probe configuration, HPA settings, rollout strategy, GitOps alignment, and implementation sequencing. Ensures the implementation plan is correct, testable, and complete before cluster changes are made. Use when asked to "review the platform implementation plan", "check the Helm charts", or "engineering review of this platform change".
---

# Platform Engineering Review

## Workflow position

```
/platform-draft
      │
      ▼
/platform-board-review ──── runs these reviewers in parallel ────┐
      │                                                     │
      │   /platform-arch-review                             │
      │   /platform-capacity-review                         │
      │   /platform-security-review                         │
      │   /platform-ops-review                              │
      │   /platform-eng-review  ← YOU ARE HERE              │
      │   /platform-doc-review                              │
      └─────────────────────────────────────────────────────┘
```

**Model routing: `sonnet`.** Engineering review of platform manifests is implementation-correctness work. Use `opus` only if complex failure domain analysis is needed.

Do NOT make cluster changes. Review the implementation plan for correctness, completeness, and quality.

---

## Priority hierarchy

Step 0 > Manifest correctness > Resource tuning > Health probes > Rollout strategy > Test plan > Everything else.

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

## 5. Rollout strategy

- **Rolling update settings:** `maxSurge` and `maxUnavailable` set explicitly? (default 25%/25% often wrong)
- **Rollback:** Rollback procedure documented in runbook?
- **Database migrations:** If schema migration involved, is expand-contract pattern used?
- **Zero-downtime:** Correct readiness probe + PDB + preStop hook?
- **GitOps sync wave:** If using Argo CD, is wave ordering correct? (namespaces before workloads, CRDs before CRs)

**Checklist:**
- [ ] `maxSurge` and `maxUnavailable` set explicitly
- [ ] Zero-downtime rollout verified
- [ ] Rollback tested in staging
- [ ] Migration sequencing safe (if applicable)

---

## 6. Test plan

Write this into the task file's Implementation Checklist:

```markdown
## Platform Test Plan
Generated by /platform-eng-review on {date}

### Staging verification
- [ ] Helm chart applies without errors
- [ ] All pods reach Running within N minutes
- [ ] Health checks pass (liveness, readiness)
- [ ] Smoke test: [specific functional test]
- [ ] Network policy verified: permitted traffic works, denied traffic blocked
- [ ] Secret injection verified
- [ ] HPA triggers correctly under load
- [ ] Rollback tested: previous version restores cleanly

### Production promotion gates
- [ ] All staging tests pass
- [ ] Capacity headroom confirmed
- [ ] Runbook reviewed by on-call
- [ ] Alerts confirmed live
- [ ] No critical CVEs in deployed image
```

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
Test plan:            written
─────────────────────────────────────────────────────
Blocking gaps:        N
Warnings:             N
─────────────────────────────────────────────────────
Status: clean | issues_open
```
