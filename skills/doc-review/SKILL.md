---
name: doc-review
description: Pre-implementation documentation planning review. Challenges plan terminology against the domain model, then checks that every doc needing an update is explicitly called out in the plan — README, ARCHITECTURE, API docs, runbooks, CHANGELOG, ADRs, capacity baselines — before any code or cluster change is made. Works in codebase mode (application features) and platform mode (Kubernetes/infrastructure). Pairs with /codebase-closeout which executes updates post-ship. Use when asked to "check the docs plan", "documentation review", or as part of /board-review or /board-review.
---

# Documentation Review

## Mode detection

**At the start of every run, determine the review mode:**

- **Platform mode** — activate when the plan/task file contains any of: `namespace`, `Helm`, `cluster`, `vcluster`, `NetworkPolicy`, `StorageClass`, `PVC`, `node pool`, `Ingress`, `HelmRelease`, `kustomize`, `GitOps`, or is sourced from `platform/` or `todo/` with a platform prefix.
- **Codebase mode** — all other cases.

State the detected mode: `> Mode: Platform` or `> Mode: Codebase`.

---

## Workflow position

**Codebase mode:**
```
/draft-prd → /board-review (board, parallel with codebase-arch-review, codebase-eng-review, security-review)
      │
      ▼
/doc-review ← YOU ARE HERE: documentation planning gate
      │
      ▼
implementation → /codebase-closeout → /prod-release
```

**Platform mode:**
```
/draft-prd
      │
      ▼
/board-review ──── runs these reviewers in parallel ────┐
      │                                                     │
      │   /codebase-arch-review (platform mode)             │
      │   /platform-capacity-review                         │
      │   /platform-security-review                         │
      │   /platform-ops-review                              │
      │   /platform-eng-review                              │
      │   /doc-review  ← YOU ARE HERE                       │
      └─────────────────────────────────────────────────────┘
```

**The handoff (codebase mode):** This skill plans what documentation needs to change. `/codebase-closeout` executes those changes after the code ships. If this review is skipped, `codebase-closeout` has to reverse-engineer intent from a diff and will miss context and the "why" behind changes.

To run all gates automatically, use `/board-review` or `/board-review`.

---

## Purpose

Documentation debt is created at implementation time, not at ship time. When a plan doesn't name the docs that need updating, one of three things happens:

1. Engineers forget to update them entirely
2. `codebase-closeout` reverse-engineers partial updates from the diff, losing intent
3. Docs are updated inconsistently — README says one thing, ARCHITECTURE says another

This skill runs against the **plan** — before any code or cluster change — and asks: *does this plan account for every piece of documentation this change touches?*

**Model routing:** Documentation scope assessment (Step 0) and impact table classification are **`haiku`-eligible**. Gap analysis, breaking change assessment, and domain grilling require **`sonnet`**.

Do NOT make code changes. Do NOT make cluster changes. Do NOT update docs now. Your job is to identify gaps in the plan's documentation coverage and ensure the plan names them.

---

## Subagent mode

When this skill runs inside `/board-review` or `/board-review` the orchestrator will provide:
- `Plan file:` — path to read from disk
- `Output file:` — path to write findings to (e.g. `todo/review/<slug>/round-N-dc.md`)

**If an output file path was provided, follow this protocol exactly:**

1. **Write the skeleton first** — before any analysis, create the output file:
   ```
   ## Summary
   _(written last)_

   ## Issues
   _(in progress)_

   ## Decisions Required
   _(in progress)_

   ## Amendments
   _(in progress)_

   ## Status
   IN PROGRESS
   ```

2. **Write after every section** — after completing each section (Step 0, impact table, each review section):
   - Append new gaps/issues to `## Issues`
   - Append any Decisions Required entries
   - Append any plan amendments made
   - Do NOT wait until the end — write each section's findings immediately

3. **Suppress AskUserQuestion** — do not call AskUserQuestion. For every decision point write a structured `### Decision:` entry in `## Decisions Required` and continue with the best safe default (bias toward adding the doc gap to the plan).

