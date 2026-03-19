---
name: project-management
description: Institutional knowledge management via a todo/ directory. Tracks features and tasks as individual markdown files with a README index, linking planning artefacts to git branches, commits, and PRs so context is never lost between sessions.
---

# Project Management

Maintain a living `todo/` directory that captures the full lifecycle of every feature or task — from initial planning through to shipped code — so that context, decisions, and hard-won lessons are never lost between sessions or team members.

## When to Activate

- Starting a new feature or task
- After running `/feature-plan` or any design/planning skill — persist the output
- When picking up work that was started in a previous session
- When context needs to be handed off or reviewed
- When asked to "log this", "track this task", "update the todo", or "what are we working on"

---

## The `todo/` Directory Structure

```
todo/
├── README.md                          ← index of all tasks (the source of truth)
├── 001-user-authentication.md
├── 002-photo-upload.md
├── 003-billing-integration.md
└── 004-search-refactor.md
```

### README.md — The Index

The index is a single table of every task, always up to date:

```markdown
# Project Tasks

| # | Task | Status | Branch | PR |
|---|------|--------|--------|----|
| 001 | User authentication | ✅ Shipped | feat/user-auth | #42 |
| 002 | Photo upload | 🔄 In progress | feat/photo-upload | #51 |
| 003 | Billing integration | 📋 Planned | — | — |
| 004 | Search refactor | 💡 Idea | — | — |

## Status Key
- 💡 Idea — rough concept, not yet planned
- 📋 Planned — design done, not started
- 🔄 In progress — active development
- 👀 In review — PR open, awaiting merge
- ✅ Shipped — merged to main
- ❌ Cancelled — won't do, reason noted
```

### Individual Task Files — `<number>-<slug>.md`

Numbering is sequential and never reused. The slug is kebab-case, max 5 words. Examples:
- `001-user-authentication.md`
- `002-photo-upload.md`
- `015-fix-checkout-race-condition.md`

---

## Task File Format

Each task file is a living document. It starts lean and grows as work progresses.

```markdown
# <number>: <Feature / Task Title>

**Status:** 🔄 In progress
**Branch:** feat/<slug>
**PR:** #<number> (or — if not yet raised)
**Created:** YYYY-MM-DD
**Shipped:** — (filled when merged)

## Goal

One paragraph. What problem does this solve and why does it matter?
Not "implement X" — the underlying user or system need.

## Approach

How we are solving it. Key architectural decisions, libraries chosen,
patterns used. This section grows as the design is locked in.

> Link to fuller design doc if `/feature-plan` was run:
> See [feature-plan output](../docs/feature-plan-002-photo-upload.md)

## Tasks

- [x] Scaffold upload endpoint
- [x] Add S3 integration
- [ ] Resize on upload
- [ ] Delete old photo on update
- [ ] Integration tests

## Problems & Solutions

<!-- The most valuable section. Add entries as you hit walls. -->

### Problem: S3 presigned URLs expire before upload completes on slow connections
**Encountered:** 2026-03-15
**Root cause:** Default 15-minute TTL too short for large files on mobile
**Solution:** Increased TTL to 2 hours; added client-side retry with fresh URL on 403
**Lesson:** Always test with throttled connections before shipping upload flows

### Problem: Image resize OOMed the upload service pod
**Encountered:** 2026-03-16
**Root cause:** Sharp library loads entire image into memory; 12MP phone photos hit 48MB
**Solution:** Added `limitInputPixels` option; capped at 25MP before resize
**Lesson:** Set container memory limits before load testing, not after

## Decisions & Trade-offs

<!-- Record every meaningful "we chose X over Y because Z" -->

- **Sync resize over async worker** — simpler, no queue; acceptable latency at current volume.
  Revisit if p95 upload > 2s. (2026-03-14)
- **Sharp over Jimp** — 10× faster; requires native deps but k8s build handles this. (2026-03-14)

## References

- PR: https://github.com/org/repo/pull/51
- Related: #001 (auth required before photo upload)
- Design doc: todo/design/002-photo-upload-design.md
- Stack Overflow: https://stackoverflow.com/a/... (re: Sharp memory limits)
```

---

## Workflow

### Starting a New Task

