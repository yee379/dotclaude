---
name: platform-doc-review
description: Pre-implementation platform documentation review. Checks that the platform plan explicitly identifies every doc that needs updating — runbooks, architecture diagrams, onboarding guides, operator docs, CHANGELOG, ADRs — before any cluster change is made. Use when asked to "check the platform docs plan", "what docs need updating for this platform change?", or as part of /platform-board-review.
---

# Platform Documentation Review

## Workflow position

```
/platform-draft
      │
      ▼
/platform-board-review ──── runs these reviewers in parallel ────┐
      │                                                     │
      │   /platform-arch-review                             │
      │   /platform-capacity-review                         │
      │   /platform-security-review                         │
      │   /platform-ops-review                              │
      │   /platform-eng-review                              │
      │   /platform-doc-review  ← YOU ARE HERE              │
      └─────────────────────────────────────────────────────┘
```

**Model routing:** Documentation scope assessment (Step 0) is `haiku`-eligible. Gap analysis and breaking change assessment require `sonnet`.

Do NOT make cluster changes. Do NOT update docs now. Identify gaps in the plan's documentation coverage and ensure the plan names them.

---

## Priority hierarchy

Documentation impact table > Runbook gaps > Onboarding guide gaps > Breaking changes > Everything else.

---

## Step 0: Documentation scope assessment

1. **What is the operator-facing surface area?** New services to manage, new failure modes, new config options, changed operational procedures.
2. **What is the developer/user-facing surface area?** New self-service capabilities, new onboarding steps, new things teams need to know.
3. **Is there a breaking change?** Namespace renames, StorageClass changes, ingress path changes, config key renames.
4. **Is this a pure internal infrastructure change with no operator or user impact?** If yes, exit: "No documentation surface. Skipping platform-doc-review."

---

## Documentation impact table

```
DOC                           | AFFECTED? | WHAT CHANGES                        | IN PLAN?
------------------------------|-----------|--------------------------------------|----------
ARCHITECTURE.md (cluster)     | yes/no/—  | [cluster topology changes]           | yes/no/n-a
Runbook: <service>            | yes/no/—  | [new failure modes, procedures]      | yes/no/n-a
Onboarding guide              | yes/no/—  | [new steps, new prerequisites]       | yes/no/n-a
Platform README               | yes/no/—  | [new capabilities, changed setup]    | yes/no/n-a
ADRs                          | yes/no/—  | [infrastructure decisions to record] | yes/no/n-a
CHANGELOG / release notes     | yes/no/—  | [operator-facing changes]            | yes/no/n-a
Helm chart README             | yes/no/—  | [new values, changed defaults]       | yes/no/n-a
Capacity baseline doc         | yes/no/—  | [updated cluster capacity figures]   | yes/no/n-a
Network topology diagram      | yes/no/—  | [new services, new paths]            | yes/no/n-a
Secret rotation runbook       | yes/no/—  | [new secrets, changed rotation]      | yes/no/n-a
On-call rotation doc          | yes/no/—  | [new service, new rotation entry]    | yes/no/n-a
Application onboarding guide  | yes/no/—  | [new self-service capabilities]      | yes/no/n-a
Monitoring/alerting guide     | yes/no/—  | [new dashboards, new alert rules]    | yes/no/n-a
Security posture doc          | yes/no/—  | [RBAC changes, new policies]         | yes/no/n-a
Migration/upgrade guide       | yes/no/—  | [breaking changes, migration steps]  | yes/no/n-a
```

Any row **AFFECTED: yes** and **IN PLAN?: no** is a gap.

---

## Review sections

### 1. Runbook coverage (highest priority)

- Is there a runbook section for every new failure mode introduced?
- Does the runbook cover restart, rollback, and scaling procedures?
- If an existing runbook is invalidated by this change, is the update called out in the plan?
- Is the runbook linked from the monitoring dashboard?

**STOP.** One AskUserQuestion per runbook gap — these directly affect on-call safety.

---

### 2. Architecture and topology documentation

- Is `ARCHITECTURE.md` updated to reflect new topology?
- Are namespace strategy diagrams updated?
- Is the network topology diagram updated?
- Are new ADRs called out in the plan for significant decisions?

---

### 3. Onboarding and operator documentation

- Is the application onboarding guide updated with new prerequisites or steps?
- Is the platform README updated with new capabilities?
- Is the Helm chart documentation updated with new values or changed defaults?
- If this introduces new self-service capabilities (new StorageClass, new Ingress class), is there documentation for how teams use it?

---

### 4. Capacity and operational baselines

- Is the capacity baseline document updated with new resource utilisation figures?
- Are capacity projections documented for planning purposes?

---

### 5. Breaking changes and migrations

If any of the following are true, a migration guide is required:

- Namespace renamed or removed
- StorageClass changed or removed (requires PVC migration)
- Ingress path or hostname changed
- Config key renamed or removed
- Service name or port changed
- RBAC policy changed in a way that removes existing access

For each breaking change:
- Is there a migration guide in the plan?
- Does it specify: what breaks, how to detect it, how to migrate, rollback path?
- Is it communicated to affected teams before the change is applied?

---

## CRITICAL RULE

- **One gap = one AskUserQuestion.** Never batch.
- Options: **A)** Add to plan now **B)** Defer to post-apply close-out **C)** Not needed.
- Bias toward adding to the plan. Platform documentation debt compounds — it becomes the tribal knowledge that makes on-call dangerous.

---

## Completion summary

```
Platform Documentation Review complete
─────────────────────────────────────────────────────
Step 0:          surface area assessed
Docs reviewed:   N rows in impact table
Gaps found:      N
  → Added to plan:            N
  → Deferred to close-out:    N
  → Confirmed not needed:     N
Breaking changes: N (migration guides required: N)
─────────────────────────────────────────────────────
Status: clean | gaps_open
```
