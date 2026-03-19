---
name: k8s-troubleshooting
description: Kubernetes cluster and workload diagnostics — architecture-first triage covering ingress/gateway/service topology, pod and container log scanning, storage health (PVC/PV/StorageClass), workload status (Deployment/StatefulSet/DaemonSet), database connectivity, and CNI/Cilium network layer validation.
triggers:
  - "pod is crashing"
  - "pod crashloop"
  - "pod not starting"
  - "pod pending"
  - "pod evicted"
  - "service not reachable"
  - "ingress not working"
  - "can't connect to database"
  - "database connection refused"
  - "pvc not bound"
  - "storage issue"
  - "network policy"
  - "cilium"
  - "troubleshoot kubernetes"
  - "troubleshoot k8s"
  - "k8s issue"
  - "deployment failing"
  - "statefulset not ready"
  - "daemonset not running"
  - "OOMKilled"
  - "imagepullbackoff"
  - "what's wrong with my pod"
  - "diagnose cluster"
  - "check cluster health"
---

# k8s-troubleshooting

Structured workflow for diagnosing Kubernetes workload and cluster issues — **architecture first, then drill down, then confirm root cause**.

The golden rule: always understand the data path before touching individual components. Traffic enters through an Ingress or Gateway → reaches a Service → is load-balanced to Pods → Pods connect to backends (databases, queues, other services). Understand that path before chasing symptoms.

**The goal is not just to fix the symptom — it is to identify and state the root cause before applying any fix.** A fix applied without a confirmed root cause is a guess. Guesses mask the real problem and cause recurrence.

### Top-down vs. bottom-up

**Top-down** (start from user impact, drill to root cause) — use for active production incidents:
```
User/Service Impact → DNS → Load Balancer → Ingress/Gateway → Service → Pod → App
```

**Bottom-up** (start from infrastructure, build up) — use for mass Pending pods, node failures, cluster upgrades:
```
Node/OS → kubelet/CRI → Container/Image → Pod Scheduling → Workload → Service → App
```

### The 7-layer traffic path

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

## Phase 0 — Orient: Confirm cluster context

Before any diagnosis, confirm you are in the right cluster and namespace.

```bash
# Confirm active cluster context
kubectl config current-context
kubectl config get-contexts

# This environment uses separate kubeconfig files per vcluster
# (see k8s-deploy skill for KUBECONFIG conventions)
echo $KUBECONFIG

# Get a broad picture of all namespaces
kubectl get namespaces

# Quick cluster-wide health snapshot
kubectl get nodes -o wide
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded | head -40
```

---

## Phase 1 — Architecture scan: map the data path

Always start here. Understand what resources exist and how they connect before looking at logs.

### 1a — Ingress and Gateways (traffic entry)

```bash
# List all Ingresses across namespaces
kubectl get ingress -A

# Describe a specific ingress — check rules, TLS, backend service references
kubectl describe ingress <name> -n <namespace>

# Check Ingress controller pods are healthy
kubectl get pods -n ingress-nginx          # nginx ingress
kubectl get pods -n istio-system           # istio gateway
kubectl get pods -n traefik                # traefik

# Gateway API (newer standard — GatewayClass, Gateway, HTTPRoute)
kubectl get gatewayclass
kubectl get gateway -A
kubectl get httproute -A
kubectl describe gateway <name> -n <namespace>

# Check ingress controller logs for 4xx/5xx
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=100

# NGINX Ingress — validate the generated nginx.conf for a host
kubectl exec -n ingress-nginx deployment/ingress-nginx-controller \
  -- nginx -T | grep -A 10 "server_name api.example.com"

# Check IngressClass binding (required K8s 1.28+)
kubectl get ingressclass
kubectl get ingress <name> -n <namespace> -o jsonpath='{.spec.ingressClassName}'

# Istio — check for misconfiguration (catches ~80% of issues)
istioctl analyze -n <namespace>
kubectl get gateway,virtualservice,destinationrule -n <namespace>
istioctl proxy-status                          # are all Envoy proxies in sync?
istioctl proxy-config route deploy/<name> -n <namespace>
```

