---
name: k8s-deploy
description: Kubernetes deployment patterns, Helm charts, Makefile-driven workflows, vcluster (loft.sh) virtual clusters, namespace-based environment promotion (test to production), rollback strategies, resource tuning, health probes, and production readiness for containerised backend and DevOps workloads.
license: MIT
compatibility: opencode
---

# Kubernetes Deploy

End-to-end guidance for deploying and operating services on Kubernetes — from manifest authoring through environment promotion to production rollback.

**This environment uses [vcluster (loft.sh)](https://www.vcluster.com) virtual clusters and Makefile-driven deployment workflows.** Manifests are rendered from Helm + values files and committed to git as the source of truth. Direct `helm upgrade` is not the deploy mechanism — Make targets are.

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

- **Inside a vcluster:** standard `kubectl`, `helm`, `make deploy` — looks like a real cluster.
- **Isolation:** each vcluster has its own namespaces, RBAC, and resource quotas.
- **Syncing:** Pods created inside a vcluster are synced down to the host cluster as real Pods.

Load `references/vcluster-cli.md` for the full CLI quickstart, KUBECONFIG conventions, and `vcluster.yaml` config reference.

---

## Makefile-Driven Deployment Workflow

We **do not run `helm upgrade` directly** as the deploy step. Instead:

1. **`helm template`** renders chart + values into plain YAML manifests
2. The rendered manifests are **committed to git** as the canonical state
3. **`kubectl apply`** (via Make targets) applies those committed manifests

This gives a complete, auditable, diff-able history of exactly what was deployed — no state hidden inside Helm's release secret.

Load `references/makefile-workflow.md` for the full Makefile template, repository layout, and the `helm template` vs `helm upgrade` comparison table.

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

Each environment is a separate vcluster with its own kubeconfig. Always run `make whoami ENV=prod` to confirm target before deploying.

---

## Deployment Templates

Load `references/deployment-templates.md` for production-ready YAML for: Deployment (with all probes, resource limits, anti-affinity, preStop), Service + Ingress, HPA, and PodDisruptionBudget.

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

Key `values.yaml` fields: `image.repository`, `image.tag`, `replicaCount`, `resources.requests/limits`, `autoscaling.enabled/min/max`, `ingress.enabled/host/tls`, `env`.

**Exception for third-party charts you don't own** (cert-manager, ingress-nginx):
```bash
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace --atomic --timeout 5m --wait
```

---

## Secrets Management

**Never commit secret values to git.** Use External Secrets Operator (preferred) to sync from Vault/AWS SM/GCP SM into K8s Secrets at runtime:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
  namespace: prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: api-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: prod/api/database-url
```

---

## Rollback

### Preferred: git-based rollback

```bash
export KUBECONFIG=~/.kube/contexts/ai-playground/prod
git log --oneline deploy/prod/manifests/
make rollback ENV=prod ROLLBACK_SHA=<commit-sha>
```

### Fallback: kubectl rollout undo (emergency only — reconcile git afterwards)

```bash
export KUBECONFIG=~/.kube/contexts/ai-playground/prod
kubectl rollout undo deployment/api -n api
```

### Rollback checklist

- [ ] Previous manifests commit SHA identified
- [ ] Rolled-back manifests applied and rollout status confirmed healthy
- [ ] git state updated to reflect what's actually running
- [ ] Database migrations are backward-compatible
- [ ] Feature flags can disable new code paths without redeployment

---

## Health Check Endpoints

Expose `/healthz` (liveness — no dependency checks) and `/readyz` (readiness — checks backing services):

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

---

## Deployment Strategy Concepts

| Strategy | How it works | K8s config | Use when |
|----------|-------------|------------|----------|
| **Rolling** (default) | Replace pods gradually | `RollingUpdate`, `maxSurge: 1, maxUnavailable: 0` | Standard deploys; backward-compatible |
| **Blue-Green** | Two identical envs; switch traffic atomically | Two Deployments; swap Service selector | Zero-tolerance for issues |
| **Canary** | Route small % to new version; increase gradually | Two Deployments + weighted Ingress | High-traffic risky changes |

---

## Production Readiness Checklist

### Manifests & git state
- [ ] Manifests rendered with `make render ENV=prod IMAGE_TAG=<sha>` and committed
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
- [ ] Network policies restrict egress to known destinations

### vcluster
- [ ] Target vcluster is Running (`vcluster list`)
- [ ] Connected to correct vcluster before applying (`make whoami ENV=prod`)
- [ ] vcluster resource quota not exceeded

### Rollback readiness
- [ ] Previous manifests commit SHA recorded
- [ ] `make rollback` tested in staging
- [ ] Database migrations are backward-compatible
- [ ] Alerts on pod restarts, OOMKills, and error rate spikes

---

## References

Load when needed:
- `references/vcluster-cli.md` — vcluster CLI quickstart and KUBECONFIG conventions
- `references/makefile-workflow.md` — full Makefile template and repository layout
- `references/deployment-templates.md` — Deployment, Service, Ingress, HPA, PDB YAML
- `references/debugging.md` — debugging failing deployments and pod issues
- `references/dockerfiles.md` — multi-stage Dockerfile templates (Node.js, Go, Python)
- `references/github-actions.md` — CI/CD pipeline shape
