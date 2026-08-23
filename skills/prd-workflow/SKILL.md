---
name: prd-workflow
description: Institutional knowledge management via a todo/ directory. Tracks features, platform changes, and infrastructure work as individual markdown files with a TODO.md priority index. Covers picking the next item, implementing, closing tickets, and reviewing backlog status. Use when asked to "track this task", "what's outstanding", "pick up where we left off", "add to the backlog", or "show status". Supersedes codebase-workflow and platform-workflow.
---

# PRD Workflow

Maintain a `todo/` directory as a prioritised backlog where every item is a first-class document — not a ticket stub, but a complete record of the problem, the design, the decisions made, and the outcome.

## Mode detection

| Signal | Mode |
|---|---|
| `[INFRA]`, "cluster", "k8s", "Helm", "namespace", "workload", "make apply", "vcluster", or `platform/` prefix in branch/path | **platform** |
| Everything else — software feature, API, refactor, bug fix | **codebase** |

State the detected mode at the start: `> Mode: Codebase` or `> Mode: Platform`.

---

## When to Activate

- Starting a new feature, task, or platform change
- "What should we work on next?", "what's left to do?", "what to do with todo #N?"
- After running a draft-prd or design skill — persist the output
- When picking up work from a previous session
- When a task is completed and needs closing out
- When asked to "log this", "track this task", "update the todo", or "show project status"

---

## The `todo/` Directory Structure

```
TODO.md                          ← priority index (source of truth)
todo/
├── 001-user-authentication.md
├── 002-photo-upload.md
└── 003-namespace-strategy.md    ← platform task
```

### TODO.md — The Priority Index

```markdown
# Project Tasks

| # | Title | Priority | Status | Provenance | Reference | Branch | PR |
|---|-------|----------|--------|------------|-----------|--------|----|
| [001](todo/001-user-authentication.md) | User authentication | 🔴 P0 | ✅ Done `1.2.0` | original backlog | — | feat/user-auth | #42 |
| [002](todo/002-photo-upload.md) | Photo upload | 🟠 P1 | 🔄 In Progress | Security review 2026-08-21 | [#001](todo/001-user-authentication.md) | feat/photo-upload | #51 |
| [003](todo/003-namespace-strategy.md) | Namespace strategy | 🟡 P2 | ✅ Done (no release) | #002 closeout | — | — | — |

**Summary:** 2 done · 1 in progress · 0 open
```

The `#` column must always be a markdown link to the task file — never a bare number.

> Priority and status emoji keys: `references/priority-status-key.md`

#### Column rules

**Title is one line.** A short summary — no history, no rationale, no findings. If you are
appending "— shipped in X, but note that Y" to a Title, that belongs in the task file. The
index is for scanning; the task file is authoritative (see *TODO.md Maintenance*).

**Status carries the release the task shipped under**, in backticks, for every terminal
status (`✅ Merged` / `✅ Done` / `🚀 Deployed` / `🚀 Applied` / `✅ Shipped`):
`🚀 Deployed \`0.14.0\``. A terminal status with no release — cluster config, manifests, or
docs only — is marked `(no release)` rather than left blank, so a missing version is
distinguishable from a forgotten one. Non-terminal statuses carry no version.

> **Derive the version, never guess it.** `git log -p -- <path/to/VERSION>` maps every
> version to the commit that set it, and `git log --grep="#<number>"` maps a task to its
> commits; `git show <sha>:<path/to/VERSION>` then gives the version in force at that
> commit. Attribute the release the task's *own* work shipped in, not a later one that
> merely touched the same area.

**Provenance is what raised the task** — the review, closeout, rollout, incident, or board
round that produced it, with a date where one applies (`Security review 2026-08-21`,
`#042 slice 0`, `original backlog`). This replaces grouping rows under `###` sub-headings:
sub-headings fragment the table into several that cannot be sorted or scanned as one, and a
row silently loses its provenance if it is ever moved. One table, provenance per row.

**Reference is the tasks this one depends on, blocks, or measurably affects** — as links,
not prose. Keep it to genuine relationships; every task in a repo is loosely related to
every other, and a Reference cell listing eight tasks tells a reader nothing.