### 1b — Services (internal routing)

```bash
# List all services — spot ClusterIP vs NodePort vs LoadBalancer
kubectl get svc -A

# Check a service's endpoint set — empty endpoints = no healthy pods
kubectl get endpoints <service-name> -n <namespace>
kubectl describe svc <service-name> -n <namespace>

# Verify selector labels match pod labels (common mismatch bug)
# Service selector:
kubectl get svc <service-name> -n <namespace> -o jsonpath='{.spec.selector}'
# Pods with matching labels:
kubectl get pods -n <namespace> -l app=<label-value>

# If using headless service (StatefulSet DNS):
# Each pod gets: <pod-name>.<svc-name>.<namespace>.svc.cluster.local
kubectl get svc <service-name> -n <namespace> -o jsonpath='{.spec.clusterIP}'
# clusterIP: None = headless
```

### 1c — Workload inventory

```bash
# Overview of all workload types in a namespace
kubectl get deploy,statefulset,daemonset,job,cronjob -n <namespace>

# Check rollout status
kubectl rollout status deployment/<name> -n <namespace>
kubectl rollout status statefulset/<name> -n <namespace>
kubectl rollout status daemonset/<name> -n <namespace>

# Deployment: desired vs ready vs up-to-date
kubectl get deploy -n <namespace> -o wide

# StatefulSet: ordered pod readiness
kubectl get statefulset -n <namespace>
kubectl get pods -n <namespace> -l app=<name> --sort-by=.metadata.name

# DaemonSet: check which nodes are missing the pod
kubectl get pods -n <namespace> -l <daemonset-label> -o wide
kubectl describe daemonset <name> -n <namespace>
```

---

## Phase 2 — Pod-level triage

### 2a — Pod status and events

```bash
# All pods with status — spot Pending, CrashLoopBackOff, OOMKilled, Evicted
kubectl get pods -n <namespace> -o wide

# Detailed view: events, probe failures, resource limits, last state
kubectl describe pod <pod-name> -n <namespace>

# Key sections in describe output to read:
#   Conditions:    Ready / ContainersReady / PodScheduled / Initialized
#   Events:        Scheduling failures, probe failures, OOMKill, image pull errors
#   Last State:    Exit code from previous crash (137 = OOMKilled, 1 = app error)
#   Limits:        Are memory/CPU limits set?

# Cluster-wide events sorted by time — first signal of what's breaking
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -30
kubectl get events -A --sort-by='.lastTimestamp' | grep -v Normal | tail -30
```

### 2b — Common pod failure patterns

| Status | Exit Code | Cause | First action |
|--------|-----------|-------|--------------|
| `CrashLoopBackOff` | 1 | App startup error | `kubectl logs --previous` |
| `CrashLoopBackOff` | 137 | OOMKilled | Increase `limits.memory` or fix leak |
| `CrashLoopBackOff` | 143 | SIGTERM not handled | Check graceful shutdown |
| `Pending` | — | No schedulable node | `describe pod` → check Events |
| `Pending` | — | PVC not bound | `kubectl get pvc` |
| `Pending` | — | Image pull failure | `ImagePullBackOff` event, check registry |
| `Evicted` | — | Node memory/disk pressure | `kubectl describe node` → Conditions |
| `Init:CrashLoopBackOff` | — | Init container failing | `kubectl logs <pod> -c <init-container>` |
| `0/1 Endpoints` | — | Readiness probe failing | Check probe config + app health endpoint |

### 2c — Log scanning

```bash
# Current logs
kubectl logs <pod-name> -n <namespace>

# Previous container (after crash)
kubectl logs <pod-name> -n <namespace> --previous

# Multi-container pod — specify container
kubectl logs <pod-name> -n <namespace> -c <container-name>

# Stream logs from all pods matching a label (production incident pattern)
kubectl logs -n <namespace> -l app=<name> --tail=100 --follow

# Last N lines from all replicas simultaneously
kubectl logs -n <namespace> -l app=<name> --tail=50 --prefix=true

# Using stern for multi-pod, colour-coded tailing (preferred for incidents)
stern <pod-name-regex> -n <namespace> --since 15m
stern . -n <namespace> --since 5m            # all pods in namespace
stern <name> -A --since 5m                   # across all namespaces

# Filter for errors across all pods in namespace
kubectl logs -n <namespace> -l app=<name> --tail=500 | grep -iE "error|fatal|panic|exception"
```

