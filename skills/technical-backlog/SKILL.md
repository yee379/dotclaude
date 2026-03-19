---
name: technical-backlog
description: Manage a prioritised technical backlog using a todo/ directory. Each item is a self-contained markdown file with problem statement, design, implementation checklist, and open questions. Covers planning, picking the next item, implementing, and closing tickets.
---

# Technical Backlog

Maintain a `todo/` directory as a prioritised technical backlog where every item
is a first-class document — not a ticket stub, but a complete record of the
problem, the design, the decisions made, and the outcome. The goal is that any
item can be picked up cold, implemented correctly, and closed without needing
to reconstruct context from scratch.

## When to Activate

- When asked "what should we work on next?" or "what's left to do?"
- When asked to plan, review, or implement a specific TODO item
- When a TODO is completed and needs closing out
- When asked to add a new item to the backlog
- When reviewing overall project maturity or alpha/beta readiness

---

## Directory Structure

```
todo/
├── TODO.md                              ← priority index (source of truth)
├── 001-per-user-identity.md
├── 002-input-validation.md
├── 010-sanitise-error-messages.md
└── ...
```

### TODO.md — The Priority Index

The index groups items by priority tier and shows status at a glance:

```markdown
# Project — TODO Index

| #   | Title                          | Status   | File                              |
|-----|--------------------------------|----------|-----------------------------------|
| 1   | Per-user identity propagation  | ⬜ Open  | [001-...md](./001-....md)         |
| 2   | Input validation               | ✅ Done  | [002-...md](./002-....md)         |

**Summary:** 3 done · 5 open
```

Priority tiers: 🔴 P0 Critical · 🟠 P1 High · 🟡 P2 Medium · 🔵 P3 Low

Status values: `⬜ Open` · `🔄 In Progress` · `✅ Done` · `❌ Won't Do`

---

## TODO File Format

Each file is a living document. It starts with a problem statement and grows
as design and implementation decisions are made.

```markdown
# TODO #<N> — <Title>

> **Priority:** 🟡 P2 — Medium
> **Status:** ⬜ Open
> **Branch:** `todo/<n>-<slug>`

---

## Problem Statement

What is wrong or missing today? Show the current (broken) flow.
Include concrete examples of what leaks, fails, or is missing.
Don't describe the solution here — describe the pain.

### What fails today

| Scenario | Current behaviour | Desired behaviour |
|----------|-------------------|-------------------|
| Backend down | Raw IP leaked to LLM | Safe message returned |

---

## Goals

Numbered list of what Done looks like. Each goal should be
independently verifiable.

1. Operators see everything — raw errors preserved in logs
2. LLM sees only safe, actionable messages
3. Every sanitisation rule has a unit test

## Non-Goals

What this PR deliberately does not do. Prevents scope creep.

---

## Design

### Architecture

Where does the fix live and why? One diagram is worth a page of prose.

\`\`\`
GraphQLClient.execute()
    ├── except TransportQueryError:
    │       LOG.error(raw)                    ← operators see everything
    │       raise CoactAPIError(safe_msg)     ← LLM sees nothing internal
\`\`\`

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

## Open Questions

Questions that must be answered before or during implementation.
Include a recommended answer so they can be resolved quickly.

1. **Should X or Y?** — Recommendation: X, because Z.

---

## Relationship to Other TODOs

Which items does this depend on, unblock, or interact with?

- **#2 (Input Validation):** Complementary — #2 catches bad inputs before
  the request; this catches bad responses after the request.
- **#13 (Correlation IDs):** Once #13 exists, the generic fallback can include
  a request ID for cross-referencing.
```

---

## Workflow

### Picking the Next Item

1. Read `todo/TODO.md` in full
2. Find the highest-priority `⬜ Open` item
3. Read its full TODO file — understand the problem before the plan
4. Ask: are there open questions that need answering first?
5. If yes → resolve them (update the file) before touching code
6. If no → create the branch and start the implementation checklist

```bash
git checkout -b todo/<n>-<slug>
```

### Planning a TODO

When asked to plan an item (or when the design section is thin):

1. Read the problem statement carefully
2. Explore the codebase — find every file the change touches
3. Draft the Design and Implementation Plan sections in the TODO file
4. Add Open Questions for anything that requires a decision
5. Present the plan for approval before writing code

The TODO file *is* the plan. Don't maintain a separate plan document.

### Implementing

1. Work through the Implementation Checklist top to bottom
2. Tick items as they complete — don't batch-tick at the end
3. If you hit a design problem not anticipated in the plan, update the
   TODO file's Design section before continuing
4. When all checklist items are ticked, run the full test suite

### Closing a TODO

When implementation is complete:

1. Tick all checklist items in the TODO file
2. Change `**Status:**` to `✅ Done`
3. Update `todo/TODO.md` — flip status, update summary count
4. Commit everything together

```bash
git add src/ tests/ docs/ todo/
git commit -m "feat: <title> (TODO #<n>)"
```

### Adding a New TODO

1. Pick the next available number from `todo/TODO.md`
2. Create `todo/<n>-<slug>.md` with the template above
3. Fill in at minimum: Problem Statement and Goals
4. Add a row to `todo/TODO.md` with priority and status `⬜ Open`
5. Commit the new file: `git add todo/ && git commit -m "docs(todo): add #<n> <title>"`

---

## Reviewing the Backlog

When asked "what should we work on next?" or "what can get us out of alpha/beta?":

1. Read `todo/TODO.md` in full
2. Group open items by: blockers → high-value → polish
3. Identify dependency chains (e.g. #10 must land before #23)
4. Suggest a sequenced roadmap with effort estimates
5. Flag any open questions in existing TODO files that are blocking progress

---

## Quality Rules

1. **The problem statement comes first.** Never write the design before
   you can clearly describe what is broken. A well-written problem
   statement makes the design obvious.
2. **Open questions block implementation.** If a TODO has unresolved
   open questions, resolve them before touching code — not during.
3. **The checklist is the contract.** Every implementation step must
   appear in the checklist. If you did something not on the list,
   add it retroactively and tick it.
4. **Non-Goals prevent scope creep.** Every TODO must say what it
   deliberately does not do. "Out of scope for this PR" is a complete
   sentence.
5. **Close the loop.** A TODO is not done until the TODO.md index
   reflects it. A stale index is worse than no index.
6. **Design refinements belong in the TODO file.** If you spot a
   problem with the original plan during implementation, update the
   Design section — don't silently deviate.

---

## Integration with Other Skills

| Skill | How it integrates |
|-------|------------------|
| `/feature-plan` | Use for new features; paste the output into a new TODO file as the Design section |
| `/project-management` | Complementary — use `/project-management` for feature delivery tracking (branches, PRs, shipping); use this skill for prioritised technical debt and hardening work |
| `/code-review` | Review findings that require fixes become new TODO items |
| `/security-review` | Security gaps discovered become P0/P1 TODO items |
| `/document-release` | After closing a batch of TODOs, run to sync docs and CHANGELOG |
