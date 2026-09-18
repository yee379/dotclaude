---
name: platform-capacity-review
description: Platform capacity and feasibility review. Assesses whether the cluster has sufficient CPU, memory, storage, networking, and control-plane headroom for a proposed change. Identifies what else is needed beyond raw compute — operators, storage classes, IP ranges, observability capacity, secrets infrastructure. Use when asked "can our cluster handle this?", "do we have enough capacity?", or "what do we need before we can run this?".
---

# Platform Capacity Review

One of the parallel reviewers on `/board-review`'s platform board (reviewer list in
`board-review/references/platform-board.md`). Runs after `/draft-prd`.

**Model routing: `sonnet`** — primarily quantitative: headroom, resource gaps, thresholds.
Escalate architectural concerns to `/codebase-arch-review` in platform mode.

Do NOT make cluster changes. Assess whether the cluster can absorb this change, and what gaps
must be closed first.

**Priority hierarchy:** Step 0 > compute headroom > storage > networking > control plane > what
else is needed > everything else.

---

## Step 0: Scope assessment

1. **Resource footprint of this change?** New workloads, replica counts, requests/limits, storage,
   network.
2. **Current cluster state?** Read capacity data from the plan; if absent, that is a blocking gap.
3. **Greenfield add or replacement?** Replacements may free resources.

---

## 1. Compute headroom

| Node pool | Allocatable | Currently requested | After this change | Headroom | Safe? |
|-----------|------------|--------------------|--------------------|----------|-------|
| default | N cores | X% | X+Δ% | Y% | ✅/⚠️/❌ |
| gpu | N cores | X% | X+Δ% | Y% | ✅/⚠️/❌ |

Same table for **memory**.

**Thresholds:**
- ✅ Safe: headroom ≥ 25%
- ⚠️ Warning: headroom 10–25% — plan a capacity increase
- ❌ Blocking: headroom < 10% — cannot proceed without adding nodes

**Pod density:** Flag if nodes are approaching max-pods-per-node limit (default 110).

**STOP.** One AskUserQuestion per ⚠️ or ❌ finding.

---

## 2. Storage

| Resource | Capacity | In use | After change | Remaining | Safe? |
|----------|----------|--------|--------------|-----------|-------|
| PVCs (count) | N | N | +N | N | ✅/⚠️/❌ |
| StorageClass: gp3 | — | N GiB | +N GiB | — | ✅/⚠️/❌ |
| etcd size | — | N GiB | +Δ | — | ✅/⚠️/❌ |

Additional questions:
- Does this require a new StorageClass? Does it exist? Is the CSI driver installed?
- Does this require a new backup policy?
- Is there a storage quota per namespace that this will hit?
- What is the data growth rate? Is there a retention/pruning plan?

**STOP.** One AskUserQuestion per gap.

---

## 3. Networking

| Resource | Capacity | In use | After change | Remaining | Safe? |
|----------|----------|--------|--------------|-----------|-------|
| LoadBalancer IPs | N | N | +N | N | ✅/⚠️/❌ |
| Pod CIDR | /16 = 65536 | N used | +N | N | ✅/⚠️/❌ |
| Service CIDR | /16 | N used | +N | N | ✅/⚠️/❌ |
| Ingress rules | N | N | +N | — | ✅/⚠️/❌ |

Additional questions:
- Does this require a new Ingress class or load balancer?
- Does the pod CIDR have room for new nodes? (Flag if > 70% consumed)
- Does this require new egress routes or firewall rules?
- Does this introduce new DNS names? Are certs in place?

**STOP.** One AskUserQuestion per gap.

---

## 4. Control plane overhead

- **API server request rate:** Will this workload generate high API server load (frequent watches, HPA polling, operator reconcile loops)?
- **etcd size:** Large amounts of ConfigMap, Secret, or CRD data?
- **Namespace count:** Approaching manageability thresholds? (Flag if > 100 without a clear management strategy)
- **CRD count:** New CRDs required? Approaching scaling limits?
- **Webhook load:** New validating/mutating webhooks that could slow admission?

---

## 5. Observability capacity

**Sizing only.** Whether an alert or dashboard exists, routes to the right receiver, and carries
a `runbook_url` is `/platform-ops-review`'s call — do not raise those findings here.

- **Prometheus scrape targets:** How many new metrics endpoints? Is Prometheus sized for them?
- **Log volume:** Expected log output — does Loki/Elasticsearch have capacity?
- **Tracing:** Does this workload emit traces? Is the tracing backend sized?

---

## 6. What else is needed beyond raw compute

The most important section. Platform failures come more often from a missing prerequisite than from
resource exhaustion.

**Existence check, not a correctness review.** Confirm each prerequisite exists and is reachable; do
not evaluate its content. The Vault role/policy, OIDC client, and service-mesh rows belong to
`/platform-security-review`; the Grafana datasource and alertmanager routing rows belong to
`/platform-ops-review`. Flag a missing one and defer the substance to that reviewer.

| Prerequisite | Status | Action required |
|---|---|---|
| Vault role + policy for this service | ✅/⚠️/❌ | |
| External Secrets path / ESO SecretStore | ✅/⚠️/❌ | |
| Image registry credentials / pull secret | ✅/⚠️/❌ | |
| DNS record for new hostname | ✅/⚠️/❌ | |
| TLS certificate (cert-manager or manual) | ✅/⚠️/❌ | |
| Grafana datasource for new metrics | ✅/⚠️/❌ | |
| PagerDuty/alertmanager routing rule | ✅/⚠️/❌ | |
| OIDC client registration (if SSO needed) | ✅/⚠️/❌ | |
| Service mesh PeerAuthentication policy | ✅/⚠️/❌ | |
| Backup policy for new PVCs | ✅/⚠️/❌ | |
| Node labels/taints for affinity rules | ✅/⚠️/❌ | |
| Cluster autoscaler node group config | ✅/⚠️/❌ | |

**STOP.** One AskUserQuestion per ⚠️ or ❌ item.

---

## 7. Capacity projections

For workloads that will scale over time:

| Metric | Current | 3 months | 6 months | 12 months |
|--------|---------|----------|----------|-----------|
| Replicas | N | N | N | N |
| Storage | N GiB | N GiB | N GiB | N GiB |
| CPU request | N cores | N | N | N |

Flag if any 12-month projection exceeds 80% cluster utilisation — plan the capacity upgrade in
advance.

---

## Completion summary

```
Platform Capacity Review complete
─────────────────────────────────────────────────────
Compute headroom:     ✅ safe | ⚠️ warning | ❌ blocking
Storage:              ✅ safe | ⚠️ warning | ❌ blocking
Networking:           ✅ safe | ⚠️ warning | ❌ blocking
Control plane:        ✅ safe | ⚠️ warning | ❌ blocking
Observability:        ✅ safe | ⚠️ warning | ❌ blocking
Prerequisites missing: N items
─────────────────────────────────────────────────────
Blocking gaps:        N
Warnings:             N
─────────────────────────────────────────────────────
Status: clear | warnings | blocked
```