Both columns are pointers. The *explanation* of a dependency lives in the task file's own
Dependencies section — see **Each task file is self-contained** below.

### Task Files

**Codebase tasks:** Load `references/codebase-task-template.md` when creating a new task file.

**Platform tasks:** Load `references/platform-task-template.md` when creating a new task file.

Numbering is sequential and never reused. Slug is kebab-case, max 5 words.

#### Each task file is self-contained

A task file should be readable on its own, by someone who has not seen `TODO.md` and is not
going to open seven sibling files to reconstruct the story. That means the task file — not
the index — carries:

- **A `## Provenance` section**, immediately after the header block: what raised this task,
  and the tasks it references, each with a one-line statement of *why* it is referenced.
  A bare list of numbers is not provenance.
- **The history**: what shipped when, in which release, what was found later, what was
  corrected. `TODO.md`'s Status and Provenance cells are the pointers to it, never the copy.

```markdown
## Provenance

**Raised by:** security review 2026-08-21 ([report](todo/research/.../report.md))

**References:**
- [#020](020-deny-list-token-revocation.md) — dependency: this task shrinks the population
  of leaked tokens, #020 is what makes an already-leaked one killable.
- [#045](045-issuer-hardening.md) — not a dependency: multiplicative, and this task landing
  does not reduce #045's necessity.
```

Duplication between the index and the task file is a drift liability, and the direction it
drifts is always the same: the index is edited during a rollout when the task file is not
open, and the two disagree with no way to tell which is current. Resolve it by having only
one copy — in the task file. The rule that the task file wins when they disagree is in
*TODO.md Maintenance*; this is what makes that rule actionable rather than aspirational.

---

## Workflow

### Picking the Next Item

**If the user names a task number** (e.g. "work on 027", "tell me about #3"): glob `todo/<number>-*.md` — open the first match directly. Do not search TODO.md first.

1. Read `TODO.md` in full
2. Find the highest-priority `⬜ Open` or `🔍 Reviewed` item (P0 before P1 before P2 before P3)
3. Read its full task file — understand the problem before the plan
4. Ask: are there open questions that need answering first?
5. If yes → resolve them (update the file) before touching code/cluster
6. If no → create the branch, then **immediately** update both files:
   - In the task file: set `**Status:**` to `🔄 In Progress` and `**Branch:**` to the branch name
   - In `TODO.md`: set status → `🔄`, Branch → branch name

**Branch naming:**

| Mode | Task type | Prefix | Example |
|------|-----------|--------|---------|
| Codebase | New feature | `feat/` | `feat/photo-upload` |
| Codebase | Bug fix | `fix/` | `fix/checkout-race` |
| Codebase | Refactor | `refactor/` | `refactor/search-layer` |
| Codebase | Docs | `docs/` | `docs/api-reference` |
| Platform | All | `platform/` | `platform/onboard-auth` |
| Platform | Emergency | `platform/hotfix-` | `platform/hotfix-ingress-down` |

---

### Starting a New Task

1. Check `TODO.md` — what's the next available number?
2. Create `todo/<number>-<slug>.md` from the appropriate template
3. Fill in at minimum: Problem Statement and Goals
4. **Add a row to `TODO.md` immediately** — priority, status `📋 Preparing`, branch `—`, PR `—`
5. **Before touching code or the cluster, ask:**
   > "Task #N is ready to plan. Shall I run `/draft-prd` now?"
   - Confirm then run the draft skill immediately.
   - Exception for trivial tasks: say so explicitly, then proceed.
6. Once the draft skill completes: set status to `⬜ Open` in both files. Ask:
   > "Plan is written. Shall I run `/board-review` to gate it?"
7. Only after `/board-review` gives CLEAR TO BUILD / CLEAR TO APPLY (status → `🔍 Reviewed`): create the branch and begin implementation.

---

### Planning a Task

When a task file exists but the Design section is sparse, **do not start implementation.** Ask first:
> "The design section for #N is sparse. Shall I run the draft-prd skill now?"

---

### During Development

