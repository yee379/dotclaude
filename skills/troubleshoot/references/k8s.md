# Kubernetes Diagnostics Reference

<!-- BEFORE RUNNING ANY KUBECTL COMMAND: look for a k8s-access skill in the project's .claude/skills/k8s-access/SKILL.md and apply it. If found, read it and follow all environment variable and KUBECONFIG instructions it contains. Only proceed with Phase 0 once access is configured. -->

The golden rule: always understand the data path before touching individual components. Traffic enters through an Ingress or Gateway → reaches a Service → is load-balanced to Pods → Pods connect to backends. Understand that path before chasing symptoms.

## Top-down vs bottom-up

**Top-down** (user impact → root cause) — use for active production incidents:
```
User/Service Impact → DNS → Load Balancer → Ingress/Gateway → Service → Pod → App
```

**Bottom-up** (infrastructure → workload) — use for mass Pending pods, node failures, cluster upgrades:
```
Node/OS → kubelet/CRI → Container/Image → Pod Scheduling → Workload → Service → App
```

## The 7-layer traffic path

```
Internet
   │  [Layer 1] DNS: nslookup api.example.com → resolves to LB IP?
   ▼
Load Balancer / NodePort
   │  [Layer 2] kubectl get svc -n ingress-nginx → EXTERNAL-IP assigned?
   ▼
Ingress Controller Pod
   │  [Layer 3] kubectl get pods -n ingress-nginx → Running?
   ▼
Ingress Resource / HTTPRoute
   │  [Layer 4] kubectl describe ingress <name> → events clean?
   ▼
Service
   │  [Layer 5] kubectl get endpoints <svc> → POPULATED? ← most common failure
   ▼
Pod / Container
   │  [Layer 6] kubectl get pods → Running + Ready?
   ▼
Application
      [Layer 7] kubectl logs <pod> → no errors?
```

Work down this chain. Stop at the first broken layer — that's your blast radius.

---

## Phase 0 — Orient: confirm cluster context

```bash
kubectl config current-context
kubectl config get-contexts
echo $KUBECONFIG

kubectl get namespaces
kubectl get nodes -o wide
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded | head -40
```

---

## Phase 1 — Architecture scan: map the data path

Always start here — understand what resources exist and how they connect before looking at logs.

### Ingress and Gateways

```bash
kubectl get ingress -A
kubectl describe ingress <name> -n <namespace>

# Controller health
kubectl get pods -n ingress-nginx
kubectl get pods -n istio-system

# Gateway API
kubectl get gatewayclass && kubectl get gateway -A && kubectl get httproute -A

# Controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=100

# IngressClass binding (required K8s 1.28+)
kubectl get ingressclass
kubectl get ingress <name> -n <namespace> -o jsonpath='{.spec.ingressClassName}'

# Istio
istioctl analyze -n <namespace>
kubectl get gateway,virtualservice,destinationrule -n <namespace>
istioctl proxy-status
```

### Services

```bash
kubectl get svc -A

# Empty endpoints = no healthy pods (most common failure)
kubectl get endpoints <service-name> -n <namespace>
kubectl describe svc <service-name> -n <namespace>

# Verify selector labels match pod labels
kubectl get svc <service-name> -n <namespace> -o jsonpath='{.spec.selector}'
kubectl get pods -n <namespace> -l app=<label-value>
```

### Workload inventory

```bash
kubectl get deploy,statefulset,daemonset,job,cronjob -n <namespace>

kubectl rollout status deployment/<name> -n <namespace>
kubectl rollout status statefulset/<name> -n <namespace>

# StatefulSet: pods must come ready in order
kubectl get pods -n <namespace> -l app=<name> --sort-by=.metadata.name

# DaemonSet: which nodes are missing the pod?
kubectl get pods -n <namespace> -l <daemonset-label> -o wide
kubectl describe daemonset <name> -n <namespace>
```

---

## Phase 2 — Pod-level triage

### Pod status and events

```bash
kubectl get pods -n <namespace> -o wide
kubectl describe pod <pod-name> -n <namespace>
# Key sections: Conditions, Events, Last State (exit code), Limits

kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -30
kubectl get events -A --sort-by='.lastTimestamp' | grep -v Normal | tail -30
```

### Common pod failure patterns

