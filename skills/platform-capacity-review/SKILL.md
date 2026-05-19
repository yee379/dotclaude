---
name: platform-capacity-review
description: Platform capacity and feasibility review. Assesses whether the cluster has sufficient CPU, memory, storage, networking, and control-plane headroom for a proposed change. Identifies what else is needed beyond raw compute — operators, storage classes, IP ranges, observability capacity, secrets infrastructure. Use when asked "can our cluster handle this?", "do we have enough capacity?", or "what do we need before we can run this?".
---

# Platform Capacity Review

## Workflow position

```
/platform-draft-prd
      │
      ▼
/board-review ──── runs these reviewers in parallel ────┐
      │                                                     │
      │   /platform-arch-review                             │
      │   /platform-capacity-review  ← YOU ARE HERE         │
      │   /platform-security-review                         │
      │   /platform-ops-review                              │
      │   /platform-eng-review                              │
      │   /doc-review                              │
      └─────────────────────────────────────────────────────┘
```

**Model routing: `sonnet`.** Capacity review is primarily quantitative — checking headroom, identifying resource gaps, flagging thresholds. Escalate specific architectural concerns to `platform-arch-review`.

Do NOT make cluster changes. Assess whether the cluster can absorb this change and what gaps need to be addressed first.

---

## Priority hierarchy

Step 0 > Compute headroom > Storage > Networking > Control plane > What else is needed > Everything else.

---

## Step 0: Scope Assessment

1. **What is the resource footprint of this change?** New workloads, replica counts, resource requests/limits, storage needs, network requirements.
2. **What is the current cluster state?** Read capacity data from the plan. If not present, flag as a blocking gap.
3. **Is this a greenfield add or a replacement?** Replacements may free resources.

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

- **Prometheus scrape targets:** How many new metrics endpoints? Is Prometheus sized for them?
- **Log volume:** Expected log output — does Loki/Elasticsearch have capacity?
- **Tracing:** Does this workload emit traces? Is the tracing backend sized?

---

## 6. What else is needed beyond raw compute

This is the most important section. Many platform failures happen not from resource exhaustion but from missing prerequisites.

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

Flag if any 12-month projection exceeds 80% cluster utilisation — a capacity upgrade should be planned proactively.

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