4. **Write ## Summary and final ## Status last** — replace the _(written last)_ placeholder only after all sections are complete. Set ## Status to PASS | PASS WITH WARNINGS | FAIL.

5. **Domain grilling is suppressed in subagent mode** — proceed directly to Step 0. Terminology issues found during review are surfaced as Issues, not interactive questions.

---

## Priority hierarchy

**Codebase mode:** Documentation impact table > Breaking changes > Gaps > Everything else.

**Platform mode:** Documentation impact table > Runbook gaps > Onboarding guide gaps > Breaking changes > Everything else.

---

## Context gathering

Before reviewing, read (if they exist):
- `CONTEXT.md` — domain glossary; canonical terminology for this codebase context
- `CONTEXT-MAP.md` — if present, the repo has multiple bounded contexts; find the relevant one and its `docs/adr/`
- `docs/adr/` — existing ADRs; note any directly relevant to the plan
- `ARCHITECTURE.md` — existing structural decisions to avoid contradicting
- `CLAUDE.md` — project conventions

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term resolves. If no `docs/adr/` exists, create it when the first ADR is needed.

---

## Domain grilling — standalone mode only

> **Skip this section entirely in subagent mode.** Terminology issues found during the rest of the review are surfaced as Issues, not interactive questions.

Before producing the impact table, stress-test the plan against the domain model. If the plan's language is wrong, any documentation it produces will be wrong too.

**Process:** Interview the user relentlessly about every aspect of the plan until you reach a shared understanding. Ask questions **one at a time**, waiting for each answer before continuing. Provide your recommended answer with each question. If a question can be answered by exploring the codebase, explore it instead of asking.

**What to challenge:**
- **Glossary conflicts** — when the plan uses a term that conflicts with `CONTEXT.md`, call it out immediately: *"Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"*
- **Fuzzy language** — when the plan uses vague or overloaded terms, propose a precise canonical term: *"You're saying 'account' — do you mean the Customer or the User? Those are different things in your domain."*
- **Concrete scenarios** — stress-test domain relationships with specific edge-case scenarios that force precision about concept boundaries
- **Code contradictions** — when the plan states how something works, check whether the code agrees; surface contradictions: *"Your plan says partial cancellation is possible, but the code only cancels entire Orders — which is right?"*

**Update `CONTEXT.md` inline** — when a term resolves during grilling, update `CONTEXT.md` immediately. Do not batch. `CONTEXT.md` is a glossary and nothing else — no implementation details, no specs, no scratch work.

**ADR discipline** — only offer to create an ADR when all three are true:
1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **Result of a real trade-off** — there were genuine alternatives and one was chosen for specific reasons

If any of the three is missing, skip the ADR.

---

## Step 0: Documentation scope assessment

**Codebase mode:**
1. **What is the user-facing surface area?** New endpoints, new commands, changed behaviour, new config options, removed features — anything a user or operator would need to know about.
2. **What is the internal surface area?** New services, changed architecture, new ADRs, changed deployment topology — anything a future engineer would need to understand.
3. **Is there a breaking change?** API changes, config renames, migration requirements, deprecated paths. Breaking changes require upgrade guides, not just doc updates.
4. **Is this a pure internal/infra change with no user-facing or API surface?** If yes, exit: "This change has no documentation surface. Skipping doc-review."

**Platform mode:**
1. **What is the operator-facing surface area?** New services to manage, new failure modes, new config options, changed operational procedures.
2. **What is the developer/user-facing surface area?** New self-service capabilities, new onboarding steps, new things teams need to know.
3. **Is there a breaking change?** Namespace renames, StorageClass changes, ingress path changes, config key renames.
4. **Is this a pure internal infrastructure change with no operator or user impact?** If yes, exit: "No documentation surface. Skipping doc-review."

Do not proceed to the impact table if Step 0 concludes there is nothing to document.

---

## Documentation impact table

