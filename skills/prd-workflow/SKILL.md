---
name: prd-workflow
description: Institutional knowledge management via a todo/ directory. Tracks features, platform changes, and infrastructure work as individual markdown files with a TODO.md priority index. Covers picking the next item, implementing, closing tickets, and reviewing backlog status. Use when asked to "track this task", "what's outstanding", "pick up where we left off", "add to the backlog", or "show status". Supersedes codebase-workflow and platform-workflow.
---

# PRD Workflow

Maintain `todo/` as a prioritised backlog where every item is a first-class document — not a
ticket stub, but a complete record of the problem, the design, the decisions, and the outcome.

Activate when: starting a feature, task, or platform change · "what should we work on next?",
"what's left?", "what about todo #N?" · persisting draft-prd or design output · picking up work
from a previous session · closing a completed task · "log this", "track this", "show status".

## Mode detection

| Signal | Mode |
|---|---|
| `[INFRA]`, "cluster", "k8s", "Helm", "namespace", "workload", "make apply", "vcluster", `platform/` prefix in branch/path | **platform** |
| Everything else — software feature, API, refactor, bug fix | **codebase** |

State it: `> Mode: Codebase` or `> Mode: Platform`.

---

## Structure

```
TODO.md                          ← priority index
todo/
├── 001-user-authentication.md
├── 002-photo-upload.md
└── 003-namespace-strategy.md    ← platform task
```

Numbering is sequential and never reused; slugs are kebab-case, max 5 words. Task files are
**never deleted** — they are permanent records.

### TODO.md — the priority index

```markdown
# Project Tasks

| # | Title | Priority | Status | Provenance | Reference | Branch | PR |
|---|-------|----------|--------|------------|-----------|--------|----|
| [001](todo/001-user-authentication.md) | User authentication | 🔴 P0 | ✅ Done `1.2.0` | original backlog | — | feat/user-auth | #42 |
| [002](todo/002-photo-upload.md) | Photo upload | 🟠 P1 | 🔄 In Progress | Security review 2026-08-21 | [#001](todo/001-user-authentication.md) | feat/photo-upload | #51 |
| [003](todo/003-namespace-strategy.md) | Namespace strategy | 🟡 P2 | ✅ Done (no release) | #002 closeout | — | — | — |

**Summary:** 2 done · 1 in progress · 0 open
```

Priority and status emoji keys: `references/priority-status-key.md`.

**One flat table.** No `###` sub-headings grouping rows — they fragment the table into several
that cannot be sorted or scanned as one, and a moved row silently loses its grouping. Provenance
goes per row instead.

**`#`** is always a markdown link to the task file, never a bare number.

**Title** is one line — a short summary, no history, rationale, or findings. If you are appending
"— shipped in X, but note Y", that belongs in the task file.

**Status** carries the release the task shipped under, in backticks, for every terminal status
(`✅ Merged` / `✅ Done` / `🚀 Deployed` / `🚀 Applied` / `✅ Shipped`): `🚀 Deployed \`0.14.0\``.
A terminal status with no release — cluster config, manifests, or docs only — is marked
`(no release)`, so a missing version is distinguishable from a forgotten one. Non-terminal
statuses carry no version.

> **Derive the version, never guess it.** `git log -p -- <path/to/VERSION>` maps each version to
> the commit that set it; `git log --grep="#<number>"` maps a task to its commits; `git show
> <sha>:<path/to/VERSION>` gives the version in force at that commit. Attribute the release the
> task's *own* work shipped in, not a later one that merely touched the same area. Capture it **at
> the moment of the transition**, while the tag or `VERSION` is still in hand.

**Provenance** is what raised the task — the review, closeout, rollout, incident, or board round
that produced it, with a date where one applies (`Security review 2026-08-21`, `#042 slice 0`,
`original backlog`). **One short sentence, never a status log:** it names the origin, not what has
happened since. A rollout timeline, a list of bugs found and fixed, or a slice-by-slice history
belongs in the task file. If you are writing "**2026-08-27:**" or a second clause describing an
outcome, move it to the task file. A Provenance cell grown past one line means the task file's
history section is missing that detail.