---

## Phase 3 — Storage diagnostics

Storage issues silently cause StatefulSets and databases to fail. Check this early when pods are Pending or stuck.

```bash
# PVC status — Bound/Pending/Lost
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc-name> -n <namespace>

# PV status and binding
kubectl get pv
kubectl describe pv <pv-name>

# StorageClass — check provisioner is available
kubectl get storageclass
kubectl describe storageclass <name>

# Check provisioner pod is healthy (varies by provider)
kubectl get pods -n kube-system | grep -i provisioner
kubectl get pods -n storage-system          # Rook/Ceph
kubectl get pods -n longhorn-system         # Longhorn
kubectl get pods -n openebs                 # OpenEBS

# Common PVC issues:
# 1. Pending → no matching PV or StorageClass misconfiguration
kubectl describe pvc <name> -n <namespace>  # look for "no persistent volumes available"

# 2. Lost → underlying PV deleted while PVC was bound
# Fix: delete PVC and recreate (data may be lost), or restore PV

# 3. RWX needed but StorageClass only supports RWO
kubectl get pvc <name> -n <namespace> -o jsonpath='{.spec.accessModes}'

# Storage usage inside a pod
kubectl exec -it <pod-name> -n <namespace> -- df -h
kubectl exec -it <pod-name> -n <namespace> -- du -sh /data/*
```

---

## Phase 4 — Database and backend connectivity

### 4a — DNS resolution

```bash
# Test DNS from within the cluster (using a debug pod)
kubectl run dns-test --image=busybox:1.36 --restart=Never --rm -it \
  -- nslookup <service-name>.<namespace>.svc.cluster.local

# Test from within an existing pod
kubectl exec -it <app-pod> -n <namespace> -- \
  nslookup postgres.production.svc.cluster.local

# Check CoreDNS is healthy
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50

# Service DNS format:
# <service>.<namespace>.svc.cluster.local:<port>
# StatefulSet pod DNS (headless): <pod-name>.<svc>.<namespace>.svc.cluster.local
```

### 4b — Port connectivity

```bash
# Test TCP connectivity to a service from within the cluster
kubectl run net-test --image=busybox:1.36 --restart=Never --rm -it \
  -- nc -zv <service-name>.<namespace>.svc.cluster.local 5432

# Test from an existing pod
kubectl exec -it <app-pod> -n <namespace> -- \
  nc -zv postgres.production.svc.cluster.local 5432

# Netshoot — swiss-army-knife debug pod (curl, dig, nmap, tcpdump, iperf3)
kubectl run netshoot --image=nicolaka/netshoot --restart=Never --rm -it \
  -- /bin/bash
# Inside netshoot:
#   curl -v http://my-service.production.svc.cluster.local:8080
#   dig my-service.production.svc.cluster.local
#   nmap -p 5432 postgres.production.svc.cluster.local
#   tcpdump -i eth0 port 5432

# Port-forward for bypass testing (skips ingress/service entirely)
kubectl port-forward svc/<service> 8080:80 -n <namespace>
# then: curl http://localhost:8080

# Check if endpoints are populated (no endpoints = readiness probe failing)
kubectl get endpoints <service-name> -n <namespace>

# Diagnose environment variables (wrong DB_HOST or PORT)
kubectl exec -it <pod-name> -n <namespace> -- env | grep -iE "db|database|pg|mysql|redis|mongo"
```

### 4c — Database-specific checks

