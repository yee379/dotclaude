---
name: platform-security-review
description: Platform-level security review for Kubernetes infrastructure changes. Covers RBAC and its escalation closure, network policies, secrets management, pod security standards, multi-tenancy isolation, service mesh mTLS, image supply chain, cluster-wide security posture implications, API audit and runtime detection coverage, and data at rest including backups and residency. Distinct from /security-review which covers application-layer API and code security. Use when onboarding a new workload, changing cluster security posture, or reviewing infrastructure for security implications.
---

# Platform Security Review

One of the parallel reviewers on `/board-review`'s platform board (reviewer list in
`board-review/references/platform-board.md`). Runs after `/draft-prd`.

**Model routing: `opus`.** Platform security requires adversarial reasoning — tracing trust boundaries across the full cluster, thinking like an attacker, and catching subtle RBAC and network policy misconfigurations. Do not run at Sonnet or Haiku.

Do NOT make cluster changes. Find security gaps in the platform plan before anything is applied.

For **application-layer** security (API auth, input validation, secrets in code), defer to `/security-review`.

---

## Priority hierarchy

Step 0 > RBAC and its escalation paths > Network policy > Secrets > Pod security > Multi-tenancy > Detection & audit > Supply chain > Data at rest > Everything else. **Never skip the RBAC escalation closure** — it is the check a verb-by-verb review passes and an attacker does not.

---

## Step 0: Security Scope Assessment

1. **What is the trust boundary change?** New service handling sensitive data, new network path, new identity?
2. **What is the blast radius of a compromise?** If the new workload is compromised, what can it reach?
3. **Does this change affect cluster-wide security posture?** New admission webhooks, new ClusterRoles, new CRDs, new operators?
4. **Which adversary does this change most expose the cluster to?** A compromised neighbouring workload, a tenant escaping its namespace, a compromised CI or GitOps credential, or a human with break-glass access? Name it — the rest of the review prioritises against it.
5. **Would a compromise be visible?** If the answer is "we'd see it in the audit log", check in §9 that the log actually covers these resources and survives an attacker with cluster-admin.

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

### RBAC escalation paths

Least privilege is not the same as *non-escalating*. Kubernetes RBAC grants authority
transitively, and several innocuous-looking permissions are equivalent to a much larger one.
Walk the closure for every new Role and ClusterRole — this is the check that catches the grants a
verb-by-verb review passes.

| Granted | Actually equivalent to | Why |
|---|---|---|
| `create pods` in a namespace | **Any ServiceAccount in that namespace** | The pod can be created with any SA and mount its token |
| `create` on deployments / jobs / cronjobs / daemonsets | Same as above, indirectly | Controllers create the pods for you — a namespace's workload-create is its SA set |
| `get`/`list` secrets in a namespace | Every identity whose token or credential lives there | Includes SA token secrets |
| `get`/`list` secrets **cluster-wide** | **cluster-admin, in practice** | Some secret somewhere is privileged |
| `pods/exec`, `pods/attach`, `pods/portforward` | The pod's identity, filesystem, and network position | Bypasses NetworkPolicy from inside the mesh |
| `pods/ephemeralcontainers` | Same as `exec`, and often overlooked in policy | Debug containers join the pod |
| `escalate` or `bind` on roles | The right to grant more than you hold | Defeats the normal RBAC guard that you cannot grant what you lack |
| `impersonate` | Any user, group, or ServiceAccount | Also launders the audit trail unless both identities are recorded |
| `create` on serviceaccounts/token | A token for any SA in scope | Direct credential minting |
| `create`/`update` on validating/mutatingwebhookconfigurations | Interception or mutation of every API request | Cluster takeover; also a cluster-wide availability risk |
| `patch` nodes, or node/proxy access | Kubelet reach, therefore every pod on the node | Node identity is broad |
| `create` on CRs of a privileged operator | Whatever that operator's SA can do | The operator is the deputy |
| `update` on a GitOps Application / HelmRelease | Whatever the GitOps controller's SA can do | Usually cluster-admin |

- [ ] Closure walked for each new Role/ClusterRole; any path reaching another identity's
      credentials or cluster-admin is named with its severity
