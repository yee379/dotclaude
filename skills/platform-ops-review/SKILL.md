---
name: platform-ops-review
description: Platform operational readiness review. Evaluates runbook coverage, monitoring and alerting completeness, on-call support model, incident response preparedness, and observability for a proposed platform change. Ensures the cluster is operable — not just functional — before a change is applied. Use when asked to "check ops readiness", "is there a runbook?", "are we ready to support this?", or as part of /board-review.
---

# Platform Ops Review

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
      │   /platform-ops-review  ← YOU ARE HERE              │
      │   /platform-eng-review                              │
      │   /doc-review                              │
      └─────────────────────────────────────────────────────┘
```

**Model routing: `sonnet`.** Ops review is primarily checklist-driven gap identification. Escalate novel failure mode analysis to `opus` if needed.

Do NOT make cluster changes. Identify operational readiness gaps before a change is applied.

---

## Priority hierarchy

Step 0 > Runbook coverage > Monitoring/alerting > On-call model > Incident response > Everything else.

---

## Operational instincts

1. **Design for the 3am engineer** — Every change must be operable by a tired human with incomplete context. No runbook = not done.
2. **Observability is a requirement** — You cannot support what you cannot see. Dashboards and alerts are deliverables, not follow-ups.
3. **Known failure modes beat unknown ones** — Document what can go wrong and how to recover. An undocumented failure mode discovered at 3am is an incident waiting to happen.
4. **Alert fatigue kills on-call** — Every alert must have a clear owner, a clear action, and a clear resolution.
5. **SLOs before alerts** — Define what "healthy" means before defining what "broken" means.

---

## Step 0: Ops Scope Assessment

1. **What new failure modes does this change introduce?** List every way the new workload can fail (crash, OOM, dependency timeout, storage full, certificate expiry, etc.).
2. **What existing runbooks are affected?** Does this change invalidate existing runbooks?
3. **Who owns this workload operationally?** Is there a clear team, on-call rotation, and escalation path?

---

## 1. Runbook coverage

A runbook is mandatory for every production workload. Written before go-live — not after the first incident.

### Runbook completeness checklist

- [ ] **Service overview** — what it does, who owns it, criticality level
- [ ] **Normal operating state** — what healthy looks like (expected metrics, log patterns)
- [ ] **Health check procedure** — how to verify health manually
- [ ] **Common failure modes** — for each: symptoms, diagnosis steps, resolution, escalation
- [ ] **Restart / rollback procedure** — exact commands
- [ ] **Scaling procedure** — how to manually scale if HPA is insufficient
- [ ] **Secret rotation procedure** — how to rotate credentials without downtime
- [ ] **Dependency failure procedures** — what to do when each upstream is down
- [ ] **Data recovery procedure** — how to restore from backup
- [ ] **Contact list** — service owner, escalation path

### Failure mode coverage table

| Failure mode | Runbook section | Alert fires? | Auto-recovers? |
|---|---|---|---|
| Pod OOMKilled | Restart procedure | ✅ | ✅ (k8s restart) |
| Dependency timeout | Dependency failure | ✅ | ⚠️ |
| Certificate expiry | Secret rotation | ⚠️ | ❌ |
| Storage full | Scaling procedure | ❌ | ❌ | ← gap |

**Flag** any failure mode with no runbook section AND no auto-recovery as a blocking gap.

**STOP.** One AskUserQuestion per blocking runbook gap.

---

## 2. Monitoring and alerting

### SLI/SLO definition

| SLI | SLO target | Measurement window |
|-----|-----------|-------------------|
| Request success rate | ≥ 99.5% | 30-day rolling |
| P99 latency | ≤ 500ms | 5-min window |
| Pod availability | ≥ 99.9% | 30-day rolling |

**Flag** if no SLOs are defined — alert thresholds without SLOs are arbitrary.

### Required alerts

| Alert | Condition | Severity | Action |
|---|---|---|---|
| High error rate | error_rate > 5% for 5m | critical | Page on-call |
| High latency | p99 > 1s for 5m | warning | Investigate |
| Pod restart loop | restarts > 3 in 10m | critical | Page on-call |
| Low replica count | available < requested | critical | Page on-call |
| Disk pressure | pvc_used > 85% | warning | Expand or clean |
| Certificate expiry | tls_cert_expiry < 7d | warning | Rotate |
| OOMKilled | oom_kills > 0 | warning | Tune memory |

For each alert verify:
- [ ] Condition is correct and tested (synthetic failure fired)
- [ ] Routes to correct receiver (PagerDuty, Slack)
- [ ] Has `runbook_url` annotation
- [ ] Not noisy in normal operation

### Dashboard completeness

- [ ] Request rate (RPS)
- [ ] Error rate (%)
- [ ] P50/P95/P99 latency
- [ ] Pod count (desired vs available)
- [ ] CPU and memory utilisation vs request vs limit
- [ ] PVC utilisation (%)
- [ ] Upstream dependency health
- [ ] Recent pod restarts

**STOP.** One AskUserQuestion per monitoring gap.

---

## 3. On-call support model

- **Ownership:** Clear team owning this workload in production?
- **Rotation:** Workload added to on-call rotation?
- **Escalation path:** If primary on-call cannot resolve, who is escalated to?
- **Support hours:** 24/7 workload requires 24/7 coverage?
- **Alert fatigue audit:** Are existing alerts for this team in good health before adding more?

**Checklist:**
- [ ] Owning team identified
- [ ] Added to on-call rotation
- [ ] Escalation path documented

**STOP.** One AskUserQuestion per gap.

---

## 4. Incident response preparedness

- **Blast radius documented:** Who else is affected if this service goes down?
- **Communication plan:** Defined path for incidents affecting multiple teams?
- **Post-mortem process:** Post-mortem template and process in place?
- **Access:** Does the on-call engineer have the access needed to execute the runbook? (kubectl, Vault, logs)

---

## 5. Operational debt and drift

- **Existing runbooks invalidated?** If this service replaces or modifies an existing one, the old runbook may now be misleading.
- **Related dashboards still accurate?** Cross-service dependency changes can break existing dashboards.

### Drift detection

Running state drifting silently from declared state is one of the most common sources of "works on my cluster" incidents. A change that looks clean in git may be deploying into a cluster that has already drifted.

**Pre-deploy drift check (mandatory before any production apply):**

```bash
# Compare committed manifests against what is actually running
kubectl diff -f deploy/prod/manifests/ --namespace <ns> || true