**Codebase mode:**
```
DOC                  | AFFECTED? | WHAT CHANGES                    | IN PLAN?
---------------------|-----------|----------------------------------|----------
README.md            | yes/no/—  | [what specifically changes]      | yes/no/n-a
ARCHITECTURE.md      | yes/no/—  | [what specifically changes]      | yes/no/n-a
CONTRIBUTING.md      | yes/no/—  | [what specifically changes]      | yes/no/n-a
CLAUDE.md            | yes/no/—  | [what specifically changes]      | yes/no/n-a
API docs             | yes/no/—  | [endpoints added/changed/removed]| yes/no/n-a
CHANGELOG.md         | yes/no/—  | [user-facing entry needed]       | yes/no/n-a
ADRs                 | yes/no/—  | [decisions to record]            | yes/no/n-a
CONTEXT.md           | yes/no/—  | [new/changed domain terms]       | yes/no/n-a
Runbook / on-call    | yes/no/—  | [new failure modes, new alerts]  | yes/no/n-a
Upgrade guide        | yes/no/—  | [breaking changes, migrations]   | yes/no/n-a
Inline code comments | yes/no/—  | [ASCII diagrams, complex logic]  | yes/no/n-a
Other: ___           | yes/no/—  | [specify]                        | yes/no/n-a
```

**Platform mode:**
```
DOC                           | AFFECTED? | WHAT CHANGES                        | IN PLAN?
------------------------------|-----------|--------------------------------------|----------
ARCHITECTURE.md (cluster)     | yes/no/—  | [cluster topology changes]           | yes/no/n-a
Runbook: <service>            | yes/no/—  | [new failure modes, procedures]      | yes/no/n-a
Onboarding guide              | yes/no/—  | [new steps, new prerequisites]       | yes/no/n-a
Platform README               | yes/no/—  | [new capabilities, changed setup]    | yes/no/n-a
ADRs                          | yes/no/—  | [infrastructure decisions to record] | yes/no/n-a
CONTEXT.md                    | yes/no/—  | [new/changed platform domain terms]  | yes/no/n-a
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

**"—"** means not applicable for this project or change type.
**"IN PLAN?"** means: does the plan explicitly call out this doc update as work to be done?

Any row that is **AFFECTED: yes** and **IN PLAN?: no** is a gap. Surface each gap individually.

---

## Review sections — Codebase mode

### 1. User-facing documentation

For any change that affects what users see, do, or configure:

- Does the plan update README with new features, changed behaviour, or removed options?
- Does the plan update CHANGELOG with a user-forward entry ("You can now X" not "Refactored Y")?
- For API changes: are new/changed/removed endpoints documented? Are request/response schemas updated?
- For CLI or config changes: are all new flags, options, and environment variables documented?
- For breaking changes: is there an upgrade guide or migration section in the plan?

**STOP.** For each gap, raise it individually. State what is missing, what the user impact is if it ships undocumented, and whether it should be added to the plan or deferred to `codebase-closeout`. Only use AskUserQuestion when there is a genuine decision (e.g. whether a breaking change warrants a standalone upgrade guide vs a CHANGELOG note).

---

### 2. Internal / architectural documentation

For any change that affects how the system is structured or operated:

- Does the plan update ARCHITECTURE.md for new services, changed component boundaries, or new data flows?
- Are new ADRs called out in the plan for significant decisions made during implementation? (Check against ADRs already generated by `codebase-arch-review` — don't duplicate, but identify any gaps.)
- For new Kubernetes workloads or infrastructure: is CLAUDE.md updated with new commands, scripts, or setup steps?
- For changes to the dev setup or contributor workflow: is CONTRIBUTING.md updated?
- For new failure modes or alert conditions: is the runbook updated?

**STOP.** One AskUserQuestion per gap. Only proceed after all gaps are resolved.

---

### 3. Inline documentation and diagrams

- Does the plan identify which code files will need new or updated inline comments?
- For complex new logic: are ASCII diagram comments called out as part of the implementation work?
- For any files with existing ASCII diagrams that this change touches: does the plan note those diagrams must be reviewed for accuracy?

Stale inline diagrams are worse than no diagrams — they actively mislead. If the plan touches files with known diagrams, that review must be explicit work, not an afterthought.

**STOP.** One AskUserQuestion per gap. Only proceed after all gaps resolved.

---

### 4. Breaking changes and migrations

If any of the following are true, a dedicated upgrade guide or migration section is required — a CHANGELOG entry alone is not sufficient:

- Public API endpoint removed or signature changed
- Config key renamed or removed
- Database migration required
- CLI flag renamed or removed
- Behaviour change that silently affects existing users
- Auth or permission model changed

For each breaking change identified:
- Is there an upgrade guide section in the plan?
- Does it specify: what breaks, how to detect it, how to migrate, and what the rollback path is?
- Is the breaking change flagged in CHANGELOG under a `### Breaking changes` heading?

