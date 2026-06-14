# Makefile-Driven Deployment Workflow

The Makefile is the source of truth for which vcluster a project belongs to. `PROJECT` and the per-env `KUBECONFIG` paths are hardcoded — not passed at runtime.

## Repository layout

```
charts/api/                    # Helm chart source
├── Chart.yaml
├── values.yaml                # base defaults
├── values-dev.yaml
├── values-staging.yaml
└── values-prod.yaml

deploy/                        # rendered manifests — committed to git
├── dev/manifests/
├── staging/manifests/
└── prod/manifests/

Makefile
```

## Makefile template

```makefile
# ---- project identity (hardcoded — this IS the cluster mapping) --
PROJECT   := ai-playground
APP       := api
NAMESPACE := api
CHART     := ./charts/api

# ---- per-environment KUBECONFIG (derived from project identity) ---
KUBECONFIG_DEV     := $(HOME)/.kube/contexts/$(PROJECT)/dev
KUBECONFIG_STAGING := $(HOME)/.kube/contexts/$(PROJECT)/staging
KUBECONFIG_PROD    := $(HOME)/.kube/contexts/$(PROJECT)/prod

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

# ---- diff ---------------------------------------------------------
.PHONY: diff
diff: whoami
	kubectl diff -f $(MANIFESTS_DIR)/ || true

# ---- deploy -------------------------------------------------------
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

## Reading a project's cluster targeting

```bash
grep -E '^\s*(PROJECT|APP|NAMESPACE|KUBECONFIG)' Makefile
# PROJECT   := ai-playground  ← tells you which vcluster dir under ~/.kube/contexts/
```

## Full pipeline usage

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

## Why helm template + git, not helm upgrade

| Concern | `helm upgrade` | `helm template` + git + `kubectl apply` |
|---|---|---|
| Audit trail | Stored in cluster Secret (opaque) | Full diff in git history |
| Rollback | `helm rollback` (cluster state) | `git show <sha> \| kubectl apply` |
| Review | `helm diff` plugin required | Plain `git diff` on YAML |
| Offline replay | Requires live cluster + Helm | Any `kubectl` with the git tree |
| Secrets leaking | Values end up in release Secret | Secrets are never in the manifests |
