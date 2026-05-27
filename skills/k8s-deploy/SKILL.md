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
Host cluster: sdf-k8s01
KUBECONFIG=~/.kube/config.sdf-k8s01
│
├── vcluster: ai-playground
│   ├── namespace: dev    ← KUBECONFIG=~/.kube/contexts/ai-playground/dev
│   ├── namespace: staging← KUBECONFIG=~/.kube/contexts/ai-playground/staging
│   └── namespace: prod   ← KUBECONFIG=~/.kube/contexts/ai-playground/prod
│
└── vcluster: <other-project>
    └── namespace: prod   ← KUBECONFIG=~/.kube/contexts/<other-project>/prod
```

- **Inside a vcluster:** standard `kubectl`, `helm`, `make deploy` — looks and feels like a real cluster.
- **From the host:** vclusters appear as StatefulSets + Services in their host namespace. Host nodes are shared.
- **Isolation:** each vcluster has its own namespaces, RBAC, and resource quotas, fully isolated from other vclusters.
- **Syncing:** by default, Pods created inside a vcluster are synced down to the host cluster as real Pods. Services, Ingresses, and PVCs can also be synced (configured in `vcluster.yaml`).

### KUBECONFIG conventions

We use **separate kubeconfig files per vcluster/namespace** rather than merging all contexts into a single `~/.kube/config`. Switching clusters is done by setting `KUBECONFIG`.

```
~/.kube/
├── config.sdf-k8s01                      # host cluster (sdf-k8s01)
└── contexts/
    ├── ai-playground/
    │   ├── dev
    │   ├── staging
    │   └── prod
    └── <other-project>/
        └── prod
```

```bash
# Host cluster (sdf-k8s01) — manage vclusters themselves, inspect host-level resources
export KUBECONFIG=/sdf/home/y/ytl/.kube/config.sdf-k8s01

# ai-playground vcluster — prod namespace
export KUBECONFIG=/sdf/home/y/ytl/.kube/contexts/ai-playground/prod

# Confirm which cluster/context is active
kubectl config current-context
kubectl config get-contexts

# One-liner: run a command against a specific cluster without changing the env
KUBECONFIG=~/.kube/contexts/ai-playground/prod kubectl get pods
```

**Key rules:**
- Always `echo $KUBECONFIG` or `kubectl config current-context` before any destructive command
- Never merge kubeconfigs with `kubectl config flatten` — keep them separate files for clarity
- The host kubeconfig (`config.sdf-k8s01`) is for infrastructure operations only; workloads are deployed via their vcluster kubeconfig

### CLI quickstart

```bash
# Install the CLI (macOS)
brew install loft-sh/tap/vcluster

# List all vclusters visible from the host cluster
KUBECONFIG=~/.kube/config.sdf-k8s01 vcluster list

# Create a new vcluster (run from host context)
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster create ai-playground --namespace vclusters-ai-playground

# Export a vcluster's kubeconfig to a file (our preferred pattern)
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster connect ai-playground \
    --namespace vclusters-ai-playground \
    --update-current=false \
    --kube-config ~/.kube/contexts/ai-playground/prod

# Connect interactively (temporarily switches current context)
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster connect ai-playground --namespace vclusters-ai-playground

# Disconnect (restores previous context)
vcluster disconnect

# Pause a vcluster (scales control plane to 0 — saves cost in non-prod)
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster pause ai-playground --namespace vclusters-ai-playground

# Resume
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster resume ai-playground --namespace vclusters-ai-playground
```

### vcluster.yaml — configuration

The `vcluster.yaml` config lives at `./infra/vclusters/<project>/vcluster.yaml`. Key sections: `controlPlane.distro`, `sync.toHost` (enable ingresses/PVCs/services), and `policies.resourceQuota`. Deploy or upgrade with:

```bash
vcluster create prod --namespace vclusters-prod \
  --values ./infra/vclusters/prod/vcluster.yaml --upgrade
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

The Makefile is the source of truth for which vcluster a project belongs to. `PROJECT` and the per-env `KUBECONFIG` paths are hardcoded — not passed at runtime. A developer reading the Makefile immediately knows exactly which cluster each `make` target hits.

