---
name: platform-security-review
description: Platform-level security review for Kubernetes infrastructure changes. Covers RBAC, network policies, secrets management, pod security standards, multi-tenancy isolation, service mesh mTLS, image supply chain, and cluster-wide security posture implications. Distinct from /security-review which covers application-layer API and code security. Use when onboarding a new workload, changing cluster security posture, or reviewing infrastructure for security implications.
---

# Platform Security Review

## Workflow position

```
/platform-draft
      │
      ▼
/platform-board-review ──── runs these reviewers in parallel ────┐
      │                                                     │
      │   /platform-arch-review                             │
      │   /platform-capacity-review                         │
      │   /platform-security-review  ← YOU ARE HERE         │
      │   /platform-ops-review                              │
      │   /platform-eng-review                              │
      │   /platform-doc-review                              │
      └─────────────────────────────────────────────────────┘
```

**Model routing: `opus`.** Platform security requires adversarial reasoning — tracing trust boundaries across the full cluster, thinking like an attacker, and catching subtle RBAC and network policy misconfigurations. Do not run at Sonnet or Haiku.

Do NOT make cluster changes. Find security gaps in the platform plan before anything is applied.

For **application-layer** security (API auth, input validation, secrets in code), defer to `/security-review`.

---

## Priority hierarchy

Step 0 > RBAC > Network policy > Secrets > Pod security > Multi-tenancy > Supply chain > Everything else.

---

## Step 0: Security Scope Assessment

1. **What is the trust boundary change?** New service handling sensitive data, new network path, new identity?
2. **What is the blast radius of a compromise?** If the new workload is compromised, what can it reach?
3. **Does this change affect cluster-wide security posture?** New admission webhooks, new ClusterRoles, new CRDs, new operators?

---

## 1. RBAC and Identity

**Principle of least privilege — every ServiceAccount has only what it needs.**

- **ServiceAccount scoping:** Dedicated ServiceAccount? Namespace-scoped?
- **ClusterRole vs Role:** Is ClusterRole actually necessary, or does a namespace Role suffice?
- **Verb minimisation:** Only required verbs granted? No `verbs: ["*"]` or `resources: ["*"]`?
- **Automount:** Is `automountServiceAccountToken: false` set for workloads that don't need API access?
- **Human RBAC:** New human-facing ClusterRoleBindings? Are they scoped correctly?

```yaml
# GOOD: namespace-scoped, minimal verbs, specific resourceNames
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: auth-api
  namespace: auth
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]
    resourceNames: ["auth-tls"]
```

**Checklist:**
- [ ] Dedicated ServiceAccount per workload
- [ ] Role (not ClusterRole) unless cluster-wide access genuinely required
- [ ] No wildcard verbs or resources
- [ ] `automountServiceAccountToken: false` where API access not needed
- [ ] No human ClusterRoleBindings granting cluster-admin

**STOP.** One AskUserQuestion per gap.

---

## 2. Network Policy

**Default deny — every workload must have explicit ingress and egress rules.**

- **Default deny in namespace:** Default-deny NetworkPolicy present?
- **Ingress rules:** Restricted to specific namespaces/pods/ports?
- **Egress rules:** Restricted to known destinations? DNS explicitly allowed?
- **Cross-namespace traffic:** Minimised and justified?
- **External egress:** Should internet egress be restricted?

```yaml
# Default deny — required in every new namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: auth
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
# Explicit allow per workload
spec:
  podSelector:
    matchLabels:
      app: auth-api
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: api-gateway
      ports:
        - port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: postgres
      ports:
        - port: 5432
    - ports:
        - port: 53
          protocol: UDP  # DNS
```

**Checklist:**
- [ ] Default-deny NetworkPolicy in every new namespace
- [ ] Explicit ingress policy for every new workload
- [ ] Explicit egress — no unrestricted outbound
- [ ] DNS egress explicitly allowed

**STOP.** One AskUserQuestion per gap.

---

## 3. Secrets Management

- **Secret storage:** Vault / External Secrets Operator / sealed-secrets? Not hardcoded in manifests?
- **Injection method:** Vault Agent, ESO, projected volumes — not plain env vars from Secret where avoidable
- **Scope:** Secrets namespace-scoped? Can other namespaces read them?
- **Rotation:** Secret rotation plan exists? Short-lived credentials used?
- **etcd encryption:** Kubernetes Secrets encrypted at rest in etcd?