**Reference** is the tasks this one depends on, blocks, or measurably affects — as links, not
prose. Genuine relationships only; every task is loosely related to every other, and a cell
listing eight of them tells a reader nothing.

Both columns are **pointers**. The explanation lives in the task file.

### Deployment bundles

A `## Deployment bundles` section **after** the table, never a sub-heading inside it. It groups
tasks that are reviewed-and-unapplied and share enough deploy surface — the same file, overlay, or
manifest — that applying them separately would be an accident rather than a decision.

- **Ready to bundle** — every task is `🔍 Reviewed` or later and shares a concrete file/overlay
  with another row in the bundle. State the shared surface as a **path**, not a theme. Flag any
  task whose verdict or scope differs from its bundle-mates (dev-only, CLEAR WITH WARNINGS vs
  CLEAR TO APPLY) so it does not silently ride into a wider apply.
- **Plan/sequence together, not deploy-ready** — tasks sharing a root cause, a split lineage, or a
  file another will touch, but not all reviewed yet. A sequencing note, not a bundle.

Sharing a *theme* (same subsystem, reviewer, or provenance) does not qualify without a shared
*file* or *overlay* — that is what the Reference column is for. Update this section in the same
action that changes a task's status: a task reaching `🔍 Reviewed` while sharing a file with
something already listed is the trigger to promote a "plan together" row or add a new bundle.

### Task files are self-contained

A task file must be readable alone, by someone who has not seen `TODO.md` and will not open seven
sibling files. So the **task file**, not the index, carries:

- **A `## Provenance` section** immediately after the header block: what raised the task, and each
  referenced task with a one-line *why*. A bare list of numbers is not provenance.
- **The history** — what shipped when, in which release, what was found later, what was corrected.

```markdown
## Provenance

**Raised by:** security review 2026-08-21 ([report](todo/research/.../report.md))

**References:**
- [#020](020-deny-list-token-revocation.md) — dependency: this task shrinks the population
  of leaked tokens, #020 is what makes an already-leaked one killable.
- [#045](045-issuer-hardening.md) — not a dependency: multiplicative, and this task landing
  does not reduce #045's necessity.
```

Keeping only one copy — in the task file — makes "the task file wins" actionable. The
index gets edited during a rollout when the task file is not open, so duplication always drifts
the same direction, with no way to tell which is current.

Templates: `references/codebase-task-template.md` · `references/platform-task-template.md`.
Prose rules for filling them in:
`~/.claude/skills/agentic-standards/references/technical-prose.md`.

---

## Workflow

### Creating a task

1. **Check for duplicates and related work before picking a number.** Read `TODO.md` in full and
   grep task files for the same problem, file, or symptom — not just the same keyword.
   - **Duplicate** → do not create a number. Fold the new information into the existing task file
     (Problems & Solutions, or Provenance → References) and stop.
   - **Related** (different problem, shared root cause, file, or dependency) → create the task,
     and in the same action add each to the other's `## Provenance` → References with the one-line
     *why* (name which: dependency, shared root cause, shared file). If the relationship is a
     shared deployable file or overlay rather than just a shared cause, add the candidate to
     `## Deployment bundles` **now**, even if neither task is reviewed — cheaper than
     rediscovering it at apply time.
   - **Unrelated** → no cross-links.
2. Create `todo/<n>-<slug>.md` from the appropriate template. Fill in at minimum **Problem
   Statement** and **Goals**, and assign a priority tier (P0–P3).
3. **Add the `TODO.md` row immediately** — priority, status `📋 Preparing`, Provenance filled in,
   branch `—`, PR `—`, plus any Reference links from step 1.
4. Commit: `git commit -m "docs(todo): add #<n> <title>"`
5. **Do not create a branch or start implementing.** Ask:
   > "Task #N is ready to plan. Shall I run `/draft-prd` now?"

   Confirm, then run it immediately. For a genuinely trivial task, say so explicitly and proceed.
