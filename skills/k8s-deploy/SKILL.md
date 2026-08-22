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
- Writing a post-deploy smoke gate, or verifying that a rollout actually shipped
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

## Verifying a rollout actually shipped

"`rollout status` said success" is weaker evidence than it looks. Each trap below has silently
produced a believed-shipped-but-didn't outcome.

### 1. Use the same KUBECONFIG the Make targets use

Deploy Makefiles typically `export KUBECONFIG` to a specific file. A bare `kubectl` in your shell
resolves to `~/.kube/config` instead — a **different cluster or context**. Symptoms are misleading:
an expired-token error from the wrong kubeconfig looks exactly like a broken cluster.

```bash
grep -nE "^KUBECONFIG|export KUBECONFIG" Makefile      # find what the target uses
export KUBECONFIG=$HOME/.kube/<that-file>              # then match it for ad-hoc probes
```

Prefer running probes through a Make target (`make status`) that sets it for you.

### 2. Know whether your apply target restarts pods — they differ per environment

A mutable tag (`latest`) needs an explicit `rollout restart`; a pinned tag or digest triggers a new
ReplicaSet on its own. Environments in the same repo often differ:

| Overlay | Image ref | What triggers new pods |
|---|---|---|
| dev | `newTag: "latest"` | `apply` is a **no-op**; the `rollout restart` in the target does the work |
| prod | `newTag: "1.2.3@sha256:…"` | changing the ref — no restart needed, and none in the target |

Read the target before trusting it: `grep -nE "rollout restart" <overlay>/Makefile`. Assuming a
restart happens when it doesn't means shipping nothing and reporting success.

### 3. Diff before applying

```bash
kubectl diff -k <overlay>/            # exits 0 and prints nothing when there is no drift
```

This catches unrelated drift about to be swept in, and tells you whether the apply or the restart is
what will actually change anything.

### 4. Compare image **digests**, not tags

With a mutable tag the tag is identical before and after, so it proves nothing. The digest is the
only evidence the new build is running:

```bash
kubectl get pods -n <ns> -l app=<app> \
  -o custom-columns='NAME:.metadata.name,DIGEST:.status.containerStatuses[0].imageID'
```

Record the digest **before** deploying. Also verify the rendered reference, not just your file edit:
`kubectl kustomize <overlay>/ | grep "image:"` (fetch generator inputs first, or it errors).

### 5. Read metrics from inside the pod when the scrape path is blocked

A NetworkPolicy that admits only the ingress controller will deny Prometheus, so dashboards are
empty even though `/metrics` is fine. Slim and distroless images often have **no `curl`** — use the
app's own interpreter:

```bash
kubectl exec -n <ns> <pod> -- python -c \
  'import urllib.request;print(urllib.request.urlopen("http://localhost:8080/metrics",timeout=5).read().decode())'
```

Counters are **per-pod and reset on restart**, so a post-deploy number is never comparable to a
pre-deploy one. Query every replica and compare **rates**, not totals.

### 6. Confirm the success traffic exercises the code you changed

The most dangerous false positive. A large `granted` count can come entirely from a code path your
change never touches — e.g. session-cookie auth delegating to an external proxy while the change was
to JWT validation. Thousands of successes then prove only that the service is up.

Identify which path your change is on, find the label that distinguishes it (`issuer=`, `path=`,
`method=`), and require a **non-zero success count on that specific label** before calling a rollout
verified. If the environment carries no such traffic, say the gate is unmet rather than substituting
an unrelated green signal — and note that a low-traffic dev may be unable to prove what a
high-traffic prod proves in minutes.

### 7. A leaked `port-forward` will let you verify the wrong environment

The nastiest one, because every check passes. `kubectl port-forward` is the usual way to reach a
service whose scrape path is blocked — and a forward left running by an earlier probe keeps serving
`/health` happily. Point a new probe at the same local port and you are talking to **whatever
namespace the old forward opened**, not the one you think.

This has produced a full green run for a production rollout that had not happened: a leaked *dev*
forward on `:18080` answered every request, so the prod check reported the new version while the prod
pods were still on the old image. Two failure modes combine:

- **The port is already bound.** Your new forward fails to bind, prints to a discarded stderr, and
  the old one answers. Treat "something already responds on this port" as **fatal**, never a warning.
- **Backgrounding a shell *function* orphans the child.** With `k() { KUBECONFIG=$KC kubectl "$@"; }`,
  `k port-forward … &` makes `$!` the **subshell's** PID. A `trap … EXIT` that kills `$!` kills the
  wrapper and leaves the real `kubectl` holding the port. Background `kubectl` **directly**:

```bash
KUBECONFIG="$KC" kubectl port-forward -n "$NS" svc/<svc> "${PORT}:8080" >/dev/null 2>&1 &
PF_PID=$!                                   # now really the kubectl PID
kill -0 "$PF_PID" 2>/dev/null || exit 1     # died? stop waiting on it
```