```bash
# PostgreSQL readiness from inside the pod
kubectl exec -it <db-pod> -n <namespace> -- pg_isready -U postgres

# PostgreSQL connection test from app pod
kubectl exec -it <app-pod> -n <namespace> -- \
  psql -h postgres.<namespace>.svc.cluster.local -U myuser -d mydb -c "SELECT 1"

# MySQL/MariaDB
kubectl exec -it <db-pod> -n <namespace> -- \
  mysqladmin ping -h 127.0.0.1 -u root -p

# Redis
kubectl exec -it <redis-pod> -n <namespace> -- redis-cli ping

# StatefulSet pod ordering — pods must come up in order (0, 1, 2...)
kubectl get pods -n <namespace> -l app=postgres --sort-by=.metadata.name
# If postgres-1 is pending, postgres-0 may not be Ready yet
```

---

## Phase 5 — Network and CNI (Cilium)

Network issues are often silent — the pod is Running but traffic is silently dropped.

### 5a — Cilium health

```bash
# Overall Cilium status (run from any Cilium pod)
kubectl exec -n kube-system ds/cilium -- cilium status

# Full connectivity test suite
cilium connectivity test

# Check Cilium pods are all Running on every node
kubectl get pods -n kube-system -l k8s-app=cilium -o wide

# Cilium version
kubectl exec -n kube-system ds/cilium -- cilium version

# Check Cilium operator
kubectl get pods -n kube-system -l name=cilium-operator
kubectl logs -n kube-system -l name=cilium-operator --tail=50
```

### 5b — Endpoint and identity inspection

```bash
# List all Cilium endpoints (one per pod) — check state is "ready"
kubectl exec -n kube-system ds/cilium -- cilium endpoint list

# Get endpoint detail for a specific pod IP
kubectl exec -n kube-system ds/cilium -- cilium endpoint get <endpoint-id>

# Check Cilium identity for a pod
kubectl exec -n kube-system ds/cilium -- cilium identity list | grep <namespace>

# Verify policy verdicts for a specific traffic path
kubectl exec -n kube-system ds/cilium -- \
  cilium policy trace \
    --src-k8s-pod <namespace>/< source-pod> \
    --dst-k8s-pod <namespace>/<dest-pod> \
    --dport <port>/TCP \
    --verbose
```

### 5c — Flow monitoring with Hubble

```bash
# Check Hubble status
hubble status
cilium hubble enable --ui   # enable if not already on

# Observe all flows in real time
hubble observe --follow

# Find dropped packets — most useful for NetworkPolicy debugging
hubble observe --verdict DROPPED --follow

# Filter by pod pair
hubble observe \
  --from-pod <namespace>/frontend \
  --to-pod <namespace>/backend \
  --follow

# Show only policy-denied drops (NetworkPolicy blocking traffic)
hubble observe \
  --verdict DROPPED \
  --reason POLICY_DENIED \
  --follow

# Observe flows for a namespace
hubble observe --namespace <namespace> --follow

# Port-forward Hubble relay for CLI access
kubectl port-forward -n kube-system svc/hubble-relay 4245:443
```

### 5d — NetworkPolicy audit

```bash
# List all NetworkPolicies
kubectl get networkpolicy -A

# Describe a policy — check ingress/egress selectors
kubectl describe networkpolicy <name> -n <namespace>

# Cilium-specific network policies
kubectl get ciliumnetworkpolicy -A          # cnp
kubectl get ciliumclusterwidenetworkpolicy  # ccnp

# Check which policies apply to a pod by its labels
kubectl get networkpolicy -n <namespace> -o json | \
  jq '.items[] | select(.spec.podSelector.matchLabels.app == "<label>")'

# Common NetworkPolicy trap: blocking DNS (port 53)
# Always ensure egress allows UDP/53 to kube-dns namespace
```

### 5e — BPF and service maps

```bash
# Check Cilium's service load-balancer map
kubectl exec -n kube-system ds/cilium -- cilium service list
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list

# Check connection tracking table
kubectl exec -n kube-system ds/cilium -- cilium bpf ct list global | head -30

# Check NAT table
kubectl exec -n kube-system ds/cilium -- cilium bpf nat list | head -30

# Monitor packet drops in real time
kubectl exec -n kube-system ds/cilium -- cilium monitor --type drop

# Monitor policy verdicts
kubectl exec -n kube-system ds/cilium -- cilium monitor --type policy-verdict
```

