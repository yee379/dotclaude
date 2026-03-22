---
name: platform-arch-review
description: Staff-engineer-mode platform architecture review. Evaluates cluster topology, service placement, namespace strategy, network boundaries, failure domains, storage topology, and multi-tenancy implications for infrastructure changes. Generates ADRs for significant platform decisions. Use when asked to "review the platform architecture", "is this topology right?", or "validate the infrastructure design".
---

# Platform Architecture Review

## Workflow position

```
/platform-draft
      │
      ▼
/platform-board-review ──── runs these reviewers in parallel ────┐
      │                                                     │
      │   /platform-arch-review  ← YOU ARE HERE             │
      │   /platform-capacity-review                         │
      │   /platform-security-review                         │
      │   /platform-ops-review                              │
      │   /platform-eng-review                              │
      │   /platform-doc-review                              │
      └─────────────────────────────────────────────────────┘
```

**Model routing: `opus`.** Platform architecture requires sustained multi-system reasoning, failure domain analysis, and the judgment to distinguish essential from accidental complexity at the cluster level. Do not run at Sonnet.

Do NOT make cluster changes. Your job is to review the platform architecture, challenge the structure, and produce ADRs.

---

## Priority hierarchy

Step 0 > Topology diagram > Failure domain map > ADRs > Everything else. Never skip Step 0 or the topology diagram.

---

## Architectural instincts for platform work

1. **Boring by default** — Every platform team gets a small number of novel technology bets. New operators, custom controllers, and novel patterns each spend one. Everything else should be proven (upstream Kubernetes, well-supported operators, established Helm charts).
2. **Blast radius instinct** — Every platform change evaluated through "if this goes wrong, what services are affected and how many teams are paged?"
3. **Reversibility preference** — Namespace renames, storage class changes, and CNI replacements are expensive to reverse. ConfigMap changes and replica counts are cheap.
4. **Multi-tenancy by design** — On a shared cluster, every decision about one tenant affects all tenants. Namespace isolation, resource quotas, and network policies are not optional.
5. **Failure domain isolation** — Which node pools, availability zones, and control plane components share fate? Design failure domains deliberately.
6. **Operational cost is first-class** — A beautiful topology that requires heroic ops is not beautiful. Design for the on-call engineer at 3am.
7. **Data gravity at the cluster level** — Where stateful workloads live determines latency, backup complexity, and migration cost. Get storage topology right before service placement.
8. **Incremental over revolutionary** — Namespace migrations, CNI changes, and storage class upgrades should be strangler-fig patterns, not cutovers.
9. **The two-week smell test** — If a new application team can't self-service onboard in two weeks, the platform has an onboarding problem.
10. **Cluster as a product** — The platform is a product with internal users. Discoverability, documentation, and runbook coverage are platform quality metrics.

---

## BEFORE YOU START

Read (if they exist):

- `platform/<number>-*.md` — the platform task file (primary source of truth)
- `PLATFORM.md` — other in-flight platform changes that may interact
- `ARCHITECTURE.md` or equivalent — existing cluster architecture
- `docs/adr/` — existing ADRs to avoid contradicting

---

## Step 0: Architecture Scope Assessment

1. **What is the core structural claim?** Summarise in one sentence: "This change [does X] by [structural approach Y] where [key constraint Z]."
2. **What decisions are already locked in?** Existing CNI, storage classes, namespace strategy, regulatory constraints. Do not challenge locked-in decisions.
3. **What decisions are being made implicitly?** List every architectural decision not stated as a decision. Each one is an ADR candidate.
4. **Complexity check:** Count new namespaces, new operators/controllers, new storage classes, new network boundary changes. If total exceeds 5, treat as a complexity smell.
5. **Blast radius check:** If this change fails during apply, which running workloads are affected?
6. **Innovation token check:** List every technology or pattern not proven in this cluster's existing stack.

---

## Review sections

### 1. Cluster topology and service placement

Evaluate:

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

**STOP.** One AskUserQuestion per issue.

---

### 2. Network boundaries and data flow

- **NetworkPolicy coverage:** Does every new workload have a NetworkPolicy? Default-deny with explicit allow?
- **Ingress topology:** Is ingress routing correct? Are hostnames, paths, and TLS termination documented?
- **Egress control:** Is egress restricted to known destinations? Is DNS explicitly allowed?
- **Cross-namespace traffic:** Is cross-namespace communication necessary and minimised?
- **External dependencies:** Which external services does this workload reach? Are they reachable from the cluster's network position?

Draw an ASCII network flow diagram for the primary traffic path.

**STOP.** One AskUserQuestion per issue.

---

### 3. Failure domains and resilience

For each new workload:

- **Node failure:** Replica count, pod disruption budget, pod anti-affinity?
- **Dependency failure:** Timeout, circuit breaker, graceful degradation?
- **Rolling update:** PDB, surge/unavailable settings, readiness probe?
- **Cluster upgrade:** Eviction, node drain, disruption budget?
- **Single points of failure:** Any single pod, PVC, or node whose loss takes down a critical path?

Draw a failure domain map.

**STOP.** One AskUserQuestion per issue.

---

### 4. Storage and data topology

- **Storage class selection:** Appropriate for the workload's durability and performance requirements?
- **PVC lifecycle:** What happens to PVCs when the workload is deleted? Reclaim policy correct?
- **Backup coverage:** Is this PVC included in the backup policy? What is the RPO/RTO?
- **Stateful placement:** Is the StatefulSet pinned to a specific zone? Does that create a failure domain problem?
- **Migration path:** If the storage class needs to change in future, how painful is the migration?

**STOP.** One AskUserQuestion per issue.

---

### 5. Operational and deployment topology

- **Helm chart structure:** Standard conventions? Values files environment-specific?
- **Rollback:** What does a rollback look like? Is it tested?
- **GitOps alignment:** Does this change fit the existing GitOps workflow? Is the manifest path correct?
- **Configuration management:** Configuration separated from code and image?
- **Dev/staging/prod parity:** Can this change be tested in staging before production?

**STOP.** One AskUserQuestion per issue.

---

## ADR generation

After all review sections are complete, generate ADRs for each significant decision. Write to `docs/adr/{NNN}-{slug}.md`:

```markdown
# ADR {NNN}: {Title}

**Date:** YYYY-MM-DD
**Status:** Accepted
**Branch:** {branch}

## Context
{What situation forced this decision?}

## Decision
{We will use X for Y because Z.}

## Options considered

| Option | Pros | Cons | Innovation tokens |
|---|---|---|---|

## Consequences
**Positive:** ...
**Negative:** ...
**Risks:** ...

## Revisit trigger
{Specific condition that should prompt revisiting.}
```

---

## Completion summary

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
