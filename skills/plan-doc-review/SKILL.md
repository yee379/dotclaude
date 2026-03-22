---
name: plan-doc-review
description: Pre-implementation documentation planning review. Checks that the plan explicitly identifies every doc that needs updating — README, ARCHITECTURE, API docs, runbooks, CHANGELOG, ADRs, CONTRIBUTING — before any code is written. Pairs with /plan-closeout which applies updates post-ship. Use when asked to "check the docs plan", "what docs need updating", or "documentation review".
license: MIT
compatibility: opencode
---

# Plan Documentation Review

## Workflow position

```
/plan-draft → /plan-board-review (board, parallel with plan-arch-review, plan-eng-review, security-review)
      │
      ▼
/plan-doc-review ← YOU ARE HERE: documentation planning gate — which docs
      │                  change, what changes in each, who owns it, is it in the plan?
      ▼
/security-review → implementation → /plan-closeout → /prod-release
```

**The handoff:** This skill plans what documentation needs to change and ensures that work is called out in the plan. `/plan-closeout` executes those changes after the code ships. If this review is skipped, `plan-closeout` has to reverse-engineer intent from a diff — it will miss context, tone, and the "why" behind changes.

To run all gates in sequence automatically, use `/plan-board-review` instead of invoking each skill individually.

---

## Purpose

Documentation debt is created at implementation time, not at ship time. When a plan doesn't name the docs that need updating, one of three things happens:

1. Engineers forget to update them entirely
2. `plan-closeout` reverse-engineers partial updates from the diff, losing intent
3. Docs are updated inconsistently — README says one thing, ARCHITECTURE says another

This skill runs against the **plan** — before any code is written — and asks a single question: *does this plan account for every piece of documentation that this change touches?*

**Model routing:** The documentation impact table (Step 0) and existence checks are **`haiku`-eligible** — they are classification tasks. Sections involving breaking change analysis, upgrade guide assessment, or judging whether a doc gap is actually a gap require **`sonnet`**.

Do NOT make code changes. Do NOT start implementation. Do NOT update docs now. Your job is to identify gaps in the plan's documentation coverage and ensure the plan names them.

---

## Priority hierarchy

If you are running low on context or the user asks you to compress:
Documentation impact table > Breaking changes > Gaps > Everything else.

---

## Step 0: Documentation scope assessment

Before reviewing, answer:

1. **What is the user-facing surface area of this change?** New endpoints, new commands, changed behaviour, new config options, removed features — anything a user or operator would need to know about.

2. **What is the internal surface area?** New services, changed architecture, new ADRs, changed deployment topology — anything a future engineer would need to understand.

3. **Is there a breaking change?** API changes, config renames, migration requirements, deprecated paths. Breaking changes require upgrade guides, not just doc updates.

4. **Is this a pure internal/infra change with no user-facing or API surface?** If yes, say so explicitly and exit: "This change has no documentation surface. Skipping plan-doc-review."

Do not proceed to the review sections if Step 0 concludes there is nothing to document.

---

## Documentation impact table

Produce this table for every change. For each doc type, assess whether it is affected, and whether the plan currently accounts for the update:

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
Runbook / on-call    | yes/no/—  | [new failure modes, new alerts]  | yes/no/n-a
Upgrade guide        | yes/no/—  | [breaking changes, migrations]   | yes/no/n-a
Inline code comments | yes/no/—  | [ASCII diagrams, complex logic]  | yes/no/n-a
Other: ___           | yes/no/—  | [specify]                        | yes/no/n-a
```

**"—"** means not applicable for this project or change type.
**"IN PLAN?"** means: does the plan explicitly call out this doc update as work to be done?

Any row that is **AFFECTED: yes** and **IN PLAN?: no** is a gap. Surface each gap individually.

---

## Review sections

### 1. User-facing documentation

For any change that affects what users see, do, or configure:

- Does the plan update README with new features, changed behaviour, or removed options?
- Does the plan update CHANGELOG with a user-forward entry ("You can now X" not "Refactored Y")?
- For API changes: are new/changed/removed endpoints documented? Are request/response schemas updated?
- For CLI or config changes: are all new flags, options, and environment variables documented?
- For breaking changes: is there an upgrade guide or migration section in the plan?

**STOP.** For each gap, raise it individually. State what is missing, what the user impact is if it ships undocumented, and whether it should be added to the plan or deferred to `plan-closeout`. Only use AskUserQuestion when there is a genuine decision (e.g. whether a breaking change warrants a standalone upgrade guide vs a CHANGELOG note).

---

### 2. Internal / architectural documentation

For any change that affects how the system is structured or operated:

- Does the plan update ARCHITECTURE.md for new services, changed component boundaries, or new data flows?
- Are new ADRs called out in the plan for significant decisions made during implementation? (Check against ADRs already generated by `plan-arch-review` — don't duplicate, but identify any gaps.)
- For new Kubernetes workloads or infrastructure: is CLAUDE.md updated with new commands, scripts, or setup steps?
- For changes to the dev setup or contributor workflow: is CONTRIBUTING.md updated?
- For new failure modes or alert conditions: is the runbook updated?

**STOP.** One AskUserQuestion per gap. Only proceed after all gaps are resolved.

---

### 3. Inline documentation and diagrams

- Does the plan identify which code files will need new or updated inline comments?
- For complex new logic: are ASCII diagram comments called out as part of the implementation work?
- For any files with existing ASCII diagrams that this change touches: does the plan note that those diagrams must be reviewed for accuracy?

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

## CRITICAL RULE — How to ask questions

- **One gap = one AskUserQuestion call.** Never batch.
- Describe concretely: which doc, what is missing, what a user or engineer would be missing without it.
- Present options: **A)** Add to plan now **B)** Defer to `plan-closeout` **C)** Not needed — here's why.
- State your recommendation and why. Bias toward adding to the plan: deferred documentation is documentation that often never happens.
- **Escape hatch:** If a section has no gaps, say so and move on.

---

## Required outputs

### Documentation impact table
Mandatory. Produced in Step 0 and refined during review. Every affected doc must have a clear "what changes" entry by the end.

### Plan amendments
For each gap the user agrees to add to the plan: state exactly what should be added and where. Write it in imperative form as a task: "Update ARCHITECTURE.md: add new ingestion service to component diagram and describe its data ownership."

### "Deferred to plan-closeout" list
Items the user chose to defer rather than add to the plan. These should be noted so `plan-closeout` knows to look for them.

### "NOT in scope" section
Documentation considered and explicitly decided as not needed, with one-line rationale.

---

## Completion summary

```
Documentation Review complete
─────────────────────────────────────────────────────
Step 0:          surface area assessed — user-facing: Y/N, internal: Y/N, breaking: Y/N
Docs reviewed:   N rows in impact table
Gaps found:      N
  → Added to plan:            N
  → Deferred to doc-release:  N
  → Confirmed not needed:     N
Breaking changes: N (upgrade guides required: N)
─────────────────────────────────────────────────────
Status: clean | gaps_open
```
