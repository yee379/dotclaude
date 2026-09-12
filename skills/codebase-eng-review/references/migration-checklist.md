# Migration & Transition Checklist

Loaded at §8 of `/codebase-eng-review`, only when the plan changes live data, breaks a
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

---

## Migration mechanics

The section above covers migration *strategy*. This covers the migration *run* — which is where
migrations actually fail. **Trigger:** the change includes a schema change or a data backfill.

**Schema change safety**
- [ ] Each DDL statement is identified as lock-taking or online, **for the specific database and
      version in use** — `ALTER TABLE … ADD COLUMN NOT NULL DEFAULT` rewrites the whole table on
      older Postgres and is instant on newer; the answer is version-dependent, not general
- [ ] Expected lock type and hold time stated for each statement, against production row counts
- [ ] A `lock_timeout` / `statement_timeout` is set on the migration session, so a blocked
      migration fails fast instead of queueing every subsequent query behind it
- [ ] Adding a NOT NULL constraint is sequenced: add nullable → backfill → validate → constrain
- [ ] Index creation is concurrent (`CREATE INDEX CONCURRENTLY`), and the plan accounts for it
      being non-transactional and leaving an invalid index if it fails
- [ ] Column drops and renames are deferred to a later release, not shipped with the code that
      stops using them — a rename is a breaking change wearing a small diff

**Backfill execution**
- [ ] The backfill is **chunked**, with the chunk size and the ordering key stated — a single
      `UPDATE` over millions of rows holds one long transaction and blocks writes
- [ ] It is **resumable**: it records progress, and a restart continues rather than starting over
- [ ] It is **re-runnable**: running it twice produces the same result (cross-ref
      `references/resilience-review.md` §1)
- [ ] Estimated runtime is calculated from **production** row counts, not dev — state the number.
      A backfill that takes 14 hours changes the deployment plan
- [ ] Throttled, with replica lag or load as the signal to back off
- [ ] Progress is observable while it runs, and failure is alerted — not discovered by grep
- [ ] Rows created or modified *during* the backfill are handled (dual-write, trigger, or a
      final sweep) — otherwise the tail is silently incomplete

**Deploy ordering**
- [ ] The order of migrate-vs-deploy is explicit, and both intermediate states are safe:
      old code against new schema, and new code against old schema
- [ ] Expand-contract sequencing is stated across releases (add → dual-write → backfill →
      switch reads → stop writing old → drop), not collapsed into one deploy
- [ ] The rollback path is stated for each intermediate state, including "the code rolls back but
      the migration does not" — which is the normal case
- [ ] Any step that cannot be rolled back is named, with the gate that precedes it

**Verification**
- [ ] Forward migration tested against a production-shaped dataset (volume and edge values), not
      an empty dev database
- [ ] Rollback tested, not assumed
- [ ] A post-migration data integrity check is defined — row counts, nullability, a checksum, or
      a reconciliation query — with the expected result stated in advance