### 5f — Collect Cilium diagnostic bundle

```bash
# Full diagnostic sysdump (file for sharing with Cilium team or for post-mortem)
cilium sysdump --output-filename cilium-debug-$(date +%Y%m%d-%H%M)

# Quick sysdump
cilium sysdump --quick
```

---

## Phase 6 — Resource pressure and scheduling

```bash
# Node resource usage
kubectl top nodes
kubectl describe node <node-name> | grep -A 10 "Allocated resources"

# Pod resource usage — spot OOM candidates
kubectl top pods -n <namespace> --sort-by=memory

# Check node conditions (MemoryPressure, DiskPressure, PIDPressure)
kubectl get nodes -o custom-columns=\
  NAME:.metadata.name,\
  STATUS:.status.conditions[-1].type,\
  READY:.status.conditions[-1].status

kubectl describe node <node-name> | grep -A 5 "Conditions:"

# Check resource quotas in a namespace
kubectl describe resourcequota -n <namespace>
kubectl describe limitrange -n <namespace>

# Why is this pod Pending? (taint/affinity/resource reasons)
kubectl describe pod <pod-name> -n <namespace> | grep -A 20 "Events:"

# Which pods are on which nodes
kubectl get pods -n <namespace> -o wide

# Are any nodes under memory/disk pressure?
kubectl get nodes -o json | \
  jq '.items[] | {name: .metadata.name, conditions: .status.conditions[] | select(.type != "Ready")}'
```

---

## Exemplar Scenarios

### Scenario A — Pod stuck in CrashLoopBackOff

```
1. kubectl describe pod <name> -n <ns>         → check Exit Code and Events
   - Exit 137 = OOMKilled → increase memory limit
   - Exit 1 = app error → check logs

2. kubectl logs <name> -n <ns> --previous       → read the crash message

3. kubectl get events -n <ns> --sort-by='.lastTimestamp'
   → look for OOMKilled, BackOff, Unhealthy

4. If init container failing:
   kubectl logs <name> -n <ns> -c <init-container-name>
```

### Scenario B — Service unreachable / connection refused

```
1. kubectl get endpoints <svc> -n <ns>
   → empty? readiness probe failing or label selector mismatch

2. kubectl get svc <svc> -n <ns> -o jsonpath='{.spec.selector}'
   kubectl get pods -n <ns> -l app=<label>
   → verify labels match

3. kubectl run net-test --image=busybox --restart=Never --rm -it \
     -- nc -zv <svc>.<ns>.svc.cluster.local <port>
   → connection refused = no healthy endpoint
   → timeout = NetworkPolicy blocking

4. hubble observe --from-pod <ns>/app --to-pod <ns>/db --follow
   → look for DROPPED / POLICY_DENIED

5. kubectl get networkpolicy -n <ns>
   → check if egress/ingress rules allow the path
```

### Scenario C — Database (StatefulSet) not ready

```
1. kubectl get statefulset <name> -n <ns>
   → check READY column (e.g. 0/3)

2. kubectl get pods -n <ns> -l app=<name> --sort-by=.metadata.name
   → pods must come ready in order: pod-0 must be Ready before pod-1 starts

3. kubectl describe pod <name>-0 -n <ns>
   → check Events: PVC binding, init container failures, probe failures

4. kubectl get pvc -n <ns>
   → any Pending PVCs? → kubectl describe pvc <name>

5. kubectl logs <name>-0 -n <ns>
   → read database startup logs for auth errors, data directory issues

6. kubectl exec -it <name>-0 -n <ns> -- pg_isready -U postgres
   → is the DB process alive inside the pod?
```

### Scenario D — Ingress returning 502/504

```
1. kubectl describe ingress <name> -n <ns>
   → check backend service name and port are correct

2. kubectl get endpoints <backend-svc> -n <ns>
   → empty = no ready pods behind the service

3. kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=100
   → look for upstream connect errors

4. kubectl logs -n <ns> -l app=<backend> --tail=100
   → is the backend app logging errors?

5. kubectl top pods -n <ns>
   → OOMKilled or CPU throttling causing slow responses → 504s
```

