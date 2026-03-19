---
name: project-management
description: Institutional knowledge management via a todo/ directory. Tracks features and tasks as individual markdown files with a TODO.md priority index, linking planning artefacts to git branches, commits, and PRs so context is never lost between sessions. Covers planning, picking the next item, implementing, and closing tickets.
---

# Project Management

Maintain a `todo/` directory as a prioritised backlog where every item is a first-class document — not a ticket stub, but a complete record of the problem, the design, the decisions made, and the outcome. The goal: any item can be picked up cold, implemented correctly, and shipped without reconstructing context from scratch.

## When to Activate

- Starting a new feature or task
- When asked "what should we work on next?" or "what's left to do?"
- After running `/feature-plan` or any design/planning skill — persist the output
- When picking up work that was started in a previous session
- When a task is completed and needs closing out
- When asked to add a new item to the backlog
- When context needs to be handed off or reviewed
- When asked to "log this", "track this task", "update the todo", or "show me project status"

---

## The `todo/` Directory Structure

```
todo/
├── TODO.md                          ← priority index (source of truth)
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
| 001 | User authentication           | 🔴 P0      | ✅ Done         | feat/user-auth         | #42  |
| 002 | Photo upload                  | 🟠 P1      | 🔄 In Progress  | feat/photo-upload      | #51  |
| 003 | Billing integration           | 🟡 P2      | ⬜ Open         | —                      | —    |
| 004 | Search refactor               | 🔵 P3      | ⬜ Open         | —                      | —    |

**Summary:** 1 done · 1 in progress · 2 open

## Priority Key
- 🔴 P0 Critical — blocking, do immediately
- 🟠 P1 High — high value, do soon
- 🟡 P2 Medium — worth doing, schedule it
- 🔵 P3 Low — nice to have

## Status Key
- ⬜ Open — not started
- 🔄 In Progress — active development
- 👀 In Review — PR open, awaiting merge
- ✅ Done — merged to main
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

## Relationship to Other Tasks

Which items does this depend on, unblock, or interact with?

- **#001 (User Auth):** Must be shipped before photo upload — auth required to associate photos with users.
- **#003 (Billing):** Independent, no dependency.
```

---

## Workflow

### Picking the Next Item

1. Read `todo/TODO.md` in full
2. Find the highest-priority `⬜ Open` item (P0 before P1 before P2 before P3)
3. Read its full task file — understand the problem before the plan
4. Ask: are there open questions that need answering first?
5. If yes → resolve them (update the file) before touching code
6. If no → create the branch and start the implementation checklist

```bash
git checkout -b feat/<slug>
```

### Starting a New Task

1. Check `todo/TODO.md` — what's the next available number?
2. Create `todo/<number>-<slug>.md` from the template above
3. Fill in at minimum: Problem Statement and Goals
4. **Add a row to `todo/TODO.md` immediately** — priority, status `⬜ Open`, branch `—`, PR `—`
5. Create a git branch: `feat/<slug>` (or `fix/<slug>` for bugs)
6. **Update `todo/TODO.md`** — set Branch to `feat/<slug>`, status to `🔄 In Progress`
7. If this is a planned feature, run `/feature-plan` and paste or link the output into the task file's **Design** section

### Planning a Task

When asked to plan an item (or when the design section is thin):

1. Read the problem statement carefully
2. Explore the codebase — find every file the change touches
3. Draft the Design and Implementation Plan sections in the task file
4. Add Open Questions for anything that requires a decision
5. Present the plan for approval before writing code

The task file *is* the plan. Don't maintain a separate plan document unless the design is complex enough to warrant a linked deep-dive.

### During Development

- **After hitting a problem** — add a `### Problem:` entry to Problems & Solutions immediately. Don't wait until the end; you'll forget the details.
- **If you encounter a design problem not anticipated in the plan** — update the Design section before continuing. Don't silently deviate.
- **Tick checklist items as they complete** — don't batch-tick at the end.
- **At the end of a session** — update the task checklist and status field. Future-you (or a teammate) should be able to resume without a handoff conversation.
- **When context window gets large** — write your current understanding into the task file before starting a fresh session. This is your external memory.

### Opening a PR

1. Update the task file:
   - Set `**PR:**` to the PR number/URL
   - Set `**Status:**` to `👀 In Review`
2. Update `todo/TODO.md` — status and PR column
3. Reference the task file in the PR description:

```markdown
## Context
See [todo/002-photo-upload.md](todo/002-photo-upload.md) for full design,
decisions, and known issues.
```

### Closing a Task

When implementation is complete:

1. Tick all checklist items in the task file
2. Change `**Status:**` to `✅ Done` and `**Shipped:**` to today's date
3. Update `todo/TODO.md` — flip status, update summary count
4. Commit everything together:

```bash
git add src/ tests/ docs/ todo/
git commit -m "feat: <title> (TODO #<n>)"
```

The task file is **never deleted** — it becomes a permanent record.

### Adding a New TODO (Backlog Item)

1. Pick the next available number from `todo/TODO.md`
2. Create `todo/<n>-<slug>.md` with the template above
3. Fill in at minimum: Problem Statement and Goals
4. Assign a priority tier (P0–P3)
5. Add a row to `todo/TODO.md` with priority and status `⬜ Open`
6. Commit: `git add todo/ && git commit -m "docs(todo): add #<n> <title>"`

### Reviewing the Backlog

When asked "what should we work on next?" or "what can get us out of alpha/beta?":

1. Read `todo/TODO.md` in full
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

`todo/TODO.md` is the single source of truth for project status. It must be updated **as part of the same action** that changes a task — never as a follow-up.

### When to update TODO.md

| Trigger | What to update |
|---------|---------------|
| New task created | Add row with priority, status ⬜, branch `—`, PR `—` |
| Task moves to In Progress | Status → 🔄, Branch → `feat/<slug>` |
| PR opened | Status → 👀, PR → `#<number>` |
| PR merged | Status → ✅, note shipped date in task file |
| Task cancelled | Status → ❌, add reason in task file |
| Branch renamed or PR number changes | Update Branch/PR columns immediately |

### TODO.md sync check

Before ending any session that touched task files, verify TODO.md is in sync:

1. Open `todo/TODO.md`
2. For each task file that was created or modified this session, confirm the row matches the current state of the task file
3. If any row is stale — wrong status, missing branch, missing PR — update it now
4. If a task file exists with no corresponding TODO.md row, add it

**TODO.md must never lag the task files.** A task file updated to `🔄 In Progress` with no corresponding TODO.md update is a broken index.

### TODO.md health check

When asked "what are we working on?" or "show me project status", always read `todo/TODO.md` first — not individual task files. If TODO.md appears stale (tasks in progress with no branch, shipped tasks still showing as in-review), run the sync check above before reporting status.

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
10. **Link, don't duplicate.** If `/feature-plan` produced a detailed doc, link to it rather than copying it. The task file is the hub, not the whole archive.

---

## Integration with Other Skills

| Skill | How it integrates |
|-------|------------------|
| `/feature-plan` | Run first; paste or link the output into the task file's **Design** section |
| `/full-review` | Run the review pipeline against the design before starting implementation |
| `/deep-research` | Research findings saved to `todo/research/<slug>/`; linked from task file |
| `/code-review` | Review findings that require fixes become new task checklist items or new backlog items |
| `/security-review` | Security gaps discovered become P0/P1 backlog items |
| `/document-release` | After shipping, reference the task file as the source of truth for CHANGELOG entries |
