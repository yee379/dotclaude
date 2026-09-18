---
name: platform-eng-review
description: Engineering review of platform implementation plans — Helm chart quality, manifest correctness, resource tuning, health probe configuration, HPA settings, rollout strategy, GitOps alignment, and implementation sequencing. Ensures the implementation plan is correct, testable, and complete before cluster changes are made. Use when asked to "review the platform implementation plan", "check the Helm charts", or "engineering review of this platform change".
---

# Platform Engineering Review

One of the parallel reviewers on `/board-review`'s platform board (reviewer list in
`board-review/references/platform-board.md`). Runs after `/draft-prd`.

**Model routing: `sonnet`.** Engineering review of platform manifests is implementation-correctness work. Use `opus` only if complex failure domain analysis is needed.

Do NOT make cluster changes. Review the implementation plan for correctness, completeness, and quality.

---

## Priority hierarchy

Step 0 > Manifest correctness > Resource tuning > Health probes > Rollout strategy > Re-appliability & stateful transitions > Upgrade & transition path > Observability wiring > Test plan > Everything else.

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

## 6. Re-appliability and stateful transitions

§1 asks whether the chart is idempotent. This section is the version that catches things:
**what happens on the second apply, and on an apply that fails halfway?** A reconciler
will run this manifest hundreds of times, so "it worked once" is not evidence.

**Re-apply and reconciliation**
- [ ] `helm upgrade --install` re-run on an unchanged release is a no-op — no restart, no
      regenerated Secret (`randAlphaNum` in a template regenerates a password on every upgrade
      and silently breaks the consumers that cached it)
- [ ] Helm hooks are safe to re-run: a `pre-install`/`pre-upgrade` Job with a fixed name fails
      on the second apply unless it carries a delete policy. State the policy
- [ ] Jobs and one-shot migrations are idempotent **and resumable** — a pod restart mid-run must
      not corrupt or duplicate. For data backfills, work
      `/codebase-eng-review`'s `references/migration-checklist.md` **Migration mechanics**
      section; the chunking, resumability, runtime-at-production-volume, and integrity-check
      questions are identical and are usually skipped on the platform side
- [ ] **Immutable fields** are identified: Service `clusterIP`, Deployment/StatefulSet
      `selector`, StatefulSet `volumeClaimTemplates`, Job `spec.template`, PVC `storageClassName`.
      Changing one requires delete-and-recreate, not an upgrade — say so explicitly and state the
      downtime, because the apply will simply fail otherwise
- [ ] GitOps self-heal will not fight an intended manual change, and drift is surfaced rather
      than silently reverted
- [ ] A **failed** apply leaves a recoverable state: no half-created CRs, no released PVC, no
      release stuck `pending-upgrade` needing a manual rollback

**Stateful transitions** *(only when the change touches a PVC, StatefulSet, CRD, or operator)*
- [ ] PVC resize path confirmed: the StorageClass has `allowVolumeExpansion`, and **volumes
      cannot shrink** — a wrong size is a migration, not an edit
- [ ] StorageClass change requires new volumes and a data copy; the copy procedure and the
      downtime are stated
- [ ] CRD schema change: stored version, conversion strategy, and whether existing CRs remain
      readable. An `apiVersion` promotion without conversion orphans every existing object
- [ ] Operator upgrade path checked against **its** supported skew, not just Kubernetes' — and
      whether it reconciles differently on the new version
- [ ] StatefulSet rollout is ordinal-ordered and the app tolerates mixed versions across
      ordinals during it
- [ ] Backup taken and **restore tested** before any irreversible step

**STOP.** One AskUserQuestion per gap.

---

## 7. Observability wiring

§9 sequences monitoring last; nothing currently verifies it is connected. A workload that is not
scraped is invisible, and it will be discovered during the first incident.

- [ ] `ServiceMonitor`/`PodMonitor` exists **and its label selector matches** the Service — the
      usual failure is a selector mismatch that silently scrapes nothing. Confirm the target
      appears in Prometheus, do not infer it from the manifest
- [ ] The metrics port is named and exposed on the Service, and NetworkPolicy permits ingress
      from the scraper's namespace — a default-deny policy added in §2 of the security review
      blocks scraping unless it is explicitly allowed
- [ ] `PrometheusRule` exists for the failure modes `/platform-ops-review` identifies, and the
      alerts route to a receiver that exists
- [ ] A dashboard shows this workload, and RED/USE panels are populated (not empty panels
      pointing at a metric name that was never emitted)
- [ ] Logs are shipped, structured, and carry the namespace/workload labels the aggregator
      queries by
- [ ] New metric labels are bounded — no pod name, request ID, or user ID as a label value; one
      unbounded label can take the metrics backend down mid-incident
- [ ] Mesh-layer resilience is set where the mesh owns it: request timeout, retry policy and
      budget, and outlier detection. These are the platform analogue of the application checks in
      `/codebase-eng-review`'s `references/resilience-review.md` — retries configured at both
      layers multiply

**STOP.** One AskUserQuestion per gap.

---

## 8. Test plan

Load `references/test-adequacy-rubric.md` — it carries the automated-vs-manual baseline, the
per-change-type minimum coverage table, the six verification dimensions to assess, and the
blocking/warning thresholds.

Then judge the plan against it and record the verdict:

1. Identify the change type(s) this plan represents.
2. For each of the six dimensions (negative, positive, new feature, regression, smoke, timing),
   state whether the plan's existing verification is adequate — quote the plan's own step where
   it is, name what's absent where it isn't.
3. Apply the blocking/warning thresholds. Do not soften a blocking finding into a warning.
4. Write the test plan into the task file using `references/test-plan-template.md`.

**STOP.** AskUserQuestion once per missing test. Do NOT batch.

---

## 9. Implementation sequencing

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
Re-appliability:      N issues found (immutable fields: N identified)
Stateful transitions: N gaps found (or: skipped — stateless change)
Upgrade/transition:   N gaps found (or: skipped — additive change)
Observability wiring: N gaps found (scrape target confirmed: yes|no)
Test plan:            written
─────────────────────────────────────────────────────
Blocking gaps:        N
Warnings:             N
─────────────────────────────────────────────────────
Status: clean | issues_open
```