```bash
pkill -f "port-forward.*${PORT}:8080"       # clear leaks before probing
ps -ef | grep -c '[p]ort-forward'            # confirm zero afterwards
```

**Cross-check the target with a second, independent signal.** The port guard is preventative; this
catches the case where it fails. Compare something kubectl reports against something the service
reports, and fail on disagreement:

```bash
kubectl get pods -n "$NS" -l app=<app> -o jsonpath='{.items[0].spec.containers[0].image}'
curl -s http://localhost:${PORT}/health | jq -r .version
# tag and served version disagree → you are not talking to $NS. Fail, don't warn.
```

(Strip the `@sha256:…` digest **before** taking the tag — `sed 's/.*://'` is greedy and returns the
digest hex, which makes the check silently self-skip.)

### 8. Roll back through git, never `kubectl rollout undo`

`undo` leaves the cluster diverged from the committed manifests, so the next routine apply silently
re-applies the bad version and undoes the undo. Revert the manifest change and re-apply.

---

## Post-deploy smoke gate

A rollout is not verified until a **script** says so with an exit code. Manual curl-and-eyeball is
not a gate: it is not repeatable, it silently shrinks each time you run it, and it cannot fail a
promotion. Every service should have one command:

```bash
scripts/smoke-<service>.sh dev      # exit 0 = promote; exit 1 = do not
scripts/smoke-<service>.sh prod
```

**Run it before the rollout too.** A gate nobody has seen fail is not known to test anything. The
pre-rollout baseline should fail on exactly the checks the new version changes, and pass on
everything else — that is the evidence the gate discriminates rather than always printing green. A
baseline that passes completely means either the rollout already happened or the gate is vacuous;
find out which before deploying.

**Design rules**, each earned by a failure:

| Rule | Why |
|---|---|
| Assert an **identity** signal, not just liveness | `/health` answers from any environment. See trap 7 — pin down *which* one you reached |
| Read the expected version from the **repo** (`VERSION`, chart `appVersion`), not an argument | Makes the run assert "what is in the working tree is what is running" instead of restating what you typed |
| **Count skips and print them**; never let a skip pass silently | A gate that quietly stops checking something is worse than no gate. `PASSED (with 2 skips)` is honest; a bare `PASSED` is not |
| Assert the **negative** paths | "It's up" is the cheap half. Unauthenticated → 401, wrong group → 403, and **no identity headers on a refusal** — a 401 that still emits them is a bypass with extra steps |
| Assert **all pods run one image** | A half-finished rollout otherwise gets tested through whichever pod the forward landed on |
| Depend only on `kubectl`/`curl`/`jq`/`python3` | Gates that need a venv, a fixture app, or a live hostname rot within months and then nobody runs them. Delegate the one check that genuinely needs more, and **skip loudly** if its dependency is absent |
| Print expected values in the runbook | `hostnames_loaded 18, conflicts 3` — otherwise a reader cannot tell a correct number from a broken one |

Wire it into the promotion path so it cannot be skipped: baseline → apply → gate on dev → gate on
prod, with `exit 1` blocking the next step. The single most important property is that **a gate which
can report on the wrong environment is worse than no gate at all** — it converts "we didn't check"
into "we checked and it was fine."

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

### Post-deploy verification
See `## Verifying a rollout actually shipped` and `## Post-deploy smoke gate` for why each of these is
not redundant.
- [ ] **Smoke gate script exists** and is the thing that decides promotion — not a manual checklist
- [ ] Smoke gate run **before** the rollout, and it **failed** on the checks this release changes
- [ ] No leaked `port-forward` on the probe port; target confirmed by a second independent signal
- [ ] Skips in the gate output read and accepted — each one is something that was *not* verified
- [ ] Pre-deploy baseline recorded: image **digest**, replica count, restart count, key metric counters
- [ ] `kubectl diff -k` reviewed — only the intended change, no swept-in drift
- [ ] Confirmed whether the apply target restarts pods, or the image ref change does
- [ ] Post-deploy **digest differs** from the pre-deploy digest on every replica
- [ ] Version actually served confirmed from inside the pod, not inferred from the tag
- [ ] Restart count still 0 and all replicas `Ready` after the rollout settles
- [ ] Logs checked for tracebacks and non-2xx spikes, not just "pod is Running"
- [ ] **Success traffic on the specific code path that changed** — non-zero, on the distinguishing label
- [ ] Abort criteria named *before* deploying, as a rate against the baseline, with the rollback command ready

---

## References

Load when needed:
- `references/vcluster-cli.md` — vcluster CLI quickstart and KUBECONFIG conventions
- `references/makefile-workflow.md` — full Makefile template and repository layout
- `references/deployment-templates.md` — Deployment, Service, Ingress, HPA, PDB YAML
- `references/debugging.md` — debugging failing deployments and pod issues
- `references/dockerfiles.md` — multi-stage Dockerfile templates (Node.js, Go, Python)
- `references/github-actions.md` — CI/CD pipeline shape