- **After hitting a problem** — add a `### Problem:` entry to Problems & Solutions immediately.
- **If you encounter an unanticipated design change** — update the Design section before continuing.
- **Tick checklist items as they complete** — don't batch-tick at the end.
- **At end of session** — update the task file status. Future-you should be able to resume without a handoff.

**Platform: after every `make apply` or equivalent**, append a new `### Applied YYYY-MM-DD` entry to the `## Deployment Log` section. Never overwrite — each apply gets its own entry. Run any available test suites immediately post-apply and record the result.

---

### Opening a PR

1. Update the task file:
   - Set `**Status:**` to `🏁 Implementation Done` when all checklist items are ticked
   - Set `**Status:**` to `👀 PR Open` and `**PR:**` to the PR number once raised
2. Update `TODO.md` — status and PR column
3. Reference the task file in the PR description:

```markdown
## Context
See [todo/002-photo-upload.md](todo/002-photo-upload.md) for full design, decisions, and known issues.
```

---

### Closing a Task

**Codebase — when PR is merged:**

1. Tick all checklist items
2. Change `**Status:**` to `✅ Merged`, set `**Shipped:**` to today's date
3. Update `TODO.md` — flip status to `✅ Merged`
4. Commit: `git commit -m "feat: <title> (TODO #<n>)"`
5. **Invoke `/codebase-closeout`** — pass the task number and branch/PR as context. It will update README/CHANGELOG/docs and set the final status to `✅ Complete` in both the task file and `TODO.md`.

When production deployment completes (after `/prod-release`):

6. Change status to `🚀 Deployed` in both files

**Platform — when change is live in cluster:**

1. Add a final Deployment Log entry with outcome and verification
2. Set `**Status:**` to `🚀 Applied`, set `**Applied:**` to today's date
3. Update `TODO.md` — flip to `🚀 Applied`, update Summary line
4. Commit: `git commit -m "deploy(platform): #<n> <title> applied"`
5. **Invoke `/codebase-closeout`** — pass the task number. It will sync `TODO.md` and update any relevant docs.

Task files are **never deleted** — they become permanent records.

---

### P0 Platform Emergency (bypassing board review)

1. Create the task file and TODO.md row — status `📋 Preparing`
2. Create branch: `platform/hotfix-<slug>`
3. Set status to `🔄 In Progress` immediately
4. Implement and apply
5. Run `/board-review` **retrospectively** after the cluster is stable
6. Record the rationale for bypassing in `## Key Decisions`

---

### Adding a New Backlog Item

1. Pick the next available number from `TODO.md`
2. Create `todo/<n>-<slug>.md` from the appropriate template
3. Fill in: Problem Statement and Goals
4. Assign a priority tier (P0–P3)
5. Add a row to `TODO.md` with priority and status `📋 Preparing`
6. Commit: `git commit -m "docs(todo): add #<n> <title>"`
7. **Do not create a branch or begin implementation yet.** Next step is the draft-prd skill.

---

### Reviewing the Backlog

When asked "what should we work on next?":

1. Read `TODO.md` in full
2. Group open items by: P0 blockers → P1 high-value → P2 polish → P3 nice-to-have
3. Identify dependency chains
4. Suggest a sequenced roadmap with effort estimates
5. Flag any open questions in existing task files that are blocking progress

**TODO.md health check:** If it appears stale (tasks in progress with no branch, shipped tasks still showing as in-review), run the sync check before reporting status.

---

## Relationship to Git

```
todo/<number>-<slug>.md    ←→    git branch: feat/<slug> or platform/<slug>
                                 git commits: reference the task number
                                 PR: links back to the task file
```

### Commit messages

Reference the task number so git history links back to context:

```
feat(photo-upload): add S3 presigned URL generation [#002]
fix(photo-upload): increase presigned URL TTL to 2h [#002]
deploy(platform): #003 namespace-strategy applied
```

### When to commit

Commit after each **logical unit of work** — a self-contained change that could be reviewed or reverted on its own. Never wait until the end of a task to commit everything.