1. Check `todo/README.md` — what's the next available number?
2. Create `todo/<number>-<slug>.md` from the template above
3. **Add a row to `todo/README.md` immediately** — status 📋 Planned (or 🔄 In progress if starting now), branch `—`, PR `—`
4. Create a git branch: `feat/<slug>` (or `fix/<slug>` for bugs)

```bash
git checkout -b feat/<slug>
```

5. **Update `todo/README.md`** — set Branch to `feat/<slug>`
6. If this is a planned feature, run `/feature-plan` and paste or link the output into the task file's **Approach** section.

### During Development

- **After hitting a problem** — add a `### Problem:` entry immediately. Don't wait until the end; you'll forget the details.
- **After making a key decision** — add a **Decisions & Trade-offs** bullet.
- **At the end of a session** — update the task checklist and status field. Future-you (or a teammate) should be able to resume without a handoff conversation.
- **When context window gets large** — write your current understanding into the task file before starting a fresh session. This is your external memory.

### Opening a PR

1. Update the task file:
   - Set `**PR:**` to the PR number/URL
   - Set `**Status:**` to `👀 In review`
2. Update `todo/README.md` status and PR column
3. Reference the task file in the PR description:

```markdown
## Context
See [todo/002-photo-upload.md](todo/002-photo-upload.md) for full design,
decisions, and known issues.
```

### After Merging

1. Set `**Status:**` to `✅ Shipped` and `**Shipped:**` to today's date
2. Update `todo/README.md`
3. The task file is **never deleted** — it becomes a permanent record

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

## Integration with Other Skills

| Skill | How it integrates |
|-------|------------------|
| `/feature-plan` | Run first; paste or link the output into the task file's **Approach** section |
| `/deep-research` | Research findings saved to `todo/research/<slug>/`; linked from task file |
| `/design-review` | Design audit findings logged in the task file's **Problems & Solutions** |
| `/code-review` | Review comments that require action become task checklist items |
| `/document-release` | After shipping, reference the task file as the source of truth for CHANGELOG entries |

---

## README.md Maintenance

`todo/README.md` is the single source of truth for project status. It must be updated **as part of the same action** that changes a task — never as a follow-up.

### When to update README.md

| Trigger | What to update |
|---------|---------------|
| New task created | Add row with status 💡 or 📋, branch `—`, PR `—` |
| Task moves to In progress | Status → 🔄, Branch → `feat/<slug>` |
| PR opened | Status → 👀, PR → `#<number>` |
| PR merged | Status → ✅, note shipped date in task file |
| Task cancelled | Status → ❌, add reason in task file |
| Branch renamed or PR number changes | Update Branch/PR columns immediately |

### README.md sync check

Before ending any session that touched task files, verify the README is in sync:

1. Open `todo/README.md`
2. For each task file that was created or modified this session, confirm the row matches the current state of the task file
3. If any row is stale — wrong status, missing branch, missing PR — update it now
4. If a task file exists with no corresponding README row, add it

**The README must never lag the task files.** A task file updated to `🔄 In progress` with no corresponding README update is a broken index.

### README health check

When asked "what are we working on?" or "show me project status", always read `todo/README.md` first — not individual task files. If the README appears stale (tasks in progress with no branch, shipped tasks still showing as in-review), run the sync check above before reporting status.

---

## Quality Rules

1. **Write problems down immediately.** The value of this system is in the **Problems & Solutions** section. A task file with no problems recorded is incomplete — every non-trivial feature hits at least one wall.
2. **Never delete task files.** They are institutional memory. Cancelled tasks get `❌ Cancelled` status and a reason.
3. **README.md is updated in the same action, not as a follow-up.** See README.md Maintenance above. A stale index is worse than no index.
4. **One branch per task.** Don't mix unrelated work on a branch — it breaks the task ↔ branch ↔ PR traceability.
5. **Update before ending a session.** If you close your laptop without updating the task file and README, the context is gone.
6. **Link, don't duplicate.** If `/feature-plan` produced a detailed doc, link to it rather than copying it. The task file is the hub, not the whole archive.

---

## Examples

```
"Start tracking a new feature for user notifications"
"Log the problem I just hit with the websocket reconnect"
"What's the current status of the billing integration task?"
"Update the todo for the search refactor — just opened a PR"
"Show me all in-progress tasks"
```