6. Once the draft completes → status `⬜ Open` in both files. Ask:
   > "Plan is written. Shall I run `/board-review` to gate it?"
7. Only after CLEAR TO BUILD / CLEAR TO APPLY (status → `🔍 Reviewed`): create the branch and
   begin.

If a task file exists but its Design section is sparse, **do not start implementation** — ask
whether to run `/draft-prd` first.

### Picking the next item

**If the user names a number** ("work on 027", "tell me about #3"): glob `todo/<number>-*.md` and
open the first match. Do not search TODO.md first.

Otherwise: read `TODO.md` in full → take the highest-priority `⬜ Open` or `🔍 Reviewed` item
(P0 → P3) → read its full task file, understanding the problem before the plan → resolve any open
questions first, updating the file → then create the branch and **immediately** set status
`🔄 In Progress` and the branch name in both the task file and `TODO.md`.

| Mode | Task type | Prefix | Example |
|------|-----------|--------|---------|
| Codebase | New feature | `feat/` | `feat/photo-upload` |
| Codebase | Bug fix | `fix/` | `fix/checkout-race` |
| Codebase | Refactor | `refactor/` | `refactor/search-layer` |
| Codebase | Docs | `docs/` | `docs/api-reference` |
| Platform | All | `platform/` | `platform/onboard-auth` |
| Platform | Emergency | `platform/hotfix-` | `platform/hotfix-ingress-down` |

### During development

- **Hit a problem** → add a `### Problem:` entry to Problems & Solutions immediately.
- **Unanticipated design change** → update the Design section before continuing.
- **Tick checklist items as they complete** — never batch-tick at the end.
- **End of session** → update status. Future-you should resume without a handoff.
- **Platform: after every `make apply`** → append a new `### Applied YYYY-MM-DD` entry to
  `## Deployment Log`, never overwriting. Run available test suites immediately post-apply and
  record the result.

### Opening a PR

Set `🏁 Implementation Done` when all checklist items are ticked, then `👀 PR Open` with the PR
number once raised; update `TODO.md`'s status and PR columns. Reference the task file in the PR:

```markdown
## Context
See [todo/002-photo-upload.md](todo/002-photo-upload.md) for full design, decisions, and known issues.
```

### Closing a task

**Codebase, on merge:** tick all checklist items → status `✅ Merged` with `**Shipped:**` today →
update `TODO.md` → `git commit -m "feat: <title> (TODO #<n>)"` → **invoke `/closeout-prd`** with
the task number and branch/PR, which updates README/CHANGELOG/docs and sets `✅ Complete` in both
files. After `/prod-release` completes, status → `🚀 Deployed`.

**Platform, once live:** add a final Deployment Log entry with outcome and verification → status
`🚀 Applied` with `**Applied:**` today → update `TODO.md` and its Summary line →
`git commit -m "deploy(platform): #<n> <title> applied"` → **invoke `/closeout-prd`**.

### P0 platform emergency (bypassing board review)

Create the task file and row (`📋 Preparing`) → branch `platform/hotfix-<slug>` → status
`🔄 In Progress` → implement and apply → run `/board-review` **retrospectively** once the cluster
is stable → record the bypass rationale in `## Key Decisions`.

### Reviewing the backlog

1. Read `TODO.md` in full; group open items P0 blockers → P1 high-value → P2 polish → P3
   nice-to-have, and identify dependency chains.
2. **Check `## Deployment bundles` against current status.** Any task that reached `🔍 Reviewed`
   since the section was last touched is a candidate to join a "ready to bundle" row; any "plan
   together" row where every task is now reviewed gets promoted. Update in the same pass.
3. Suggest a sequenced roadmap with effort estimates, calling out bundle opportunities so
   reviewed-but-unapplied work ships together rather than trickling out one apply at a time.
4. Flag open questions in existing task files that are blocking progress.

If `TODO.md` looks stale (in-progress tasks with no branch, shipped tasks still in review), run
the sync check before reporting status.