- [ ] Deferred/automated actors included — the GitOps controller, CI's cluster credential, and
      any operator reconciling on a user's behalf (confused deputy: whose authority applies at
      reconcile time?)
- [ ] **Break-glass** cluster-admin access: who holds it, is it time-bound, is it separate from
      day-to-day identity, and is every use alerted rather than merely logged? See §9

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
image: <your-registry>/auth-api@sha256:abc123...
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

---

## 9. Detection, audit, and forensic readiness

Sections 1–8 are prevention. This one answers: **if this workload or credential were
compromised, would we know, and could we reconstruct it?** An attacker who reaches cluster-admin
can delete in-cluster logs, so the answer depends almost entirely on decisions made before the
incident. Application-layer detection is `/security-review` §4.13; this is the cluster layer.

- **API audit policy covers the new resources** at a useful level — `Metadata` for most,
  `RequestResponse` for secrets, RBAC objects, and webhook configurations. A new CRD is not
  audited by a policy that enumerates resources explicitly
- **`exec`, `attach`, and `port-forward` are audited and alerted**, not merely logged. These are
  the human break-glass paths and the most valuable single signal the cluster produces
- **Impersonation records both identities** — the impersonator and the impersonated. Without
  this, `impersonate` is a way to act with no attribution
- **Audit logs ship off-cluster** promptly, to a store the cluster's own credentials cannot
  delete. In-cluster-only retention fails exactly in the scenario it exists for
- **Retention stated** and long enough for a dwell time measured in months
- **RBAC and policy changes alerted** — any new ClusterRoleBinding, any binding to cluster-admin,
  any webhook configuration change
- **Runtime detection** for the new workload where one is deployed (Falco or equivalent):
  unexpected process, unexpected outbound connection, write to a read-only path, shell in a
  container
- **Denials are visible:** mesh `AuthorizationPolicy` denials, NetworkPolicy drops (where the CNI
  can report them), and ingress 403s. A default-deny you cannot observe is a default-deny you
  cannot debug or alert on
- **Admission webhook rejections and failures logged** — a failing webhook is both a security
  control that stopped working and, with the wrong `failurePolicy`, an outage
- **Forensic question, answered now:** given this workload's ServiceAccount compromised at time
  *T*, can you list what it called and what it read?

**STOP.** One AskUserQuestion per gap.

---

## 10. Data at rest, backups, and residency

Platform-layer counterpart to `/security-review`'s `references/data-governance.md`. The data a
workload holds is a platform concern the moment it lands on a volume.

- **Classification of what this workload persists** — is any of it restricted (personal,
  financial, health, credentials) or governed by a DUA, IRB protocol, or export control? The
  class determines everything below, so an unstated class is a finding
- **Volume encryption** at rest, and whose key — cloud-managed, or one you control and can rotate
- **PVC access mode and reclaim policy:** `Retain` leaves data on a released volume that outlives
  the namespace; `Delete` destroys it on a mistaken `helm uninstall`. Either can be wrong — state
  which was chosen and why
- **Volume snapshots and backups:** encrypted, access-controlled, and **not readable from another
  namespace or tenant**. A backup bucket is frequently the weakest copy of the strongest data
- **Restore is tested**, and a restore does not resurrect data a deletion request removed
- **Residency:** does the storage class, backup destination, or replica target place data in a
  region the governing agreement prohibits?
- **Egress destinations** the workload writes to (object storage, external database, telemetry
  backend) are enumerated and NetworkPolicy-constrained to them — cross-ref §2
- **Non-production copies:** does any lower environment restore from a production backup? If so
  it inherits production classification with weaker controls

**STOP.** One AskUserQuestion per gap.

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
Detection & audit:    ✅ clean | ⚠️ warnings | ❌ blocking
Data at rest:         ✅ clean | ⚠️ warnings | ❌ blocking
─────────────────────────────────────────────────────
RBAC escalation:      N paths walked, N reaching other identities or cluster-admin
Blocking gaps:        N
Warnings:             N
─────────────────────────────────────────────────────
Status: clean | warnings | blocked
```
