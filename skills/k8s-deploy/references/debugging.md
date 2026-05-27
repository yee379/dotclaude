## Debugging

```bash
# Set KUBECONFIG to the target vcluster first — then all kubectl commands
# automatically hit the right cluster with no --context needed.
export KUBECONFIG=~/.kube/contexts/ai-playground/prod

# Pod status
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
# Switch to the HOST cluster to inspect vcluster infrastructure
export KUBECONFIG=~/.kube/config.sdf-k8s01

# Check the vcluster control plane pods (host-side)
kubectl get pods -n vclusters-ai-playground

# Check vcluster syncer logs — useful for sync errors (Ingress/PVC not appearing)
kubectl logs -n vclusters-ai-playground -l app=vcluster --tail=50

# List all vclusters
vcluster list

# If a vcluster is unresponsive: pause and resume to restart the control plane
vcluster pause ai-playground --namespace vclusters-ai-playground
vcluster resume ai-playground --namespace vclusters-ai-playground

# Compare committed manifests vs what's actually running in the vcluster
export KUBECONFIG=~/.kube/contexts/ai-playground/prod
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
