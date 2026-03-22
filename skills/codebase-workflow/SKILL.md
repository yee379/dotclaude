---
name: codebase-workflow
description: Institutional knowledge management via a todo/ directory. Tracks features and tasks as individual markdown files with a TODO.md priority index, linking planning artefacts to git branches, commits, and PRs so context is never lost between sessions. Covers planning, picking the next item, implementing, and closing tickets.
---

# Project Management

Maintain a `todo/` directory as a prioritised backlog where every item is a first-class document — not a ticket stub, but a complete record of the problem, the design, the decisions made, and the outcome. The goal: any item can be picked up cold, implemented correctly, and shipped without reconstructing context from scratch.

## When to Activate

- Starting a new feature or task
- When asked "what should we work on next?" or "what's left to do?", "what to do with todo <number>?", "tell me more about todo <number>?", "what is the plan for todo <number>?"
- After running `/plan-draft` or any design/planning skill — persist the output
- When picking up work that was started in a previous session
- When a task is completed and needs closing out
- When asked to add a new item to the backlog
- When context needs to be handed off or reviewed
- When asked to "log this", "track this task", "update the todo", or "show me project status"

---

## The `todo/` Directory Structure

```
TODO.md                          ← priority index (source of truth)
todo/
├── 001-user-authentication.md
├── 002-photo-upload.md
├── 003-billing-integration.md
└── 004-search-refactor.md
```

### TODO.md — The Priority Index

The index groups items by priority tier and shows status, branch, and PR at a glance:

```markdown
# Project Tasks

| #   | Title                         | Priority   | Status          | Branch                 | PR   |
|-----|-------------------------------|------------|-----------------|------------------------|------|
| [001](todo/001-user-authentication.md) | User authentication | 🔴 P0 | ✅ Done | feat/user-auth | #42  |
| [002](todo/002-photo-upload.md) | Photo upload        | 🟠 P1 | 🔄 In Progress | feat/photo-upload | #51 |
| [003](todo/003-billing-integration.md) | Billing integration | 🟡 P2 | ⬜ Open | —             | —    |
| [004](todo/004-search-refactor.md) | Search refactor     | 🔵 P3 | ⬜ Open         | —              | —    |

**Summary:** 1 done · 1 in progress · 2 open

> The `#` column must always be a markdown link to the task file:
> `[001](todo/001-slug.md)` — never a bare number.

## Priority Key
- 🔴 P0 Critical — blocking, do immediately
- 🟠 P1 High — high value, do soon
- 🟡 P2 Medium — worth doing, schedule it
- 🔵 P3 Low — nice to have

## Status Key
- 📋 Preparing — task created, plan-draft not yet run
- ⬜ Open — plan-draft complete, awaiting /plan-board-review
- 🔎 In Review — plan-board-review board is actively running
- 🔍 Reviewed — plan approved by plan-board-review board, ready to implement
- 🔄 In Progress — active development
- 🏁 Implementation Done — code complete, PR not yet raised
- 👀 PR Open — PR raised, awaiting code review and merge
- ✅ Merged — merged to main, not yet deployed
- 🚀 Deployed — live in production
- ❌ Won't Do — cancelled, reason noted in task file
```

### Individual Task Files — `<number>-<slug>.md`

Numbering is sequential and never reused. The slug is kebab-case, max 5 words. Examples:
- `001-user-authentication.md`
- `002-photo-upload.md`
- `015-fix-checkout-race-condition.md`

---

## Task File Format

Each task file is a living document. It starts with a problem statement and grows as design and implementation decisions are made.

```markdown
# TODO #<N> — <Feature / Task Title>

> **Priority:** 🟡 P2 — Medium
> **Status:** 🔄 In Progress
> **Branch:** `feat/<slug>`
> **PR:** #<number> (or — if not yet raised)
> **Created:** YYYY-MM-DD
> **Shipped:** — (filled when merged)

---

## Problem Statement

What is wrong or missing today? Show the current (broken) flow.
Include concrete examples of what fails, leaks, or is missing.
Don't describe the solution here — describe the pain.

### What fails today

| Scenario | Current behaviour | Desired behaviour |
|----------|-------------------|-------------------|
| Backend down | Raw IP leaked to LLM | Safe message returned |

---

## Goals

Numbered list of what Done looks like. Each goal should be independently verifiable.

