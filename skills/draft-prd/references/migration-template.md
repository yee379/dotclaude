```
Migration pattern:
  [ ] Expand-contract (add new resource/path, migrate consumers, remove old)
  [ ] Parallel run (old + new run simultaneously, compare outputs)
  [ ] Rolling replace (drain nodes/pods in waves, no hard cutover)
  [ ] Hard cutover (maintenance window, all-at-once)
  Chosen: ___ — Rationale: ___

Workload impact during transition:
  Which running workloads are affected during the change (not just after)?
    ___
  Will any pods be restarted, drained, or rescheduled as part of this change?
    ___
  Is there a safe apply order that minimises disruption?
    ___

Version skew:
  Can the old and new versions of affected components run simultaneously?  Y / N
  If N — what is the required apply order or maintenance window?
    ___
  Maximum safe skew window (how long both versions can coexist):
    ___

Rollback cost:
  Can the change be fully reversed without data loss or manual intervention?  Y / N
  If N — what is the point of no return and how do we communicate it?
    ___
  Estimated rollback time:  ___
  State at risk if rollback is needed (PVC data, CRD state, etc.):  ___

Deprecation / retirement:
  If replacing an existing resource or interface — when is the old one removed?
    ___
  What depends on the old resource and must be migrated first?
    ___

Traffic / connection migration:
  Is a gradual traffic shift required (canary, weighted routing)?  Y / N
  If Y — tool (Istio weights / NGINX / DNS TTL), initial %, and observation window:
    ___
  DNS or endpoint cutover required?  Y / N
  If Y — TTL reduction plan and rollback DNS path:
    ___
```
