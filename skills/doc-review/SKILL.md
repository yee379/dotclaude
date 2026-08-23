---
name: doc-review
description: Pre-implementation documentation coverage review. Checks that every doc needing an update is explicitly called out in the plan — README, ARCHITECTURE, API docs, runbooks, CHANGELOG, ADRs, capacity baselines — before any code or cluster change is made. Works in codebase mode (application features) and platform mode (Kubernetes/infrastructure). Pairs with /codebase-closeout which executes updates post-ship. Use when asked to "check the docs plan", "documentation review", or as part of /board-review.
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
/draft-prd → /board-review (board, parallel with codebase-arch-review,
      │                     codebase-eng-review, codebase-ux-review, security-review)
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
      │                                                 │
      │   /codebase-arch-review (platform mode)         │
      │   /platform-capacity-review                     │
      │   /platform-security-review                     │
      │   /platform-ops-review                          │
      │   /platform-eng-review                          │
      │   /doc-review  ← YOU ARE HERE                   │
      └─────────────────────────────────────────────────┘
```

**The handoff (codebase mode):** this skill plans what documentation needs to change;
`/codebase-closeout` executes those changes after the code ships. Skip this review and
`codebase-closeout` has to reverse-engineer intent from a diff, losing the "why".

To run all gates automatically, use `/board-review`.

---

## Purpose

Documentation debt is created at implementation time, not at ship time. When a plan doesn't name
the docs that need updating, one of three things happens: engineers forget them entirely;
`codebase-closeout` reverse-engineers partial updates from the diff and loses intent; or docs are
updated inconsistently so README and ARCHITECTURE disagree.

This skill runs against the **plan** — before any code or cluster change — and asks one question:
*does this plan account for every piece of documentation this change touches?*

**Do NOT** make code changes, cluster changes, or doc updates now. Your job is to find gaps in the
plan's documentation coverage and get the plan to name them.

**Model routing:** scope assessment (Step 0) and impact table classification are **`haiku`-eligible**.
Gap analysis and breaking-change assessment require **`sonnet`**.

### Lane boundaries

This skill judges **coverage** — does the doc update exist as named work in the plan. Three
adjacent questions belong to other reviewers; flag and defer, do not decide them here:

| Question | Owner |
|---|---|
| Is the documentation *good* — readable, right examples, user-journey structure, troubleshooting? | `/codebase-ux-review` (dimension 3) |
| Is the plan's *terminology* right against the domain model? Should this decision become an ADR? | `/draft-prd` (Grill Mode), then `/codebase-arch-review` |
| Is the capacity *sizing* in the baseline doc correct? | `/platform-capacity-review` |

You still check that the ADR, the glossary entry, and the baseline update are **named as work** —
you just don't adjudicate their content.

---

## Subagent mode

When run inside `/board-review`, the orchestrator provides `Plan file:` and `Output file:`
(e.g. `todo/review/<slug>/round-N-dc.md`). If an output file path was given, load
`references/subagent-protocol.md` (in the `board-review` skill directory) and follow it exactly.

Checkpoints for this skill: Step 0, impact table, each review section.

Bias the safe default toward adding the doc gap to the plan. Terminology issues surface as Issues,
not questions.

## Priority hierarchy

**Codebase mode:** impact table > breaking changes > gaps > everything else.
**Platform mode:** impact table > runbook gaps > onboarding guide gaps > breaking changes > everything else.

---

## Context gathering

Before reviewing, read (if they exist):

- `CONTEXT.md` — domain glossary; the canonical terminology for this context
- `CONTEXT-MAP.md` — if present, the repo has multiple bounded contexts; find the relevant one
- `docs/adr/` — existing ADRs; note any directly relevant to the plan
- `ARCHITECTURE.md` — existing structural decisions, to avoid contradicting them
- `CLAUDE.md` — project conventions

Read-only. Creating `CONTEXT.md` and writing ADRs belongs to `/draft-prd` and
`/codebase-arch-review` — if either is missing, that absence is a gap for the plan to name.

---

## Step 0: Documentation scope assessment

**Codebase mode:**
1. **User-facing surface area?** New endpoints, commands, changed behaviour, new config options, removed features — anything a user or operator needs to know about.
2. **Internal surface area?** New services, changed architecture, new ADRs, changed deployment topology — anything a future engineer needs to understand.
3. **Breaking change?** API changes, config renames, migrations, deprecated paths. These need upgrade guides, not just doc updates.
4. **Pure internal change with no user-facing or API surface?** If yes, exit: "This change has no documentation surface. Skipping doc-review."

**Platform mode:**
1. **Operator-facing surface area?** New services to manage, new failure modes, new config options, changed procedures.
2. **Developer/user-facing surface area?** New self-service capabilities, new onboarding steps.
3. **Breaking change?** Namespace renames, StorageClass changes, ingress path changes, config key renames.
4. **Pure internal infrastructure change with no operator or user impact?** If yes, exit: "No documentation surface. Skipping doc-review."

Note that step 4 is a narrow gate: a backend refactor with no user surface still usually touches
ARCHITECTURE.md, ADRs, CLAUDE.md, or a runbook. Exit only if *nothing* in the impact table applies.

---

## Documentation impact table

**Mandatory.** Load `references/impact-tables.md` and fill in the table for the detected mode.

Any row that is **AFFECTED: yes** and **IN PLAN?: no** is a gap. Surface each gap individually.

---

## Review sections — Codebase mode

> **Platform mode:** load `references/platform-mode.md` and follow P1–P5 instead of the four
> sections below.

### 1. User-facing documentation

- Does the plan update README with new features, changed behaviour, or removed options?
- Does the plan update CHANGELOG with a user-forward entry ("You can now X", not "Refactored Y")?
- API changes: are new/changed/removed endpoints documented? Request/response schemas updated?
- CLI or config changes: are all new flags, options, and environment variables documented?
- Breaking changes: is there an upgrade guide or migration section in the plan?

**STOP.** One gap, one question.

### 2. Internal / architectural documentation

- Does the plan update ARCHITECTURE.md for new services, changed boundaries, or new data flows?
- Does the plan name the ADRs that need writing? Check against ADRs `/codebase-arch-review`
  already generated — don't duplicate, but do identify gaps.
- New Kubernetes workloads or infrastructure: is CLAUDE.md updated with new commands or setup steps?
- Changes to dev setup or contributor workflow: is CONTRIBUTING.md updated?
- New failure modes or alert conditions: is the runbook updated?

**STOP.** One gap, one question.

### 3. Inline documentation and diagrams

- Does the plan identify which code files need new or updated inline comments?
- Complex new logic: are ASCII diagram comments called out as implementation work?
- Files with existing ASCII diagrams that this change touches: does the plan note those diagrams
  must be reviewed for accuracy?

Stale inline diagrams are worse than none — they actively mislead. If the plan touches files with
known diagrams, reviewing them must be explicit work, not an afterthought.

**STOP.** One gap, one question.

### 4. Breaking changes and migrations

A dedicated upgrade guide is required — a CHANGELOG entry alone is not sufficient — if any of
these is true:

- Public API endpoint removed or signature changed
- Config key renamed or removed
- Database migration required
- CLI flag renamed or removed
- Behaviour change that silently affects existing users
- Auth or permission model changed

For each breaking change: is the upgrade guide in the plan, does it specify **what breaks, how to
detect it, how to migrate, and the rollback path**, and is it flagged in CHANGELOG under a
`### Breaking changes` heading?