```makefile
# ---- project identity (hardcoded — this IS the cluster mapping) --
# These values define which vcluster this project lives in.
# Change them here if the project moves to a different vcluster.
PROJECT   := ai-playground
APP       := api
NAMESPACE := api
CHART     := ./charts/api

# ---- per-environment KUBECONFIG (derived from project identity) ---
# Each env maps to a specific kubeconfig file. No --context flag needed.
KUBECONFIG_DEV     := $(HOME)/.kube/contexts/$(PROJECT)/dev
KUBECONFIG_STAGING := $(HOME)/.kube/contexts/$(PROJECT)/staging
KUBECONFIG_PROD    := $(HOME)/.kube/contexts/$(PROJECT)/prod

# Default env (can still be overridden: make deploy ENV=prod)
ENV       ?= dev
KUBECONFIG := $(HOME)/.kube/contexts/$(PROJECT)/$(ENV)
export KUBECONFIG

IMAGE_TAG  ?= $(shell git rev-parse --short HEAD)
MANIFESTS_DIR := ./deploy/$(ENV)/manifests

# ---- guard: confirm target cluster before any deploy/rollback -----
.PHONY: whoami
whoami:
	@echo "Project:    $(PROJECT)"
	@echo "Env:        $(ENV)"
	@echo "KUBECONFIG: $(KUBECONFIG)"
	@kubectl config current-context

# ---- render -------------------------------------------------------
# Render Helm chart to plain YAML and commit — this is the source of truth.
.PHONY: render
render:
	@echo "Rendering $(ENV) manifests (image: $(IMAGE_TAG))..."
	mkdir -p $(MANIFESTS_DIR)
	helm template $(APP) $(CHART) \
	  -f $(CHART)/values.yaml \
	  -f $(CHART)/values-$(ENV).yaml \
	  --set image.tag=$(IMAGE_TAG) \
	  --namespace $(NAMESPACE) \
	  > $(MANIFESTS_DIR)/all.yaml
	@echo "Rendered → $(MANIFESTS_DIR)/all.yaml"

# Split multi-doc YAML into individual files (optional): add --output-dir $(MANIFESTS_DIR) instead of > all.yaml

# ---- diff ---------------------------------------------------------
# Show what would change before applying.
.PHONY: diff
diff: whoami
	kubectl diff -f $(MANIFESTS_DIR)/ || true

# ---- deploy -------------------------------------------------------
# Apply committed manifests. render MUST be run (and committed) first.
.PHONY: deploy
deploy: whoami
	@echo "Deploying $(ENV) from $(MANIFESTS_DIR)..."
	kubectl apply -f $(MANIFESTS_DIR)/ --namespace $(NAMESPACE)
	kubectl rollout status deployment/$(APP) \
	  --namespace $(NAMESPACE) --timeout 5m

# ---- render + commit + deploy (full pipeline) --------------------
.PHONY: release
release: render
	git add $(MANIFESTS_DIR)/
	git diff --cached --quiet || git commit -m "deploy($(ENV)): render manifests for $(IMAGE_TAG)"
	$(MAKE) deploy

# ---- rollback (git-based) ----------------------------------------
# Roll back to any previously committed manifest state.
# Usage: make rollback ENV=prod ROLLBACK_SHA=abc1234
.PHONY: rollback
rollback: whoami
	@echo "Rolling back $(ENV) to $(ROLLBACK_SHA)..."
	git show $(ROLLBACK_SHA):$(MANIFESTS_DIR)/all.yaml \
	  | kubectl apply -f - --namespace $(NAMESPACE)
	kubectl rollout status deployment/$(APP) \
	  --namespace $(NAMESPACE) --timeout 5m

# ---- helpers ------------------------------------------------------
.PHONY: pods logs
pods: whoami
	kubectl get pods -n $(NAMESPACE)
logs:
	kubectl logs -n $(NAMESPACE) -l app=$(APP) --tail=100 --follow
```

### Reading a project's cluster targeting

```bash
grep -E '^\s*(PROJECT|APP|NAMESPACE|KUBECONFIG)' Makefile
# PROJECT   := ai-playground  ← tells you which vcluster dir under ~/.kube/contexts/
```

---

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