1. Operators see everything — raw errors preserved in logs
2. LLM sees only safe, actionable messages
3. Every sanitisation rule has a unit test

## Non-Goals

What this task deliberately does not do. Prevents scope creep.

---

## Design

### Architecture

Where does the fix live and why? One diagram is worth a page of prose.

```
GraphQLClient.execute()
    ├── except TransportQueryError:
    │       LOG.error(raw)                    ← operators see everything
    │       raise CoactAPIError(safe_msg)     ← LLM sees nothing internal
```

### Key Decisions

Record every "we chose X over Y because Z" as you design.

---

## Implementation Plan

Ordered steps. Concrete enough that a fresh pair of hands could execute.

### Step 1 — <file>
What changes and why.

### Step 2 — <file>
...

---

## Implementation Checklist

- [ ] Step 1 done
- [ ] Step 2 done
- [ ] Tests written and passing
- [ ] Docs updated

---

## Problems & Solutions

<!-- The most valuable section. Add entries as you hit walls. -->

### Problem: S3 presigned URLs expire before upload completes on slow connections
**Encountered:** 2026-03-15
**Root cause:** Default 15-minute TTL too short for large files on mobile
**Solution:** Increased TTL to 2 hours; added client-side retry with fresh URL on 403
**Lesson:** Always test with throttled connections before shipping upload flows

---

## Open Questions

Questions that must be answered before or during implementation.
Include a recommended answer so they can be resolved quickly.

1. **Should X or Y?** — Recommendation: X, because Z.

---

## Board Review

> *Populated by `/plan-board-review` after the board completes. Do not fill manually.*

**Verdict:** CLEAR TO BUILD | CLEAR WITH WARNINGS | BLOCKED | UNSTABLE
**Date:** YYYY-MM-DD
**Rounds:** N

| Reviewer | Result | Amended | Key findings |
|---|---|---|---|
| research-handbook | — | — | — |
| plan-arch-review | — | — | — |
| plan-eng-review | — | — | — |
| plan-doc-review | — | — | — |
| security-review | — | — | — |

**Accepted warnings:** none
**ADRs written:** 0

---

## Relationship to Other Tasks

Which items does this depend on, unblock, or interact with?