### Scenario E — Network policy blocking traffic (Cilium)

```
1. hubble observe --verdict DROPPED --follow
   → look for drops between the affected pods

2. kubectl exec -n kube-system ds/cilium -- \
     cilium policy trace \
       --src-k8s-pod <ns>/frontend \
       --dst-k8s-pod <ns>/backend \
       --dport 8080/TCP --verbose
   → "DENIED" = policy rule is blocking

3. kubectl get networkpolicy -A
   kubectl get ciliumnetworkpolicy -A
   → find the policy applying to the destination pod

4. Check for missing DNS egress (port 53 blocked):
   hubble observe --from-pod <ns>/pod --to-port 53 --follow
   → DNS drops cause cascading failures

5. Fix: update NetworkPolicy to allow the required port/namespace selector
```

### Scenario F — PVC stuck in Pending

```
1. kubectl describe pvc <name> -n <ns>
   → look for: "no persistent volumes available", "storageclass not found",
     "waiting for first consumer" (WaitForFirstConsumer binding mode)

2. kubectl get storageclass
   → is the requested StorageClass defined?

3. kubectl get pods -n kube-system | grep provisioner
   → is the CSI/storage provisioner running?

4. kubectl get events -n <ns> --sort-by='.lastTimestamp' | grep pvc
   → provisioner error messages

5. If WaitForFirstConsumer: PVC binds only after a pod is scheduled
   → if the pod is also Pending, fix scheduling issue first
```

---

## Root-cause identification

**Do not apply a fix until you can state the root cause in one sentence.**

The format: _"The root cause is [specific thing] because [evidence], not [ruled-out alternative]."_

Examples:
- ✅ "The root cause is a label selector mismatch on the `api` Service — the Service selects `app=api` but pods are labelled `app=api-v2`, confirmed by empty Endpoints object."
- ✅ "The root cause is OOMKilled due to a memory leak in the request handler, not an undersized limit — memory grew linearly over 4h and the limit was set to 2× historical peak."
- ❌ "The pod is crashing." (symptom, not cause)
- ❌ "Something is wrong with the network." (too vague)

### Root-cause checklist — before fixing

- [ ] **Evidence confirmed:** I have a specific command output, log line, or metric that directly shows the cause — not just a plausible theory.
- [ ] **Alternatives ruled out:** I have eliminated the two most likely alternative causes.
- [ ] **Blast radius known:** I know whether this is isolated to one pod/service or affects multiple.
- [ ] **Recurrence risk assessed:** I know whether fixing the symptom prevents recurrence or just masks it.
- [ ] **One-sentence root cause written:** stated above before applying any fix.

### Common root-cause traps

| Symptom | Common wrong hypothesis | Actual cause (check this) |
|---------|------------------------|---------------------------|
| Pod `CrashLoopBackOff` | "App is broken" | Exit code — 137=OOM, 1=app error, 143=unhandled SIGTERM |
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

# Pods with no resource requests set (scheduling risk)
kubectl get pods -A -o json | \
  jq -r '.items[] | select(.spec.containers[].resources.requests == null) | .metadata.name'

# Which services have no endpoints (broken selectors)
kubectl get endpoints -A | awk '$3 == "<none>" {print $1, $2}'

# Nodes with pressure conditions
kubectl get nodes -o json | \
  jq -r '.items[] | .metadata.name as $n |
    .status.conditions[] |
    select(.type != "Ready" and .status == "True") |
    [$n, .type, .message] | @tsv'

# ConfigMaps and Secrets referenced by a deployment (check they exist)
kubectl get deploy <name> -n <ns> -o json | \
  jq '[.spec.template.spec.containers[].envFrom[].configMapRef.name,
       .spec.template.spec.containers[].envFrom[].secretRef.name] | .[]' -r