| Status | Exit Code | Cause | First action |
|--------|-----------|-------|--------------|
| `CrashLoopBackOff` | 1 | App startup error | `kubectl logs --previous` |
| `CrashLoopBackOff` | 137 | OOMKilled | Increase `limits.memory` or fix leak |
| `CrashLoopBackOff` | 143 | SIGTERM not handled | Check graceful shutdown |
| `Pending` | — | No schedulable node | `describe pod` → Events |
| `Pending` | — | PVC not bound | `kubectl get pvc` |
| `Pending` | — | Image pull failure | `ImagePullBackOff` event |
| `Evicted` | — | Node memory/disk pressure | `kubectl describe node` → Conditions |
| `Init:CrashLoopBackOff` | — | Init container failing | `kubectl logs <pod> -c <init-container>` |
| `0/1 Endpoints` | — | Readiness probe failing | Check probe config + health endpoint |

### Log scanning

```bash
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
kubectl logs <pod-name> -n <namespace> -c <container-name>

# All replicas simultaneously
kubectl logs -n <namespace> -l app=<name> --tail=100 --follow
kubectl logs -n <namespace> -l app=<name> --tail=50 --prefix=true

# stern (preferred for incidents — colour-coded, multi-pod)
stern <pod-name-regex> -n <namespace> --since 15m
stern . -n <namespace> --since 5m
stern <name> -A --since 5m

# Error filter
kubectl logs -n <namespace> -l app=<name> --tail=500 | grep -iE "error|fatal|panic|exception"
```

---

## Phase 3 — Storage diagnostics

Storage issues silently cause StatefulSets and databases to fail. Check early when pods are Pending or stuck.

```bash
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc-name> -n <namespace>

kubectl get pv
kubectl get storageclass
kubectl describe storageclass <name>

# Provisioner health
kubectl get pods -n kube-system | grep -i provisioner
kubectl get pods -n storage-system          # Rook/Ceph
kubectl get pods -n longhorn-system

# Common issues:
# 1. Pending → no matching PV or StorageClass misconfiguration
# 2. Lost → underlying PV deleted while PVC was bound
# 3. RWX needed but StorageClass only supports RWO
kubectl get pvc <name> -n <namespace> -o jsonpath='{.spec.accessModes}'

# Storage usage inside a pod
kubectl exec -it <pod-name> -n <namespace> -- df -h
```

---

## Phase 4 — Database and backend connectivity

### DNS resolution

```bash
# From a debug pod
kubectl run dns-test --image=busybox:1.36 --restart=Never --rm -it \
  -- nslookup <service-name>.<namespace>.svc.cluster.local

# CoreDNS health
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50
```

### Port connectivity

```bash
# TCP test
kubectl run net-test --image=busybox:1.36 --restart=Never --rm -it \
  -- nc -zv <service-name>.<namespace>.svc.cluster.local 5432

# Netshoot — full debug pod (curl, dig, nmap, tcpdump, iperf3)
kubectl run netshoot --image=nicolaka/netshoot --restart=Never --rm -it -- /bin/bash

# Port-forward to bypass ingress/service entirely
kubectl port-forward svc/<service> 8080:80 -n <namespace>

# Check env vars in the failing pod
kubectl exec -it <pod-name> -n <namespace> -- env | grep -iE "db|database|pg|mysql|redis"
```

### Database-specific

```bash
# PostgreSQL
kubectl exec -it <db-pod> -n <namespace> -- pg_isready -U postgres

# MySQL
kubectl exec -it <db-pod> -n <namespace> -- mysqladmin ping -h 127.0.0.1 -u root -p

# Redis
kubectl exec -it <redis-pod> -n <namespace> -- redis-cli ping

# StatefulSet ordering — pod-N waits for pod-(N-1) to be Ready
kubectl get pods -n <namespace> -l app=postgres --sort-by=.metadata.name
```

---

## Phase 5 — Network and CNI (Cilium)

Network issues are often silent — pod Running but traffic silently dropped.

```bash
# Cilium health
kubectl exec -n kube-system ds/cilium -- cilium status
cilium connectivity test
kubectl get pods -n kube-system -l k8s-app=cilium -o wide

# NetworkPolicy audit
kubectl get networkpolicy -A
kubectl describe networkpolicy <name> -n <namespace>
kubectl get ciliumnetworkpolicy -A
kubectl get ciliumclusterwidenetworkpolicy

# Hubble flow monitoring
hubble observe --verdict DROPPED --follow
hubble observe --from-pod <ns>/<pod> --to-pod <ns>/<pod> --follow

# Policy trace
cilium policy trace --src-k8s-pod <ns>/<pod> --dst-k8s-pod <ns>/<pod> --dport <port>/TCP --verbose

# Common trap: NetworkPolicy blocking DNS (port 53/UDP) — always check egress to kube-dns
```

