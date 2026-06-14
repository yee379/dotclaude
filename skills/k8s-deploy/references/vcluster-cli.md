# vcluster CLI Reference

## Installation

```bash
# macOS
brew install loft-sh/tap/vcluster
```

## Listing and connecting

```bash
# List all vclusters visible from the host cluster
KUBECONFIG=~/.kube/config.sdf-k8s01 vcluster list

# Export a vcluster's kubeconfig to a file (preferred pattern)
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
```

## Creating and managing vclusters

```bash
# Create a new vcluster (run from host context)
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster create ai-playground --namespace vclusters-ai-playground

# Pause a vcluster (scales control plane to 0 — saves cost in non-prod)
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster pause ai-playground --namespace vclusters-ai-playground

# Resume
KUBECONFIG=~/.kube/config.sdf-k8s01 \
  vcluster resume ai-playground --namespace vclusters-ai-playground
```

## vcluster.yaml — configuration

The config lives at `./infra/vclusters/<project>/vcluster.yaml`. Key sections: `controlPlane.distro`, `sync.toHost` (enable ingresses/PVCs/services), and `policies.resourceQuota`. Deploy or upgrade with:

```bash
vcluster create prod --namespace vclusters-prod \
  --values ./infra/vclusters/prod/vcluster.yaml --upgrade
```

## KUBECONFIG conventions

We use **separate kubeconfig files per vcluster/namespace** rather than merging all contexts into `~/.kube/config`:

```
~/.kube/
├── config.sdf-k8s01                      # host cluster
└── contexts/
    ├── ai-playground/
    │   ├── dev
    │   ├── staging
    │   └── prod
    └── <other-project>/
        └── prod
```

Key rules:
- Always `echo $KUBECONFIG` or `kubectl config current-context` before any destructive command
- The host kubeconfig (`config.sdf-k8s01`) is for infrastructure operations only
- Never merge kubeconfigs with `kubectl config flatten`
