# Platform Mode — Cluster Architecture Review

Loaded only when `Mode: Platform` was detected. These instincts and sections **supplement**
the codebase instincts in `references/arch-instincts.md` and **replace** codebase review
sections 1–5 in `SKILL.md`.

## Additional instincts
Adapted for shared-cluster platform work:

1. **Multi-tenancy by design** — On a shared cluster, every decision about one tenant affects all tenants. Namespace isolation, resource quotas, and NetworkPolicies are not optional.
2. **Blast radius at the cluster level** — If this change fails during apply, which running workloads are affected and how many teams are paged?
3. **Reversibility at the platform level** — Namespace renames, storage class changes, and CNI replacements are expensive to reverse. ConfigMap changes and replica counts are cheap.
4. **Data gravity at the cluster level** — Where stateful workloads live determines latency, backup complexity, and migration cost. Get storage topology right before service placement.
5. **Cluster as a product** — The platform is a product with internal users. Discoverability, documentation, and runbook coverage are platform quality metrics.
6. **The two-week onboarding test** — If a new application team can't self-service onboard in two weeks, the platform has an onboarding problem.

## Context gathering

Read (if they exist):

- `platform/<number>-*.md` or `todo/<number>-*.md` — the platform task file (primary source of truth)
- `PLATFORM.md` — other in-flight platform changes that may interact
- `ARCHITECTURE.md` or equivalent — existing cluster architecture
- `docs/adr/` — existing ADRs to avoid contradicting

## Step 0 additions

Add these checks to the standard Step 0:

5. **Blast radius check:** If this change fails during apply, which running workloads are affected?
6. **Complexity check (platform):** Count new namespaces, new operators/controllers, new storage classes, new network boundary changes. If total exceeds 5, treat as a complexity smell.

## Review sections

P1–P5 below replace `SKILL.md` review sections 1–5. Every other part of the skill — Step 0, the
global stop rule, ADR generation, required outputs, questioning protocol — still applies.

## P1. Cluster topology and service placement

- **Namespace strategy:** Is each namespace scoped to a team, a service, or an environment? Consistent with existing namespaces?
- **Resource ownership:** Does each PVC, ConfigMap, and Secret have exactly one owning namespace?
- **Node affinity:** Are workloads placed on appropriate node pools? Is placement documented?
- **Multi-tenancy:** Does this change respect existing tenant isolation?
- **Service mesh topology:** Is the service included in the mesh? Is mTLS enforced?

Draw an ASCII topology diagram:

```
Cluster
├── Namespace: auth (team: identity)
│     ├── auth-api (Deployment, 2→10 replicas)
│     │     → Service: ClusterIP :8080
│     │     → NetworkPolicy: ingress=api-gateway, egress=postgres,vault
│     └── ServiceAccount: auth-api
├── Namespace: api-gateway
│     └── gateway (Deployment) → Ingress → auth-api
└── Namespace: postgres (shared stateful)
      └── postgres (StatefulSet, PVC: 100Gi gp3)
```

---

## P2. Network boundaries and data flow

- **NetworkPolicy coverage:** Does every new workload have a NetworkPolicy? Default-deny with explicit allow?
- **Ingress topology:** Is ingress routing correct? Are hostnames, paths, and TLS termination documented?
- **Egress control:** Is egress restricted to known destinations? Is DNS explicitly allowed?
- **Cross-namespace traffic:** Is cross-namespace communication necessary and minimised?
- **External dependencies:** Which external services does this workload reach? Are they reachable from the cluster's network position?

Draw an ASCII network flow diagram for the primary traffic path.

---

## P3. Failure domains and resilience

For each new workload:

- **Node failure:** Replica count, pod disruption budget, pod anti-affinity?
- **Dependency failure:** Timeout, circuit breaker, graceful degradation?
- **Rolling update:** PDB, surge/unavailable settings, readiness probe?
- **Cluster upgrade:** Eviction, node drain, disruption budget?
- **Single points of failure:** Any single pod, PVC, or node whose loss takes down a critical path?

Draw a failure domain map.

---

## P4. Storage and data topology

- **Storage class selection:** Appropriate for the workload's durability and performance requirements?
- **PVC lifecycle:** What happens to PVCs when the workload is deleted? Reclaim policy correct?
- **Backup coverage:** Is this PVC included in the backup policy? What is the RPO/RTO?
- **Stateful placement:** Is the StatefulSet pinned to a specific zone? Does that create a failure domain problem?
- **Migration path:** If the storage class needs to change in future, how painful is the migration?

---

## P5. Operational and deployment topology (platform)

- **Helm chart structure:** Standard conventions? Values files environment-specific?
- **Rollback:** What does a rollback look like? Is it tested?
- **GitOps alignment:** Does this change fit the existing GitOps workflow? Is the manifest path correct?
- **Configuration management:** Configuration separated from code and image?
- **Dev/staging/prod parity:** Can this change be tested in staging before production?

## Completion summary

Use this instead of the codebase completion summary in `SKILL.md`:

```
Platform Architect Review complete
─────────────────────────────────────────────────────
Step 0:               scope assessed, N implicit decisions surfaced
Topology:             N issues found
Network boundaries:   N issues found
Failure domains:      N issues found
Storage/data:         N issues found
Operational topology: N issues found
─────────────────────────────────────────────────────
ADRs generated:       N (written to docs/adr/)
Blast radius:         acceptable | ⚠️ elevated | ❌ unacceptable
Innovation tokens:    N spent
─────────────────────────────────────────────────────
Status: clean | decisions_open
```

---
