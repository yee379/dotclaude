# TODO #<N> — <Feature / Task Title>

> **Priority:** 🟡 P2 — Medium
> **Status:** 🔄 In Progress
> **Branch:** `feat/<slug>`
> **PR:** #<number> (or — if not yet raised)
> **Created:** YYYY-MM-DD
> **Shipped:** — (filled when merged)

<!-- On reaching a terminal status, write the release into the Status line itself:
     `> **Status:** 🚀 Deployed \`0.14.0\` — live in dev and prod as of YYYY-MM-DD`
     or `(no release)` if the deliverable was config or docs only. -->

---

## Provenance

**Raised by:** <the review, closeout, rollout, incident, or board round that produced this task,
with a date where one applies — e.g. `security review 2026-08-21`, `#042 slice 0 closeout`,
`original backlog`>

**References:**
- [#NNN](NNN-slug.md) — <one line on *why*: dependency, blocked-by, or measurably affected. A bare
  list of numbers is not provenance.>

<!-- This section is what makes the task file readable on its own. TODO.md's Provenance and
     Reference columns are pointers to it, never the copy — when they disagree, this file wins. -->

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

> *Populated by `/board-review` after the board completes. Do not fill manually.*

**Verdict:** CLEAR TO BUILD | CLEAR WITH WARNINGS | BLOCKED | UNSTABLE
**Date:** YYYY-MM-DD
**Rounds:** N

| Reviewer | Result | Amended | Key findings |
|---|---|---|---|
| research | — | — | — |
| codebase-arch-review | — | — | — |
| codebase-eng-review | — | — | — |
| doc-review | — | — | — |
| security-review | — | — | — |

**Accepted warnings:** none
**ADRs written:** 0

---

## Relationship to Other Tasks

Which items does this depend on, unblock, or interact with?

- **#001 (User Auth):** Must be shipped before photo upload — auth required to associate photos with users.
- **#003 (Billing):** Independent, no dependency.
