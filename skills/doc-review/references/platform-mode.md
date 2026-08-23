# Platform Mode Review Sections

Load when mode detection resolves to **Platform**. Replaces the codebase review sections in
`SKILL.md`. Work through P1–P5 in order; P1 has the highest priority.

Question discipline is the same as codebase mode: one gap = one `AskUserQuestion`, never batched,
with options **A)** add to plan now **B)** defer to post-apply close-out **C)** not needed, and
your recommendation stated. **Runbook gaps are always option A — never defer them.**

---

## P1. Runbook coverage (highest priority)

- Is there a runbook section for every new failure mode introduced?
- Does the runbook cover restart, rollback, and scaling procedures?
- If an existing runbook is invalidated by this change, is the update called out in the plan?
- Is the runbook linked from the monitoring dashboard?

These directly affect on-call safety. **STOP** — one question per gap.

## P2. Architecture and topology documentation

- Is `ARCHITECTURE.md` updated to reflect the new topology?
- Are namespace strategy diagrams updated?
- Is the network topology diagram updated?
- Does the plan name the ADRs that need writing for significant decisions? (Writing them is
  `/codebase-arch-review`'s job — you check the plan accounts for the work.)

**STOP** — one question per gap.

## P3. Onboarding and operator documentation

- Is the application onboarding guide updated with new prerequisites or steps?
- Is the platform README updated with new capabilities?
- Is the Helm chart documentation updated with new values or changed defaults?
- If this introduces a new self-service capability (new StorageClass, new Ingress class), is
  there documentation for how teams use it?

**STOP** — one question per gap.

## P4. Capacity and operational baselines

- Is the capacity baseline document updated with new resource utilisation figures?
- Are capacity projections documented for planning purposes?

Whether the *sizing itself* is right is `/platform-capacity-review`'s call — you check only that
the plan records the updated figures somewhere.

**STOP** — one question per gap.

## P5. Breaking changes and migrations

A migration guide is required if any of these is true:

- Namespace renamed or removed
- StorageClass changed or removed (requires PVC migration)
- Ingress path or hostname changed
- Config key renamed or removed
- Service name or port changed
- RBAC policy changed in a way that removes existing access

For each breaking change, the plan must specify: what breaks, how to detect it, how to migrate,
and the rollback path — plus how it is communicated to affected teams before the change is applied.

**STOP** — one question per gap.