---

## Phase 6 — Resource pressure and scheduling

```bash
kubectl top nodes
kubectl top pods -n <namespace> --sort-by=memory
kubectl describe node <node-name> | grep -A 10 "Allocated resources"

# Node conditions (MemoryPressure, DiskPressure, PIDPressure)
kubectl get nodes -o json | \
  jq '.items[] | {name: .metadata.name, conditions: .status.conditions[] | select(.type != "Ready")}'

# Resource quotas
kubectl describe resourcequota -n <namespace>
kubectl describe limitrange -n <namespace>

# Scheduling failure reason
kubectl describe pod <pod-name> -n <namespace> | grep -A 20 "Events:"
```

---

## Root-cause traps

Use these before finalising Phase 4 hypotheses:

| Symptom | Common wrong hypothesis | Actual cause (check this) |
|---------|------------------------|---------------------------|
| Pod `CrashLoopBackOff` | "App is broken" | Exit code: 137=OOM, 1=app error, 143=unhandled SIGTERM |
| Service unreachable | "Network policy blocking" | Empty Endpoints — label selector mismatch is 10× more common |
| 502/504 from ingress | "Ingress misconfigured" | Readiness probe failing → no healthy pods behind service |
| StatefulSet stuck | "Storage issue" | Pod ordering — pod-N won't start until pod-(N-1) is Ready |
| Intermittent failures | "Resource contention" | Clock skew, DNS TTL, or retry storm from upstream |
| `Pending` pod | "Not enough resources" | Taint/toleration mismatch or missing node selector |

---

## Quick diagnostic one-liners

```bash
# All non-running/non-completed pods cluster-wide
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded

# All recent Warning events
kubectl get events -A --field-selector=type=Warning --sort-by='.lastTimestamp' | tail -40

# Pods restarting most frequently
kubectl get pods -A --sort-by='.status.containerStatuses[0].restartCount' | tail -20

# Services with no endpoints (broken selectors)
kubectl get endpoints -A | awk '$3 == "<none>" {print $1, $2}'

# Nodes with pressure conditions
kubectl get nodes -o json | \
  jq -r '.items[] | .metadata.name as $n |
    .status.conditions[] |
    select(.type != "Ready" and .status == "True") |
    [$n, .type, .message] | @tsv'

# Count Warning events by reason
kubectl get events -n <namespace> -o json | jq '
  [.items[] | select(.type=="Warning")]
  | group_by(.reason)
  | map({reason: .[0].reason, count: length})
  | sort_by(.count) | reverse'
```

---

## Event-driven debugging

Events are short-lived (default 1-hour TTL) but contain the most actionable real-time information. Read them before logs.

```bash
kubectl get events -A --field-selector type=Warning --sort-by='.lastTimestamp' | tail -30
kubectl events --for pod/<pod-name> -n <namespace>
kubectl events --types=Warning --watch -n <namespace>

# Storage events
kubectl get events -A --sort-by='.lastTimestamp' | grep -iE "volume|pvc|pv|mount|attach"

# Scheduling failures
kubectl get events -A --field-selector reason=FailedScheduling
```

### Common Warning event reasons

| Event Reason | Resource | Meaning |
|---|---|---|
| `BackOff` | Pod | CrashLoopBackOff — container keeps crashing |
| `OOMKilling` | Node | Container killed for exceeding memory limit |
| `FailedScheduling` | Pod | No node satisfies pod's requirements |
| `FailedAttachVolume` | Pod | CSI driver can't attach the disk |
| `FailedMount` | Pod | Volume mount failed on the node |
| `Evicted` | Pod | Node pressure evicted the pod |
| `NodeNotReady` | Node | kubelet stopped reporting |
| `Unhealthy` | Pod | Liveness/readiness probe failing |
| `FailedSync` | Ingress | Ingress controller reconcile error |
| `ServiceNotFound` | Ingress | Backend service doesn't exist |

---

## 10-minute incident runbook