Each environment is a separate vcluster with its own kubeconfig. Switching environments = setting `KUBECONFIG`. Always run `make whoami ENV=prod` to confirm target before deploying.

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

**Never commit secret values to git.** Use External Secrets Operator (preferred) to sync from Vault/AWS SM/GCP SM into K8s Secrets at runtime:

```yaml
# Option A: plain K8s Secret — inject value from CI/CD pipeline at render time
#   stringData: { DATABASE_URL: "$(DATABASE_URL)" }
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
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml         # override: replicaCount, resources, autoscaling, ingress
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── hpa.yaml
    ├── pdb.yaml
    ├── configmap.yaml
    └── _helpers.tpl
```

Key `values.yaml` fields: `image.repository`, `image.tag` (overridden in CI with SHA), `replicaCount`, `resources.requests/limits`, `autoscaling.enabled/min/max`, `ingress.enabled/host/tls`, `env` (injected as ConfigMap).

### Helm deploy commands (reference only)

> We use `make render` + `make deploy` (not `helm upgrade` directly). See [Makefile-Driven Deployment Workflow](#makefile-driven-deployment-workflow). The one exception: third-party charts you don't own (cert-manager, ingress-nginx):
> ```bash
> helm upgrade --install cert-manager jetstack/cert-manager \
>   --namespace cert-manager --create-namespace --atomic --timeout 5m --wait
> ```

---

## Rollback

### Preferred: git-based rollback

Since manifests are committed to git, rolling back means applying a previous commit's manifests:

```bash
# Set KUBECONFIG to the target environment first
export KUBECONFIG=~/.kube/contexts/ai-playground/prod

# Find the commit with the last known-good manifests
git log --oneline deploy/prod/manifests/

# Roll back using the Makefile target
make rollback ENV=prod ROLLBACK_SHA=<commit-sha>

# Or manually:
git show <commit-sha>:deploy/prod/manifests/all.yaml \
  | kubectl apply -f - --namespace api

kubectl rollout status deployment/api --namespace api --timeout 5m
```

### Fallback: kubectl rollout undo

Use when you need to roll back the running Deployment without touching git state (emergency only — reconcile git afterwards):

```bash
export KUBECONFIG=~/.kube/contexts/ai-playground/prod
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

Load `references/debugging.md` when a deployment fails or pods are not healthy.

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

---

## Deployment Strategy Concepts

| Strategy | How it works | K8s config | Use when |
|----------|-------------|------------|----------|
| **Rolling** (default) | Replace pods gradually; old+new run simultaneously | `strategy.type: RollingUpdate`, `maxSurge: 1, maxUnavailable: 0` | Standard deploys; changes must be backward-compatible |
| **Blue-Green** | Two identical envs; switch traffic atomically | Two Deployments; swap Service selector | Zero-tolerance for issues; instant rollback required |
| **Canary** | Route small % to new version; increase gradually | Two Deployments + weighted Ingress/mesh | High-traffic services; risky changes |

---

## Multi-Stage Dockerfiles

Node.js, Go, and Python multi-stage Dockerfile templates with non-root user, layer caching, and health checks.

> Read when needed: `~/.claude/skills/k8s-deploy/references/dockerfiles.md`

Key rules: pin specific version tags, run as non-root (UID 1001), copy dependency files before source for layer caching, add `.dockerignore` excluding `node_modules/.git/tests`, never store secrets in the image.

---

## Health Check Endpoint

Expose `/healthz` (liveness) and `/readyz` (readiness). Readiness checks backing services; liveness does not.

```typescript
app.get("/healthz", (_, res) => res.status(200).json({ status: "ok" }));

app.get("/readyz", async (_, res) => {
  try {
    await db.query("SELECT 1");
    res.status(200).json({ status: "ok" });
  } catch {
    res.status(503).json({ status: "error", message: "Database unreachable" });
  }
});
```

K8s probe config: see the Deployment YAML in the [Manifests section](#deployment-production-ready-baseline) above.

---

## GitHub Actions CI/CD

Pipeline shape: `lint → typecheck → test → build image → make release ENV=staging → make release ENV=prod`

> Read when needed: `~/.claude/skills/k8s-deploy/references/github-actions.md`

---
