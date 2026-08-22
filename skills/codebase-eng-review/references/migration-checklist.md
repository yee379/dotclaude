# Migration & Transition Checklist

Loaded at §5 of `/codebase-eng-review`, only when the plan changes live data, breaks a
contract, replaces a running component, changes how consumers connect, or upgrades a
dependency incompatibly. For each item that is unresolved, incomplete, or answered wrongly,
raise it as an issue — one AskUserQuestion per gap.

**Migration pattern**
- [ ] A migration pattern has been chosen: expand-contract / strangler fig / parallel run / hard cutover
- [ ] The rationale for that pattern is documented (not just named)
- [ ] The plan does NOT use hard cutover where a safer pattern is viable — hard cutover must be explicitly justified

**Backward compatibility**
- [ ] All existing consumers/clients that must continue working are identified
- [ ] The backward compatibility window is defined (until when must the old interface remain available?)
- [ ] There is a mechanism to know when all consumers have migrated (tracking, version header, deprecation metric)

**Version skew**
- [ ] It is confirmed whether old and new versions can run simultaneously during rollout
- [ ] If they cannot — the required deployment order or maintenance window is documented
- [ ] The maximum safe skew window is stated (how long both can coexist before the old must be removed)

**Rollback cost**
- [ ] It is confirmed whether the migration is reversible without data loss
- [ ] If irreversible — the point of no return is identified and there is a gate before it (e.g. dry-run, confirmation step)
- [ ] Estimated rollback time is stated
- [ ] Data or state at risk during rollback is identified

**Deprecation**
- [ ] A deadline for retiring the old interface/schema/service is set
- [ ] Dependents are identified and a communication or migration plan exists
- [ ] Ownership of tracking the cutover is assigned

**Traffic migration**
- [ ] If gradual rollout is needed: feature flag name, initial %, and rollout stages are defined
- [ ] If canary is needed: canary size and observation window are stated
- [ ] There is a clear "full rollout" and "flag cleanup" step — not just "increase to 100%"