---

## Status transitions

`TODO.md` is updated **as part of the same action** that changes a task — never as a follow-up.
Where a task file and `TODO.md` disagree, **the task file is authoritative.**

| Trigger | Status becomes |
|---------|---------------|
| New task created | `📋 Preparing` (Provenance filled in) |
| draft-prd completes | `⬜ Open`; prompt for `/board-review` |
| board-review starts | `🔎 In Review` |
| board-review CLEAR | `🔍 Reviewed`; merge review into task file; delete `todo/review/<slug>/` |
| board-review BLOCKED/UNSTABLE | `⬜ Open`; note blockers in Problems & Solutions |
| Branch created | `🔄 In Progress`; Branch column filled |
| All checklist items ticked | `🏁 Implementation Done` |
| PR opened | `👀 PR Open`; PR column filled |
| PR merged | `✅ Merged` **+ the release** (or `(no release)`) |
| `/closeout-prd` completes | `✅ Complete`; docs updated; version matches `VERSION` |
| Deployed / applied | `🚀 Deployed` (codebase) or `🚀 Applied` (platform), **+ the release**, in both files |
| Cancelled | `❌ Won't Do`; reason in task file |

---

## Git

```
todo/<number>-<slug>.md    ←→    git branch: feat/<slug> or platform/<slug>
                                 git commits: reference the task number
                                 PR: links back to the task file
```

Commit messages reference the task number so history links back to context:

```
feat(photo-upload): add S3 presigned URL generation [#002]
fix(photo-upload): increase presigned URL TTL to 2h [#002]
deploy(platform): #003 namespace-strategy applied
```

Commit after each **logical unit of work** — a self-contained change reviewable or revertible on
its own. Never save it all for the end. Always stage **by name**; never `git add -A` or `git add .`.

| Situation | Commit? |
|-----------|---------|
| A passing test + the code that makes it pass | ✅ Yes |
| A refactor with no behaviour change | ✅ Yes — its own commit |
| A bug fix | ✅ Yes — immediately |
| Updating `TODO.md` / task file status | ✅ Yes — same commit as the work |
| Adding a new task to the backlog | ✅ Yes |
| Half-finished feature, tests failing | ❌ No |
| Multiple unrelated changes bundled | ❌ No |

---

## Quality rules

1. **Problem statement first.** Never write the design before you can describe what is broken.
2. **Open questions block implementation.** Resolve them before touching code or cluster.
3. **Write problems down immediately.** A task file with no Problems & Solutions is incomplete.
4. **Non-Goals prevent scope creep.** Every task says what it deliberately does not do.
5. **The checklist is the contract.** Every step appears in it.
6. **Never delete task files.** Cancelled tasks get `❌ Won't Do` and a reason.
7. **One branch per task.**
8. **Update before ending a session.**

## Where standards fit

Standards belong in the **plan**, not in implementation:

```
draft-prd → board-review → implementation → closeout → prod-release
    ↑             ↑                ↑
 standards     enforced by      just execute
 inform the    reviewers        the plan
 design
```

Wanting to apply a standard during implementation means the plan was underspecified — update the
Design section and note it in Problems & Solutions.

## Integration

| Skill | Integration |
|-------|------------|
| `/codebase-scout` | Writes task files into `todo/`; this workflow picks them up |
| `/draft-prd` | Fills the Design (codebase) or Platform Design (platform) section |
| `/board-review` | Run before implementation; verdict updates task status |
| `/research` | Saved to `todo/research/<slug>/`; linked from the task file |
| `/k8s-deploy` | Write the outcome to Deployment Log after every apply |
| `/troubleshoot` | Record findings as `### Problem:` in Problems & Solutions |
| `/code-review` | Findings → new checklist items or backlog items |
| `/closeout-prd` | After shipping: close the task file, sync TODO.md, update docs |
| `/prod-release` | Terminal status: `🚀 Deployed` (codebase) or `🚀 Applied` (platform) |