```

---

## Tool reference

| Tool | When to use |
|------|-------------|
| `kubectl describe` | Detailed state + events for any resource |
| `kubectl logs --previous` | Logs from the last crashed container |
| `stern` | Multi-pod log tailing with regex and colour |
| `k9s` | Interactive TUI — fastest way to navigate pods/events in real time |
| `kubens` | Fast namespace switching |
| `netshoot` | Full-featured debug pod (curl, dig, nmap, tcpdump) |
| `hubble observe` | Cilium network flow monitoring (drop/allowed verdicts) |
| `cilium connectivity test` | Full end-to-end CNI validation |
| `cilium sysdump` | Diagnostic bundle for offline analysis or filing issues |
| `istioctl analyze` | Detect Istio/Gateway misconfigurations before tracing packets |
| `kubectl debug` | Ephemeral debug container — safer than exec for prod |
| `kubectl run --rm -it` | Disposable debug pod for DNS/network tests |

---

## Event-driven debugging

Kubernetes events are **short-lived (default 1-hour TTL)** but contain the most actionable real-time diagnostic information. Read them before logs.

```bash
# All Warning events, all namespaces, sorted by time
kubectl get events -A \
  --field-selector type=Warning \
  --sort-by='.lastTimestamp' | tail -30

# Target-specific events (K8s 1.23+ modern syntax)
kubectl events --for pod/<pod-name> -n <namespace>
kubectl events --for deployment/<name> -n <namespace>
kubectl events --types=Warning --watch -n <namespace>

# Storage-related event filter
kubectl get events -A --sort-by='.lastTimestamp' \
  | grep -iE "volume|pvc|pv|mount|attach"

# Scheduling failure events
kubectl get events -A --field-selector reason=FailedScheduling

# Count by reason — find the top recurring failure type
kubectl get events -n <namespace> -o json | jq '
  [.items[] | select(.type=="Warning")]
  | group_by(.reason)
  | map({reason: .[0].reason, count: length})
  | sort_by(.count) | reverse'
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
| `Pulling` / `Failed` | Pod | Image pull status / failure |

---

## 10-minute incident runbook

```bash
# ── PHASE 1: TRIAGE (0-2 min) ────────────────────────────────
kubectl get nodes -o wide | grep -v " Ready"
kubectl get pods -n <namespace> | grep -v Running
kubectl get events -n <namespace> --field-selector type=Warning \
  --sort-by='.lastTimestamp' | tail -15

# Check for recent rollout that may have caused the regression
kubectl rollout history deployment/<app> -n <namespace>

# ── PHASE 2: ARCHITECTURE CHECK (2-4 min) ────────────────────
kubectl get endpoints -n <namespace>              # empty = label mismatch
kubectl get ingress -n <namespace>
kubectl get pvc -n <namespace> | grep -v Bound    # storage issue?

# ── PHASE 3: DEEP DIVE (4-8 min) ─────────────────────────────
# Grab the first failing pod and read its events + previous logs
FAILED=$(kubectl get pods -n <namespace> | grep -vE "Running|NAME|Completed" | awk '{print $1}' | head -1)
kubectl describe pod $FAILED -n <namespace> | tail -40
kubectl logs $FAILED -n <namespace> --previous --tail=50

# ── PHASE 4: RESOURCE PRESSURE (8-10 min) ────────────────────
kubectl top nodes
kubectl top pods -n <namespace> --sort-by=memory

# ── EMERGENCY ROLLBACK ────────────────────────────────────────
kubectl rollout undo deployment/<app> -n <namespace>
kubectl rollout status deployment/<app> -n <namespace>
# OR git-based rollback (preferred — see k8s-deploy skill):
# make rollback ENV=prod ROLLBACK_SHA=<last-known-good-sha>
```

---

## Updating This Skill with Exemplars

When you diagnose an issue, add the pattern here:

```markdown
### Exemplar: <brief description> (<date>)
- **Symptom**: what the user/alert reported
- **Resource**: Deployment/StatefulSet/Service/...
- **Signal found**: `<command>` → `<key output>`
- **Alternatives ruled out**: what else was checked and eliminated
- **Root cause**: one sentence — "[specific thing] because [evidence], not [ruled-out alternative]"
- **Fix**: what was changed
- **Recurrence prevention**: what would prevent this happening again
```