# For Helm-managed third-party charts
helm diff upgrade <release> <chart> -f values-prod.yaml
```

- [ ] `kubectl diff` run against the target environment — unexpected live state identified and explained before applying
- [ ] Any unexplained drift (manual `kubectl apply`, out-of-band change, failed previous rollout) is resolved or documented before proceeding
- [ ] GitOps sync status checked if Argo CD / Flux is in use — no OutOfSync resources in the affected namespace

**Ongoing drift detection:**

- [ ] A mechanism exists to detect drift continuously (Argo CD sync status, Flux drift detection, or a scheduled `kubectl diff` in CI)
- [ ] Drift alerts are routed to the owning team, not silently ignored
- [ ] The runbook documents what to do when drift is detected (reconcile vs. investigate first)

---

## Completion summary

```
Platform Ops Review complete
─────────────────────────────────────────────────────
Runbook coverage:     ✅ complete | ⚠️ gaps | ❌ missing
Failure modes:        N documented, N with no runbook + no auto-recovery
Monitoring:           ✅ complete | ⚠️ gaps | ❌ missing
Alerting:             N required, N configured, N missing
SLOs defined:         ✅ yes | ❌ no
On-call model:        ✅ clear | ⚠️ gaps | ❌ undefined
Incident response:    ✅ ready | ⚠️ gaps | ❌ not ready
Drift detection:      ✅ pre-deploy check + ongoing | ⚠️ gaps | ❌ none
─────────────────────────────────────────────────────
Blocking gaps:        N
Warnings:             N
─────────────────────────────────────────────────────
Status: ready | warnings | not_ready
```