```bash
# ── TRIAGE (0-2 min) ─────────────────────────────────────────
kubectl get nodes -o wide | grep -v " Ready"
kubectl get pods -n <namespace> | grep -v Running
kubectl get events -n <namespace> --field-selector type=Warning \
  --sort-by='.lastTimestamp' | tail -15
kubectl rollout history deployment/<app> -n <namespace>

# ── ARCHITECTURE CHECK (2-4 min) ─────────────────────────────
kubectl get endpoints -n <namespace>              # empty = label mismatch
kubectl get ingress -n <namespace>
kubectl get pvc -n <namespace> | grep -v Bound

# ── DEEP DIVE (4-8 min) ──────────────────────────────────────
FAILED=$(kubectl get pods -n <namespace> | grep -vE "Running|NAME|Completed" | awk '{print $1}' | head -1)
kubectl describe pod $FAILED -n <namespace> | tail -40
kubectl logs $FAILED -n <namespace> --previous --tail=50

# ── RESOURCE PRESSURE (8-10 min) ─────────────────────────────
kubectl top nodes
kubectl top pods -n <namespace> --sort-by=memory

# ── EMERGENCY ROLLBACK ────────────────────────────────────────
kubectl rollout undo deployment/<app> -n <namespace>
kubectl rollout status deployment/<app> -n <namespace>
# OR git-based (preferred — see k8s-deploy skill):
# make rollback ENV=prod ROLLBACK_SHA=<last-known-good-sha>
```

---

## Tool reference

| Tool | When to use |
|------|-------------|
| `kubectl describe` | Detailed state + events for any resource |
| `kubectl logs --previous` | Logs from the last crashed container |
| `stern` | Multi-pod log tailing with regex and colour |
| `k9s` | Interactive TUI — fastest way to navigate pods/events |
| `netshoot` | Full-featured debug pod (curl, dig, nmap, tcpdump) |
| `hubble observe` | Cilium network flow monitoring (drop/allowed verdicts) |
| `cilium connectivity test` | Full end-to-end CNI validation |
| `cilium sysdump` | Diagnostic bundle for offline analysis |
| `istioctl analyze` | Detect Istio/Gateway misconfigurations |
| `kubectl debug` | Ephemeral debug container — safer than exec for prod |
| `kubectl run --rm -it` | Disposable debug pod for DNS/network tests |

---

## Exemplar scenarios

### Scenario A — Pod stuck in CrashLoopBackOff
```
1. kubectl describe pod <name> -n <ns>     → check Exit Code and Events
   - Exit 137 = OOMKilled → increase memory limit
   - Exit 1 = app error → check logs

2. kubectl logs <name> -n <ns> --previous  → read the crash message

3. kubectl get events -n <ns> --sort-by='.lastTimestamp'

4. If init container failing:
   kubectl logs <name> -n <ns> -c <init-container-name>
```

### Scenario B — Service unreachable
```
1. kubectl get endpoints <svc> -n <ns>
   → empty? readiness probe failing or label selector mismatch

2. kubectl get svc <svc> -n <ns> -o jsonpath='{.spec.selector}'
   kubectl get pods -n <ns> -l app=<label>

3. kubectl run net-test --image=busybox --restart=Never --rm -it \
     -- nc -zv <svc>.<ns>.svc.cluster.local <port>
   → connection refused = no healthy endpoint
   → timeout = NetworkPolicy blocking

4. hubble observe --from-pod <ns>/app --to-pod <ns>/db --follow
```

### Scenario C — StatefulSet not ready
```
1. kubectl get statefulset <name> -n <ns>   → check READY column

2. kubectl get pods -n <ns> -l app=<name> --sort-by=.metadata.name
   → pods must come ready in order: pod-0 before pod-1

3. kubectl describe pod <name>-0 -n <ns>
   → PVC binding? init container? probe failures?

4. kubectl get pvc -n <ns>                  → any Pending?

5. kubectl logs <name>-0 -n <ns>
   → database startup logs: auth errors, data directory issues
```

### Scenario D — Ingress returning 502/504
```
1. kubectl describe ingress <name> -n <ns>  → backend service + port correct?

2. kubectl get endpoints <backend-svc> -n <ns>
   → empty = no ready pods

3. kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=100
   → upstream connect errors

4. kubectl top pods -n <ns>
   → OOMKilled or CPU throttling → 504s
```

### Scenario E — PVC stuck in Pending
```
1. kubectl describe pvc <name> -n <ns>
   → "no persistent volumes available" / "storageclass not found"
   → "waiting for first consumer" (WaitForFirstConsumer binding mode)

2. kubectl get storageclass             → StorageClass defined?

3. kubectl get pods -n kube-system | grep provisioner
   → CSI/storage provisioner running?

4. If WaitForFirstConsumer: PVC only binds after a pod is scheduled
   → if pod is also Pending, fix the scheduling issue first
```

---

## Exemplars

<!-- Add exemplars here as you diagnose issues -->
