**Only required when the plan includes any of the following:**
- A schema or data model change affecting live data
- A breaking or backward-incompatible API change
- Replacement or removal of a running service or component
- A change to how consumers discover or connect to a service (endpoint, protocol, auth)
- A dependency upgrade with a compatibility break

**If none of the above apply, skip this phase and note: "No migration required — additive change."**

Answer each item below. If an item is not applicable, say so in one line.

```
Migration pattern:
  [ ] Expand-contract (add new path, migrate consumers, remove old path)
  [ ] Strangler fig (route % of traffic to new, drain old)
  [ ] Parallel run (run old + new simultaneously, compare outputs)
  [ ] Hard cutover (maintenance window, all-at-once)
  Chosen: ___ — Rationale: ___

Backward compatibility window:
  Which existing consumers/clients must still work after the change ships?
    ___
  Until when must the old interface/schema remain available?
    ___
  How will we know all consumers have migrated?
    ___

Version skew:
  Can the old and new versions run simultaneously during rollout?  Y / N
  If N — what is the required deployment order or downtime window?
    ___
  Maximum safe skew window (time both versions can coexist):
    ___

Rollback cost:
  Can the migration be reversed without data loss?  Y / N
  If N — what is the point of no return and how do we signal it?
    ___
  Estimated rollback time:  ___
  Data at risk if rollback is needed:  ___

Deprecation timeline:
  When is the old interface/schema/service retired?
    ___
  What is the communication plan for consumers?
    ___
  Who is responsible for tracking and enforcing the cutover?
    ___

Traffic migration:
  Feature flag required?  Y / N
  If Y — flag name, initial %, and rollout stages:
    ___
  Canary required before full rollout?  Y / N
  If Y — canary size and observation window:
    ___
```