**STOP.** One gap, one question.

---

## CRITICAL RULE — How to ask questions

- **One gap = one `AskUserQuestion` call.** Never batch.
- Describe it concretely: which doc, what is missing, what a user or engineer would be without it.
- Options: **A)** add to plan now **B)** defer to `codebase-closeout` / post-apply close-out
  **C)** not needed — with the reason.
- State your recommendation. **Bias toward A:** deferred documentation often never happens.
- Platform runbook gaps are **always** option A.
- **Escape hatch:** if a section has no gaps, say so and move on.

---

## Required outputs

| Output | Content |
|---|---|
| Documentation impact table | Mandatory. Every affected doc has a concrete "what changes" entry. |
| Plan amendments | Per accepted gap, exactly what to add and where, in imperative task form: "Update ARCHITECTURE.md: add the ingestion service to the component diagram and describe its data ownership." |
| Deferred to close-out | Items deferred rather than added, so `codebase-closeout` knows to look for them. |
| NOT in scope | Documentation considered and explicitly ruled out, one line of rationale each. |

---

## Completion summary

```
Documentation Review complete — Mode: Codebase | Platform
─────────────────────────────────────────────────────
Step 0:           surface area assessed — user/operator-facing: Y/N,
                  internal: Y/N, breaking: Y/N
Docs reviewed:    N rows in impact table
Gaps found:       N
  → Added to plan:            N
  → Deferred to close-out:    N
  → Confirmed not needed:     N
Breaking changes: N (upgrade/migration guides required: N)
Deferred to other reviewers: N (doc quality → ux, terminology/ADRs → arch)
─────────────────────────────────────────────────────
Status: clean | gaps_open
```
