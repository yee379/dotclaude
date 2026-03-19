---
name: k8s-deploy
description: Kubernetes deployment patterns, Helm charts, Makefile-driven workflows, vcluster (loft.sh) virtual clusters, namespace-based environment promotion (test to production), rollback strategies, resource tuning, health probes, and production readiness for containerised backend and DevOps workloads.
license: MIT
compatibility: opencode
---

# Kubernetes Deploy

End-to-end guidance for deploying and operating services on Kubernetes — from manifest authoring through environment promotion to production rollback.

**This environment uses [vcluster (loft.sh)](https://www.vcluster.com) virtual clusters and Makefile-driven deployment workflows.** Manifests are rendered from Helm + values files and committed to git as the source of truth. Direct `helm upgrade` is not the deploy mechanism — Make targets are. See [vcluster](#vcluster-loftsh) and [Makefile Workflow](#makefile-driven-deployment-workflow) sections.

## When to Use

- Writing or reviewing Deployment, Service, Ingress, ConfigMap, or Secret manifests
- Structuring Helm charts for multi-environment promotion
- Rendering Helm templates to committed manifest files (`helm template`)
- Writing or reviewing Makefile deploy targets
- Working with vcluster virtual clusters (creating, connecting, scoping)
- Planning a test → staging → production promotion workflow
- Debugging pod scheduling, crashloops, or OOMKills
- Tuning resource requests/limits and HPA settings
- Setting up liveness, readiness, and startup probes
- Preparing a rollback plan before a release

---

## vcluster (loft.sh)

[vcluster](https://www.vcluster.com) runs a fully functional virtual Kubernetes control plane inside a namespace of a host cluster. Each vcluster gets its own API server, scheduler, and etcd — so it behaves like a real cluster while sharing the host's nodes and network infrastructure.

### Mental model

```
Host cluster (physical nodes)
└── Namespace: vclusters
    ├── vcluster: dev        (virtual cluster — dev workloads)
    ├── vcluster: staging    (virtual cluster — staging workloads)
    └── vcluster: prod       (virtual cluster — production workloads)
```

- **Inside a vcluster:** standard `kubectl`, `helm`, `make deploy` — looks and feels like a real cluster.
- **From the host:** vclusters appear as StatefulSets + Services in their host namespace. Host nodes are shared.
- **Isolation:** each vcluster has its own namespaces, RBAC, and resource quotas, fully isolated from other vclusters.
- **Syncing:** by default, Pods created inside a vcluster are synced down to the host cluster as real Pods. Services, Ingresses, and PVCs can also be synced (configured in `vcluster.yaml`).

### CLI quickstart

```bash
# Install the CLI (macOS)
brew install loft-sh/tap/vcluster

# Create a vcluster in a host namespace
vcluster create prod --namespace vclusters-prod

# Connect — switches kubeconfig context to the vcluster
vcluster connect prod --namespace vclusters-prod

# Run a single command inside the vcluster without switching context
vcluster connect prod --namespace vclusters-prod -- kubectl get pods -A

# List all vclusters (across all host namespaces)
vcluster list

# Disconnect (restores previous kubeconfig context)
vcluster disconnect

# Pause a vcluster (scales control plane to 0 — saves cost in non-prod)
vcluster pause dev --namespace vclusters-dev

# Resume
vcluster resume dev --namespace vclusters-dev

# Delete
vcluster delete dev --namespace vclusters-dev
```

### vcluster.yaml — configuration

The `vcluster.yaml` config file controls the virtual cluster's behaviour (v0.20+ unified format):

```yaml
# vcluster.yaml
controlPlane:
  distro:
    k8s:
      enabled: true          # use upstream Kubernetes (default)
  statefulSet:
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: 1000m
        memory: 1Gi

sync:
  toHost:
    ingresses:
      enabled: true          # sync Ingress objects to host cluster
    persistentVolumeClaims:
      enabled: true
    services:
      enabled: true

# Resource quotas scoped to this vcluster's workloads
policies:
  resourceQuota:
    enabled: true
    quota:
      requests.cpu: "4"
      requests.memory: 8Gi
      limits.cpu: "8"
      limits.memory: 16Gi
      count/pods: "50"
```

Deploy or update a vcluster using its config:

```bash
vcluster create prod \
  --namespace vclusters-prod \
  --values ./infra/vclusters/prod/vcluster.yaml \
  --upgrade    # upgrade if it already exists
```

### vcluster in the Makefile workflow

Since we use Makefiles for deployments, wrap vcluster operations as Make targets too:

```makefile
# Connect to a named vcluster and export the kubeconfig
.PHONY: vcluster-connect
vcluster-connect:
	vcluster connect $(VCLUSTER_NAME) --namespace $(VCLUSTER_NAMESPACE) \
	  --kube-config-context-name $(VCLUSTER_CONTEXT)

# Apply all rendered manifests into the currently connected vcluster
.PHONY: deploy
deploy: render
	kubectl apply -f deploy/$(ENV)/manifests/ --context $(VCLUSTER_CONTEXT)
```

### Namespace layout inside a vcluster

Even inside a vcluster, use namespaces per service or tier — vcluster namespaces are fully independent of the host:

```bash
# Inside the vcluster (after vcluster connect ...)
kubectl create namespace api
kubectl create namespace workers
kubectl create namespace monitoring
```

---

## Makefile-Driven Deployment Workflow

We **do not run `helm upgrade` directly** as the deploy step. Instead:

1. **`helm template`** renders chart + values into plain YAML manifests
2. The rendered manifests are **committed to git** as the canonical state
3. **`kubectl apply`** (via Make targets) applies those committed manifests

This gives a complete, auditable, diff-able history of exactly what was deployed — no state hidden inside Helm's release secret.

### Repository layout

```
charts/api/                    # Helm chart source
├── Chart.yaml
├── values.yaml                # base defaults
├── values-dev.yaml
├── values-staging.yaml
└── values-prod.yaml

deploy/                        # rendered manifests — committed to git
├── dev/
│   └── manifests/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── ...
├── staging/
│   └── manifests/
└── prod/
    └── manifests/

Makefile
```

### Makefile patterns

```makefile
# ---- configuration -----------------------------------------------
CHART        := ./charts/api
ENV          ?= dev                          # override: make deploy ENV=prod
IMAGE_TAG    ?= $(shell git rev-parse --short HEAD)

VCLUSTER_NAME      := api-$(ENV)
VCLUSTER_NAMESPACE := vclusters-$(ENV)
VCLUSTER_CONTEXT   := vcluster_$(VCLUSTER_NAME)_$(VCLUSTER_NAMESPACE)

MANIFESTS_DIR := ./deploy/$(ENV)/manifests

# ---- render -------------------------------------------------------
# Render Helm chart to plain YAML and commit — this is the source of truth.
.PHONY: render
render:
	@echo "Rendering $(ENV) manifests (image: $(IMAGE_TAG))..."
	mkdir -p $(MANIFESTS_DIR)
	helm template api $(CHART) \
	  -f $(CHART)/values.yaml \
	  -f $(CHART)/values-$(ENV).yaml \
	  --set image.tag=$(IMAGE_TAG) \
	  --namespace api \
	  > $(MANIFESTS_DIR)/all.yaml
	@echo "Rendered → $(MANIFESTS_DIR)/all.yaml"

# Split multi-doc YAML into individual files (optional, aids readability)
.PHONY: render-split
render-split:
	mkdir -p $(MANIFESTS_DIR)
	helm template api $(CHART) \
	  -f $(CHART)/values.yaml \
	  -f $(CHART)/values-$(ENV).yaml \
	  --set image.tag=$(IMAGE_TAG) \
	  --namespace api \
	  --output-dir $(MANIFESTS_DIR)

# ---- diff ---------------------------------------------------------
# Show what would change before applying (requires kubectl-diff or helm-diff).
.PHONY: diff
diff:
	kubectl diff -f $(MANIFESTS_DIR)/ --context $(VCLUSTER_CONTEXT) || true

# ---- deploy -------------------------------------------------------
# Apply committed manifests to the vcluster. render MUST be run first.
.PHONY: deploy
deploy:
	@echo "Deploying $(ENV) from $(MANIFESTS_DIR)..."
	kubectl apply -f $(MANIFESTS_DIR)/ \
	  --context $(VCLUSTER_CONTEXT) \
	  --namespace api
	kubectl rollout status deployment/api \
	  --context $(VCLUSTER_CONTEXT) \
	  --namespace api \
	  --timeout 5m

# ---- render + commit + deploy (full pipeline) --------------------
.PHONY: release
release: render
	git add $(MANIFESTS_DIR)/
	git diff --cached --quiet || git commit -m "deploy($(ENV)): render manifests for $(IMAGE_TAG)"
	$(MAKE) deploy

# ---- rollback (git-based) ----------------------------------------
# Roll back to any previously committed manifest state.
.PHONY: rollback
rollback:
	@echo "Rolling back $(ENV) to $(ROLLBACK_SHA)..."
	git show $(ROLLBACK_SHA):$(MANIFESTS_DIR)/all.yaml | \
	  kubectl apply -f - --context $(VCLUSTER_CONTEXT) --namespace api
	kubectl rollout status deployment/api \
	  --context $(VCLUSTER_CONTEXT) --namespace api --timeout 5m

# ---- connect to vcluster -----------------------------------------
.PHONY: connect
connect:
	vcluster connect $(VCLUSTER_NAME) \
	  --namespace $(VCLUSTER_NAMESPACE) \
	  --kube-config-context-name $(VCLUSTER_CONTEXT)

# ---- helpers ------------------------------------------------------
.PHONY: pods logs
pods:
	kubectl get pods -n api --context $(VCLUSTER_CONTEXT)
logs:
	kubectl logs -n api -l app=api --tail=100 --follow --context $(VCLUSTER_CONTEXT)
```

### Workflow in practice

```bash
# 1. Make code changes, build & push image
make build push IMAGE_TAG=v1.4.2

# 2. Render manifests for your environment
make render ENV=staging IMAGE_TAG=v1.4.2

# 3. Review the diff before applying
make diff ENV=staging

# 4. Commit the rendered manifests and deploy
make release ENV=staging IMAGE_TAG=v1.4.2

# 5. Promote to prod (same steps, different ENV)
make render ENV=prod IMAGE_TAG=v1.4.2
make diff ENV=prod
make release ENV=prod IMAGE_TAG=v1.4.2
```

### Why helm template + git, not helm upgrade

| Concern | `helm upgrade` | `helm template` + git + `kubectl apply` |
|---|---|---|
| Audit trail | Stored in cluster Secret (opaque) | Full diff in git history |
| Rollback | `helm rollback` (cluster state) | `git show <sha> \| kubectl apply` |
| Review | `helm diff` plugin required | Plain `git diff` on YAML |
| Offline replay | Requires live cluster + Helm | Any `kubectl` with the git tree |
| Secrets leaking | Values end up in release Secret | Secrets are never in the manifests |

### When to use helm directly (exceptions)

- **`helm template`** — always, for rendering
- **`helm diff`** — optional, useful for a pre-render sanity check
- **`helm install` / `helm upgrade`** — only for third-party charts you don't own (e.g., cert-manager, ingress-nginx, monitoring stack) where you don't maintain the chart source

---

## Environment Promotion Workflow

```
feature branch
     │
     ▼
[CI: build + test]
     │  passes
     ▼
make render ENV=dev + make release ENV=dev
     │  smoke tests pass (inside dev vcluster)
     ▼
make render ENV=staging + make release ENV=staging
     │  integration tests pass (inside staging vcluster)
     ▼
[PR approved + merged to main]
     │
     ▼
make render ENV=prod + make release ENV=prod
     │  health check passes ──► ✗ make rollback ENV=prod ROLLBACK_SHA=<prev>
```

### vcluster-per-environment isolation

```bash
# Each environment is a separate vcluster — never share
vcluster list
# NAME           NAMESPACE         STATUS
# api-dev        vclusters-dev     Running
# api-staging    vclusters-staging Running
# api-prod       vclusters-prod    Running

# Connect to the target environment before running kubectl commands
make connect ENV=staging
kubectl get namespaces    # inside the staging vcluster
```

---

### Deployment (production-ready baseline)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: prod
  labels:
    app: api
    version: "1.2.3"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0          # zero-downtime
  template:
    metadata:
      labels:
        app: api
        version: "1.2.3"
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: api
          image: ghcr.io/org/api:1.2.3   # always pin digest or semver, never :latest
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: api-config
            - secretRef:
                name: api-secrets
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 2
          startupProbe:
            httpGet:
              path: /healthz
              port: 8080
            periodSeconds: 5
            failureThreshold: 30    # 150 s max startup
          lifecycle:
            preStop:
              exec:
                command: ["sleep", "5"]  # drain in-flight requests
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: api
                topologyKey: kubernetes.io/hostname
```

### Service + Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: prod
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api
  namespace: prod
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 80
```

### HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
  namespace: prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
```

### PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api
  namespace: prod
spec:
  minAvailable: 2       # keep at least 2 pods alive during node drain
  selector:
    matchLabels:
      app: api
```

---

## Secrets Management

**Never commit secret values to git.**

```yaml
# Reference secrets from an external store
# Option A: Kubernetes Secrets (base64 encoded, use RBAC + encryption at rest)
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
  namespace: prod
type: Opaque
stringData:          # plain text — kubectl encodes automatically
  DATABASE_URL: "$(DATABASE_URL)"    # inject from CI/CD pipeline

# Option B: External Secrets Operator (preferred for production)
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
  namespace: prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager     # or vault, gcp-sm, azure-kv
    kind: ClusterSecretStore
  target:
    name: api-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: prod/api/database-url
```

---

## Helm Chart Structure

```
charts/api/
├── Chart.yaml
├── values.yaml              # defaults (non-sensitive)
├── values-test.yaml         # test overrides
├── values-staging.yaml      # staging overrides
├── values-prod.yaml         # prod overrides (replica count, resources)
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── hpa.yaml
    ├── pdb.yaml
    ├── configmap.yaml
    └── _helpers.tpl
```

```yaml
# values.yaml (defaults)
image:
  repository: ghcr.io/org/api
  tag: latest          # overridden in CI with actual SHA
  pullPolicy: IfNotPresent

replicaCount: 1

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10

ingress:
  enabled: false
  host: ""
  tls: false

env: {}            # key: value map injected as ConfigMap

---
# values-prod.yaml
replicaCount: 3

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20

ingress:
  enabled: true
  host: api.example.com
  tls: true

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Helm deploy commands (reference only)

> **Note:** We use `make render` + `make deploy` instead of running Helm directly. See [Makefile-Driven Deployment Workflow](#makefile-driven-deployment-workflow) above. The commands below are for reference or for managing third-party charts you don't own.

```bash
# Render only (what we actually use in CI — output goes to git)
helm template api ./charts/api \
  -f ./charts/api/values.yaml \
  -f ./charts/api/values-prod.yaml \
  --set image.tag=$IMAGE_TAG \
  --namespace api \
  > ./deploy/prod/manifests/all.yaml

# Diff before applying (useful sanity check)
helm diff upgrade api ./charts/api \
  -f ./charts/api/values-prod.yaml \
  --set image.tag=$IMAGE_TAG

# Direct upgrade (third-party charts only — e.g. cert-manager, ingress-nginx)
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --atomic --timeout 5m --wait
```

---

## Rollback

### Preferred: git-based rollback

Since manifests are committed to git, rolling back means applying a previous commit's manifests:

```bash
# Find the commit with the last known-good manifests
git log --oneline deploy/prod/manifests/

# Roll back to a specific commit
make rollback ENV=prod ROLLBACK_SHA=<commit-sha>

# Or manually:
git show <commit-sha>:deploy/prod/manifests/all.yaml \
  | kubectl apply -f - --context vcluster_api-prod_vclusters-prod --namespace api

kubectl rollout status deployment/api --namespace api \
  --context vcluster_api-prod_vclusters-prod --timeout 5m
```

### Fallback: kubectl rollout undo

Use when you need to roll back the running Deployment without touching git state (emergency only — reconcile git afterwards):

```bash
# Undo last rollout inside the vcluster
vcluster connect api-prod --namespace vclusters-prod
kubectl rollout undo deployment/api -n api
kubectl rollout status deployment/api -n api
```

### Rollback checklist

- [ ] Previous manifests commit SHA identified (`git log deploy/<env>/manifests/`)
- [ ] Rolled-back manifests applied and rollout status confirmed healthy
- [ ] git state updated to reflect what's actually running (commit or revert)
- [ ] Database migrations are backward-compatible (no destructive schema changes)
- [ ] Feature flags can disable new code paths without redeployment
- [ ] Rollback tested in staging before production release

---

## Debugging

```bash
# Connect to the target vcluster first
make connect ENV=prod
# or: vcluster connect api-prod --namespace vclusters-prod

# Pod status (inside the vcluster)
kubectl get pods -n api -l app=api
kubectl describe pod <pod-name> -n api    # events, resource limits, probe failures

# Logs
kubectl logs -n api -l app=api --tail=100 --follow
kubectl logs -n api <pod-name> --previous  # logs from crashed container

# Exec into running pod
kubectl exec -it <pod-name> -n api -- /bin/sh

# Resource usage
kubectl top pods -n api -l app=api

# Events (crashloop, OOMKill, scheduling failures)
kubectl get events -n api --sort-by='.lastTimestamp' | tail -20

# Check HPA
kubectl describe hpa api -n api

# Check why pod is Pending
kubectl describe pod <pod-name> -n api | grep -A10 Events
```

### vcluster-specific debugging

```bash
# Check the vcluster control plane health (from the HOST cluster)
kubectl get pods -n vclusters-prod        # vcluster StatefulSet should be Running

# Check vcluster syncer logs (host cluster) — useful for sync errors
kubectl logs -n vclusters-prod -l app=vcluster --tail=50

# List all vclusters and their status
vcluster list

# If the vcluster itself is unresponsive: pause and resume to restart control plane
vcluster pause api-prod --namespace vclusters-prod
vcluster resume api-prod --namespace vclusters-prod

# Compare manifests in git vs what's actually running
git show HEAD:deploy/prod/manifests/all.yaml | kubectl diff -f - -n api || true
```

### Common failure patterns

| Symptom | Likely cause | Fix |
|---|---|---|
| `CrashLoopBackOff` | App error on startup | Check logs `--previous` |
| `OOMKilled` | Memory limit too low | Increase `limits.memory` or fix leak |
| `Pending` (no nodes) | Insufficient cluster resources | Scale node pool or reduce requests |
| `Pending` (affinity) | Anti-affinity too strict | Relax `requiredDuring` → `preferredDuring` |
| Readiness failing | App not ready before probe fires | Increase `initialDelaySeconds` |
| Slow rollout | `maxUnavailable: 0` + `maxSurge: 1` | Expected — only 1 new pod at a time |

---

## Production Readiness Checklist

Before promoting to production:

### Manifests & git state
- [ ] Manifests rendered with `make render ENV=prod IMAGE_TAG=<sha>` and committed to git
- [ ] `git diff deploy/prod/manifests/` reviewed — no unexpected changes
- [ ] Image pinned to immutable tag (SHA or semver), not `:latest`
- [ ] No secrets committed — all sensitive values sourced from vault/external-secrets

### Kubernetes resources
- [ ] Resource requests and limits set — no unbounded containers
- [ ] Liveness, readiness, and startup probes configured
- [ ] `terminationGracePeriodSeconds` ≥ longest expected request duration
- [ ] `preStop` sleep to drain in-flight requests
- [ ] PodDisruptionBudget ensures minimum availability during node drains
- [ ] Pod anti-affinity spreads replicas across nodes
- [ ] HPA configured with sensible min/max
- [ ] Namespace RBAC — workloads cannot read secrets from other namespaces
- [ ] Network policies restrict egress to known destinations

### vcluster
- [ ] Target vcluster is Running (`vcluster list`)
- [ ] Connected to the correct vcluster before applying (`make connect ENV=prod`)
- [ ] vcluster resource quota is not exceeded (`kubectl describe namespace api`)
- [ ] Synced resources (Ingress, PVC) visible on host cluster after deploy

### Rollback readiness
- [ ] Previous manifests commit SHA recorded
- [ ] `make rollback ENV=prod ROLLBACK_SHA=<sha>` tested in staging
- [ ] Database migrations are backward-compatible
- [ ] Feature flags can disable new code paths without redeployment
- [ ] Alerts on pod restarts, OOMKills, and error rate spikes