- **#001 (User Auth):** Must be shipped before photo upload — auth required to associate photos with users.
- **#003 (Billing):** Independent, no dependency.
```

---

## Workflow

### Picking the Next Item

**If the user names a task number** (e.g. "work on 027", "tell me about #3", "what's the plan
for 012"): read `todo/<number>-*.md` directly — glob `todo/027-*.md` and open the first match.
Do not search `TODO.md` or the codebase first; the file is always at that path.

1. Read `TODO.md` in full
2. Find the highest-priority `⬜ Open` or `🔍 Reviewed` item (P0 before P1 before P2 before P3)
3. Read its full task file — understand the problem before the plan
4. Ask: are there open questions that need answering first?
5. If yes → resolve them (update the file) before touching code
6. If no → create the branch, then **immediately** update both files:
   - In the task file: set `**Status:**` to `🔄 In Progress` and `**Branch:**` to `feat/<slug>`
   - In `TODO.md`: set status → `🔄`, Branch → `feat/<slug>`

```bash
git checkout -b feat/<slug>
```

### Starting a New Task

1. Check `TODO.md` — what's the next available number?
2. Create `todo/<number>-<slug>.md` from the template above
3. Fill in at minimum: Problem Statement and Goals
4. **Add a row to `TODO.md` immediately** — priority, status `📋 Preparing`, branch `—`, PR `—`
5. **Before touching code, ask:**
   > "Task #N is ready to plan. Shall I run `/plan-draft` now to flesh out the design,
   > or would you like to add more context to the Problem Statement first?"
   - If the user confirms → run `/plan-draft` immediately.
   - If the user wants to add context first → wait, then run `/plan-draft` once ready.
   - The only exception: genuinely trivial tasks where the fix is a single obvious change
     (e.g. "add a 30s timeout to one function"). Even then, say so explicitly:
     > "This looks trivial enough to skip plan-draft — proceeding directly. Let me know
     > if you'd like a full plan instead."
6. **Once `/plan-draft` completes:** set status to `⬜ Open` in both the task file and
   `TODO.md`. Then ask:
   > "Plan is written. Shall I run `/plan-board-review` now to gate it through the board?"
7. Only after `/plan-board-review` gives CLEAR TO BUILD (status → `🔍 Reviewed`): create the branch
   and begin implementation (status → `🔄 In Progress`).

### Planning a Task

When a task file exists but the Design section is empty or sparse, **do not start
implementation.** Ask first:

> "The design section for #N is sparse. Shall I run `/plan-draft` now to flesh it out
> before we start building?"

- If yes → run `/plan-draft`, then ask about `/plan-board-review`.
- If the user wants to add context first → wait, then proceed.
- Never silently skip to code.

1. **Read the task file first** — always start here, never from a blank slate. The problem
   statement and goals are already written (by `/todo-scout`, manually, or from a previous
   session). Do not re-derive them; build on what's there.
2. **Run `/plan-draft`** to fill in the design — it will read the task file's Problem
   Statement and Goals as its Phase 1 input, skipping the problem-identification step.
   All output (requirements, architecture, ADRs, delivery slices) gets written back into
   the task file's **Design** and **Implementation Plan** sections.
3. **Research first if needed** — if the Design section is empty *and* the technology is
   unfamiliar, run `/research-handbook` or `/search-first` before calling `/plan-draft`.
   Save findings to `todo/research/<slug>/` and link from the task file's Design section.
4. Add Open Questions for anything that requires a decision before implementation starts.
5. Present the plan for approval before writing code.
6. Once approved, run `/plan-board-review` to gate the design before implementation begins.

**Task file origin → next step:**

| Where the task file came from | Status | Next step |
|-------------------------------|--------|-----------|
| `/todo-scout` | 📋 Preparing | Problem Statement already written — run `/plan-draft` directly |
| Added manually (thin) | 📋 Preparing | Fill Problem Statement first, then run `/plan-draft` |
| Previous session (partial design) | 📋 Preparing | Resume `/plan-draft` from where the Design section left off |
| `/plan-draft` already run | ⬜ Open | Design is complete — run `/plan-board-review` |
| `/plan-board-review` passed | 🔍 Reviewed | CLEAR TO BUILD — create branch, begin implementation |

The task file *is* the plan. Don't maintain a separate plan document unless the design is
complex enough to warrant a linked deep-dive.

### During Development

- **After hitting a problem** — add a `### Problem:` entry to Problems & Solutions immediately. Don't wait until the end; you'll forget the details.
- **If you encounter a design problem not anticipated in the plan** — update the Design section before continuing. Don't silently deviate.
- **Tick checklist items as they complete** — don't batch-tick at the end.
- **At the end of a session** — update the task checklist and status field. Future-you (or a teammate) should be able to resume without a handoff conversation.
- **When context window gets large** — write your current understanding into the task file before starting a fresh session. This is your external memory.

### Opening a PR

1. Update the task file:
   - Set `**Status:**` to `🏁 Implementation Done` when all checklist items are ticked
   - Set `**Status:**` to `👀 PR Open` and `**PR:**` to the PR number/URL once the PR is raised
2. Update `TODO.md` — status and PR column
3. Reference the task file in the PR description:

```markdown
## Context
See [todo/002-photo-upload.md](todo/002-photo-upload.md) for full design,
decisions, and known issues.
```

### Closing a Task

When the PR is merged:

1. Tick all checklist items in the task file
2. Change `**Status:**` to `✅ Merged` and `**Shipped:**` to today's date
3. Update `TODO.md` — flip status to `✅ Merged`, update summary count
4. Commit everything together:

```bash
git add src/ tests/ docs/ todo/
git commit -m "feat: <title> (TODO #<n>)"
```

When production deployment completes (after `/prod-release`):

5. Change `**Status:**` in the task file to `🚀 Deployed`
6. Update `TODO.md` — flip status to `🚀 Deployed`

The task file is **never deleted** — it becomes a permanent record.

### Adding a New TODO (Backlog Item)

1. Pick the next available number from `TODO.md`
2. Create `todo/<n>-<slug>.md` with the template above
3. Fill in at minimum: Problem Statement and Goals
4. Assign a priority tier (P0–P3)
5. Add a row to `TODO.md` with priority and status `📋 Preparing`
6. Commit: `git add TODO.md todo/ && git commit -m "docs(todo): add #<n> <title>"`
7. **Do not create a branch or begin implementation yet.** The next step is `/plan-draft`
   (which advances status to `⬜ Open`), then `/plan-board-review` (which advances to `🔍 Reviewed`).
   A task is not ready to implement until it has passed the board.