**STOP.** One AskUserQuestion per gap.

---

## Review sections — Platform mode

### P1. Runbook coverage (highest priority)

- Is there a runbook section for every new failure mode introduced?
- Does the runbook cover restart, rollback, and scaling procedures?
- If an existing runbook is invalidated by this change, is the update called out in the plan?
- Is the runbook linked from the monitoring dashboard?

**STOP.** One AskUserQuestion per runbook gap — these directly affect on-call safety.

---

### P2. Architecture and topology documentation

- Is `ARCHITECTURE.md` updated to reflect new topology?
- Are namespace strategy diagrams updated?
- Is the network topology diagram updated?
- Are new ADRs called out in the plan for significant decisions?

**STOP.** One AskUserQuestion per gap.

---

### P3. Onboarding and operator documentation

- Is the application onboarding guide updated with new prerequisites or steps?
- Is the platform README updated with new capabilities?
- Is the Helm chart documentation updated with new values or changed defaults?
- If this introduces new self-service capabilities (new StorageClass, new Ingress class), is there documentation for how teams use it?

**STOP.** One AskUserQuestion per gap.

---

### P4. Capacity and operational baselines

- Is the capacity baseline document updated with new resource utilisation figures?
- Are capacity projections documented for planning purposes?

**STOP.** One AskUserQuestion per gap.

---

### P5. Breaking changes and migrations

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

**STOP.** One AskUserQuestion per gap.

---

## CRITICAL RULE — How to ask questions

- **One gap = one AskUserQuestion call.** Never batch.
- Describe concretely: which doc, what is missing, what a user or engineer would be missing without it.
- Present options: **A)** Add to plan now **B)** Defer to `codebase-closeout` / post-apply close-out **C)** Not needed — here's why.
- State your recommendation and why. Bias toward adding to the plan: deferred documentation is documentation that often never happens.
- Platform runbook gaps are **always** option A — do not defer runbook updates.
- **Escape hatch:** If a section has no gaps, say so and move on.

---

## Required outputs

### Documentation impact table
Mandatory. Produced in Step 0 and refined during review. Every affected doc must have a clear "what changes" entry by the end.

### Plan amendments
For each gap the user agrees to add to the plan: state exactly what should be added and where. Write it in imperative form as a task: "Update ARCHITECTURE.md: add new ingestion service to component diagram and describe its data ownership."

### "Deferred to close-out" list
Items the user chose to defer rather than add to the plan. Noted so `codebase-closeout` knows to look for them.

### "NOT in scope" section
Documentation considered and explicitly decided as not needed, with one-line rationale.

---

## Completion summary

**Codebase mode:**
```
Documentation Review complete
─────────────────────────────────────────────────────
Step 0:          surface area assessed — user-facing: Y/N, internal: Y/N, breaking: Y/N
Docs reviewed:   N rows in impact table
Gaps found:      N
  → Added to plan:            N
  → Deferred to close-out:    N
  → Confirmed not needed:     N
Breaking changes: N (upgrade guides required: N)
─────────────────────────────────────────────────────
Status: clean | gaps_open
```

**Platform mode:**
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