**Checklist:**
- [ ] No secret values in YAML manifests or ConfigMaps
- [ ] Secrets managed by Vault / ESO / sealed-secrets
- [ ] Secrets namespace-scoped
- [ ] Secret rotation plan exists
- [ ] etcd encryption confirmed

**STOP.** One AskUserQuestion per gap.

---

## 4. Pod Security Standards

```yaml
# Required on every production workload
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  fsGroup: 1001
containers:
  - securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
```

- Flag any `privileged: true` — almost never acceptable
- Flag any `hostPath` mounts — bypass namespace isolation
- Flag `hostNetwork`, `hostPID`, `hostIPC` — break container isolation
- **PodSecurity admission:** Does the namespace have a PodSecurity label? Does the workload comply?

**Checklist:**
- [ ] `runAsNonRoot: true`
- [ ] `allowPrivilegeEscalation: false`
- [ ] `readOnlyRootFilesystem: true`
- [ ] `capabilities: drop: ["ALL"]`
- [ ] No `privileged: true`, no `hostPath`, no `hostNetwork/hostPID/hostIPC`
- [ ] Namespace PodSecurity label set appropriately

**STOP.** One AskUserQuestion per gap.

---

## 5. Multi-tenancy and isolation

**A compromise of one tenant must not affect other tenants.**

- **Namespace isolation:** Enforced by NetworkPolicy AND RBAC?
- **Resource quotas:** New namespace has ResourceQuota? (Prevents one tenant consuming all cluster resources)
- **LimitRanges:** Namespace has LimitRanges? (Prevents unbounded containers)
- **Tenant blast radius:** If compromised, can it read secrets from other namespaces?

```yaml
# ResourceQuota — every new namespace
apiVersion: v1
kind: ResourceQuota
metadata:
  name: auth-quota
  namespace: auth
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
    count/pods: "20"
```

**Checklist:**
- [ ] ResourceQuota set for new namespace
- [ ] LimitRange set
- [ ] Tenant blast radius assessed

---

## 6. Service mesh and mTLS

- **Mesh inclusion:** Is the new workload in the service mesh?
- **mTLS mode:** Is STRICT mTLS enforced? Is plaintext blocked?
- **AuthorizationPolicy:** Restricts which services can call this workload?
- **Sidecar injection:** Enabled for the namespace/deployment?

**Checklist:**
- [ ] Namespace labeled for sidecar injection
- [ ] PeerAuthentication: `mtls.mode: STRICT`
- [ ] AuthorizationPolicy: default deny with explicit allow

---

## 7. Image supply chain

- **Registry:** Approved registry? Private?
- **Tag policy:** Pinned to digest, not tag? (Tags are mutable)
- **Scanning:** CVE scan passed? No critical unmitigated findings?
- **Base image:** Minimal (distroless, alpine)? Pinned?
- **Admission control:** Cluster admission controller enforces image policy?

```yaml
# Pin to digest
image: registry.slac.stanford.edu/auth-api@sha256:abc123...
```

**Checklist:**
- [ ] Image from approved registry
- [ ] Image pinned to digest
- [ ] CVE scan passed
- [ ] Admission controller enforces image policy

---

## 8. Cluster-wide security posture implications

- **New operators/controllers:** ClusterRole required? Blast radius if compromised?
- **New webhooks:** `failurePolicy` appropriate? Timeout set?
- **New CRDs:** New attack surface?
- **Audit logging:** New security-relevant events to audit?

---

## Completion summary

```
Platform Security Review complete
─────────────────────────────────────────────────────
RBAC:                 ✅ clean | ⚠️ warnings | ❌ blocking
Network policy:       ✅ clean | ⚠️ warnings | ❌ blocking
Secrets:              ✅ clean | ⚠️ warnings | ❌ blocking
Pod security:         ✅ clean | ⚠️ warnings | ❌ blocking
Multi-tenancy:        ✅ clean | ⚠️ warnings | ❌ blocking
Service mesh / mTLS:  ✅ clean | ⚠️ warnings | ❌ blocking
Image supply chain:   ✅ clean | ⚠️ warnings | ❌ blocking
Cluster-wide impact:  ✅ clean | ⚠️ warnings | ❌ blocking
─────────────────────────────────────────────────────
Blocking gaps:        N
Warnings:             N
─────────────────────────────────────────────────────
Status: clean | warnings | blocked
```