### Reviewing the Backlog

When asked "what should we work on next?" or "what can get us out of alpha/beta?":

1. Read `TODO.md` in full
2. Group open items by: P0 blockers → P1 high-value → P2 polish → P3 nice-to-have
3. Identify dependency chains (e.g. #001 must land before #002)
4. Suggest a sequenced roadmap with effort estimates
5. Flag any open questions in existing task files that are blocking progress

---

## Relationship to Git

The `todo/` directory and git workflow are two layers of the same system:

```
todo/<number>-<slug>.md    ←→    git branch: feat/<slug>
                                 git commits: reference the task number
                                 PR: links back to the task file
```

### Branch naming

| Task type | Branch prefix | Example |
|-----------|--------------|---------|
| New feature | `feat/` | `feat/photo-upload` |
| Bug fix | `fix/` | `fix/checkout-race-condition` |
| Refactor | `refactor/` | `refactor/search-query-layer` |
| Docs | `docs/` | `docs/api-reference` |
| Chore | `chore/` | `chore/upgrade-node-20` |

### Commit messages

Reference the task number in commits so git history links back to context:

```
feat(photo-upload): add S3 presigned URL generation [#002]
fix(photo-upload): increase presigned URL TTL to 2h [#002]
test(photo-upload): add integration tests for upload flow [#002]
```

### When to commit

Commit after each **logical unit of work** — a self-contained change that could be reviewed,
reverted, or understood on its own. Do not wait until the end of a task to commit everything.

| Situation | Commit? |
|-----------|---------|
| A passing test + the code that makes it pass | ✅ Yes — atomic TDD unit |
| A refactor with no behaviour change | ✅ Yes — its own commit, not bundled with features |
| A bug fix | ✅ Yes — immediately, with a `fix:` message explaining what broke |
| Updating `TODO.md` / task file status | ✅ Yes — same commit as the work that caused the status change |
| Adding a new task to the backlog | ✅ Yes — `docs(todo): add #<n> <title>` |
| Half-finished feature, tests failing | ❌ No — finish the unit first |
| Multiple unrelated changes bundled together | ❌ No — split into separate commits |

**One commit = one concern.** If the commit message needs "and" to describe what it does, split it.

### What to stage

Always stage files **by name**. Never use `git add -A`, `git add .`, or `git add -u` — these
risk accidentally committing secrets, build artefacts, or unrelated changes.

```bash
# Good
git add src/upload.py tests/test_upload.py

# Bad
git add -A
git add .
```

Before committing, run `git diff --cached` to verify exactly what is staged.

### PRs

A good PR description for a tracked task:

```markdown
## Summary
Implements photo upload with resize and old-photo cleanup.

## Full context
See [todo/002-photo-upload.md](todo/002-photo-upload.md) —
includes design decisions, problems encountered, and trade-offs.

## Key decisions
- Sync resize (not async) — acceptable latency, simpler ops
- Sharp with `limitInputPixels` — prevents OOM on large phone photos

## Test plan
- [ ] Upload JPEG, PNG, WebP — verify 256×256 thumbnail
- [ ] Upload > 5MB — verify 400 response
- [ ] Upload on throttled connection — verify retry on expired URL
- [ ] Upload twice — verify old photo deleted
```

---

## TODO.md Maintenance

`TODO.md` is the single source of truth for project status. It must be updated **as part of the same action** that changes a task — never as a follow-up.

### When to update TODO.md

| Trigger | What to update |
|---------|---------------|
| New task created | Add row with priority, status 📋 Preparing, branch `—`, PR `—` |
| plan-draft completes | Status → ⬜ Open in task file and TODO.md; prompt user to run /plan-board-review |
| plan-board-review starts | Status → 🔎 In Review in task file and TODO.md |
| plan-board-review passes (CLEAR TO BUILD / CLEAR WITH WARNINGS) | Status → 🔍 Reviewed; board review summary merged into task file; `todo/review/<slug>/` deleted |
| plan-board-review blocked or unstable | Status → 📋 Preparing (revert to pre-review); board review summary merged into task file; `todo/review/<slug>/` deleted; blocking issues noted in Problems & Solutions |
| Implementation starts (branch created) | Status → 🔄 In Progress in task file and TODO.md, Branch → `feat/<slug>` |
| Implementation complete (all checklist items ticked) | Status → 🏁 Implementation Done in task file and TODO.md |
| PR opened | Status → 👀 PR Open, PR → `#<number>` |
| PR merged | Status → ✅ Merged, note shipped date in task file |
| prod-release completes | Status → 🚀 Deployed |
| Task cancelled | Status → ❌, add reason in task file |
| Branch renamed or PR number changes | Update Branch/PR columns immediately |

### TODO.md sync check

Before ending any session that touched task files, verify TODO.md is in sync:

1. Open `TODO.md`
2. For each task file that was created or modified this session, confirm the row matches the current state of the task file
3. If any row is stale — wrong status, missing branch, missing PR — update it now
4. If a task file exists with no corresponding TODO.md row, add it

**TODO.md must never lag the task files.** A task file updated to `🔄 In Progress` with no corresponding TODO.md update is a broken index.

### TODO.md health check

When asked "what are we working on?" or "show me project status", always read `TODO.md` first — not individual task files. If TODO.md appears stale (tasks in progress with no branch, shipped tasks still showing as in-review), run the sync check above before reporting status.

---

## Quality Rules

1. **The problem statement comes first.** Never write the design before you can clearly describe what is broken. A well-written problem statement makes the design obvious.
2. **Open questions block implementation.** If a task has unresolved open questions, resolve them before touching code — not during.
3. **Write problems down immediately.** The value of this system is in the **Problems & Solutions** section. A task file with no problems recorded is incomplete — every non-trivial feature hits at least one wall.
4. **Non-Goals prevent scope creep.** Every task must say what it deliberately does not do.
5. **The checklist is the contract.** Every implementation step must appear in the checklist. If you did something not on the list, add it retroactively and tick it.
6. **TODO.md is updated in the same action, not as a follow-up.** A stale index is worse than no index.
7. **Never delete task files.** They are institutional memory. Cancelled tasks get `❌ Won't Do` status and a reason.
8. **One branch per task.** Don't mix unrelated work on a branch — it breaks the task ↔ branch ↔ PR traceability.
9. **Update before ending a session.** If you close your laptop without updating the task file and TODO.md, the context is gone.
10. **Link, don't duplicate.** If `/plan-draft` produced a detailed doc, link to it rather than copying it. The task file is the hub, not the whole archive.

---

## Where Standards Fit in the Workflow

A common question is where skills like `tdd-standards`, `code-standards`, `agentic-standards`,
and `twelve-factor-standards` belong. The answer: they belong in the **plan**, not the implementation.

```
plan-draft → plan-board-review → implementation → plan-closeout → prod-release
     ↑                ↑                  ↑
  standards       standards          just execute
  inform the      enforced by        the plan;
  design          plan-eng-review    standards
                  and others         already baked in
```

- **Standards** are inputs to `plan-draft` and enforced during `plan-board-review`. By the time
  you're writing code, the approach should already comply — the plan was reviewed against them.
- **`code-review`** is the implementation **exit gate** — run it before marking a task
  `🏁 Implementation Done`. It catches drift from the plan and anything the reviewers missed.
- **Implementation itself is execution** — follow the plan, tick the checklist, run `code-review`
  when done. There is no separate "implementation workflow" skill because the plan *is* the workflow.

If you find yourself wanting to apply a standard during implementation, that's a signal the plan
was underspecified — update the task file's Design section and note it in Problems & Solutions.

---

## Integration with Other Skills

| Skill | How it integrates |
|-------|------------------|
| `/todo-scout` | Run to proactively generate backlog candidates; writes task files directly into `todo/` |
| `/plan-draft` | Run first; paste or link the output into the task file's **Design** section |
| `/plan-board-review` | Run the review pipeline against the design before starting implementation |
| `/research-handbook` | Research findings saved to `todo/research/<slug>/`; linked from task file |
| `/code-review` | Review findings that require fixes become new task checklist items or new backlog items |
| `/security-review` | Security gaps discovered become P0/P1 backlog items |
| `/plan-closeout` | After shipping, close out the task file, sync TODO.md, update all docs, and polish CHANGELOG |