| Situation | Commit? |
|-----------|---------|
| A passing test + the code that makes it pass | ✅ Yes |
| A refactor with no behaviour change | ✅ Yes — its own commit |
| A bug fix | ✅ Yes — immediately |
| Updating `TODO.md` / task file status | ✅ Yes — same commit as the work |
| Adding a new task to the backlog | ✅ Yes |
| Half-finished feature, tests failing | ❌ No |
| Multiple unrelated changes bundled | ❌ No |

Always stage files **by name** — never `git add -A` or `git add .`.

---

## TODO.md Maintenance

`TODO.md` is the single source of truth for project status. Update it **as part of the same action** that changes a task — never as a follow-up. If the status in a task file disagrees with `TODO.md`, the task file is authoritative.

### Status transition triggers

| Trigger | What to update |
|---------|---------------|
| New task created | Add row: priority, status `📋 Preparing`, branch `—`, PR `—`, **Provenance filled in** (what raised it), Reference `—` |
| draft-prd completes | Status → `⬜ Open`; prompt to run `/board-review` |
| board-review starts | Status → `🔎 In Review` |
| board-review CLEAR | Status → `🔍 Reviewed`; merge board review into task file; delete `todo/review/<slug>/` |
| board-review BLOCKED/UNSTABLE | Status → `⬜ Open`; note blocking issues in Problems & Solutions |
| Branch created | Status → `🔄 In Progress`; Branch column filled |
| All checklist items ticked | Status → `🏁 Implementation Done` |
| PR opened | Status → `👀 PR Open`; PR column filled |
| PR merged | Status → `✅ Merged` **+ the release it merged under** (or `(no release)`) |
| `/codebase-closeout` completes | Status → `✅ Complete`; docs/CHANGELOG/README updated; version in Status matches `VERSION` |
| Production deployed / cluster applied | Status → `🚀 Deployed` (codebase) or `🚀 Applied` (platform), **+ the release**, in both `TODO.md` and the task file's `> **Status:**` line |
| Cancelled | Status → `❌ Won't Do`; reason in task file |

Capture the version **at the moment of the transition**, when you still have the tag or `VERSION`
in hand. Recovering it later means deriving it from git history, which works but is slow and
mis-attributes to a neighbouring release if done carelessly — see `references/priority-status-key.md`.

---

## Quality Rules

1. **Problem statement first.** Never write the design before you can describe what is broken.
2. **Open questions block implementation.** Resolve them before touching code or cluster.
3. **Write problems down immediately.** A task file with no Problems & Solutions is incomplete.
4. **Non-Goals prevent scope creep.** Every task must say what it deliberately does not do.
5. **The checklist is the contract.** Every step must appear in the checklist.
6. **TODO.md is updated in the same action, not as a follow-up.**
7. **Never delete task files.** Cancelled tasks get `❌ Won't Do` status and a reason.
8. **One branch per task.**
9. **Update before ending a session.**

---

## Where Standards Fit

Standards belong in the **plan**, not in implementation:

```
draft-prd → board-review → implementation → closeout → prod-release
    ↑             ↑                ↑
 standards     enforced by      just execute
 inform the    reviewers        the plan
 design
```

If you find yourself wanting to apply a standard during implementation, the plan was underspecified — update the Design section and note it in Problems & Solutions.

---

## Integration with Other Skills

| Skill | How it integrates |
|-------|------------------|
| `/codebase-scout` | Writes task files into `todo/`; workflow picks them up |
| `/draft-prd` | Fills the Design section of codebase task files |
| `/draft-prd` | Fills Platform Design section of platform task files |
| `/board-review` | Run before implementation; verdict updates task status |
| `/research` | Research saved to `todo/research/<slug>/`; linked from task file |
| `/k8s-deploy` | Write deployment outcome back to Deployment Log after every apply |
| `/troubleshoot` | Record findings as `### Problem:` in Problems & Solutions |
| `/code-review` | Review findings → new checklist items or backlog items |
| `/codebase-closeout` | After shipping: close out task file, sync TODO.md, update docs |
| `/prod-release` | Terminal status: `🚀 Deployed` (codebase) or `🚀 Applied` (platform) |
