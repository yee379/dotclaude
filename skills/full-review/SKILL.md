---
name: full-review
description: Orchestrates the board review pipeline — runs plan-arch-review, plan-eng-review, plan-doc-review, and security-review in parallel, then re-runs the full board if any reviewer amends the plan. Iterates until all reviewers pass in the same round with no changes. Use when asked to "run a full review", "review everything", or "gate this plan".
license: MIT
compatibility: opencode
---

# Full Review

Runs the four plan reviewers as a **board** — in parallel, not sequentially. If any reviewer
amends the plan, the whole board re-reviews the updated plan. The round repeats until all
reviewers pass in the same round without triggering any further changes. Maximum 3 rounds.

**Model routing:** Triage is Haiku-eligible. Each reviewer runs at **Opus** — they require deep
reasoning, cross-file analysis, and architectural judgment. Do not downgrade to Sonnet.

**This skill assumes a plan already exists.** If you don't have one yet, run `/feature-plan` first.

**This skill does not implement anything.** It convenes the board, tracks rounds, and tells you
when you're clear to build.

---

## The board model

```
/full-review
      │
      ▼
  [Triage]      which reviewers are relevant for this change?
      │
      ▼
  ┌─────────────────────────────────────────────────┐
  │  ROUND N  (all relevant reviewers in parallel)  │
  │                                                 │
  │  plan-arch-review   plan-eng-review             │
  │  plan-doc-review    security-review             │
  │                                                 │
  │  if any reviewer amends the plan ───────────────┤
  │                                      next round │
  └─────────────────────────────────────────────────┘
      │  all pass in same round, no amendments
      ▼
  [Clear to build]
      │
      ▼  (after implementation)
  /plan-closeout → /prod-release
```

---

## Step 0: Locate the plan

Before anything else, find what's being reviewed:

1. Check for a plan file: `DESIGN.md`, `design-doc.md`, or any `.md` in `.claude/` describing the feature.
2. Check git: `git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~5)...HEAD --stat 2>/dev/null | head -30` — is there already code on this branch that implicitly defines the scope?
3. Check `TODO.md` / `todo/` for the item being worked.

If no plan is found, **stop** and tell the user:
> "No plan found. Run `/feature-plan` first to produce a design document, then come back to `/full-review`."

If a plan is found, summarise it in 2-3 sentences so the user can confirm you've read the right
thing before proceeding.

---

## Step 1: Triage — which reviewers apply?

Not every change needs every reviewer. Run triage first to avoid wasted effort.

```
REVIEWER             SKIP IF...
──────────────────────────────────────────────────────────────────────
plan-arch-review     change touches only a single existing service with
                     no new data stores, no new async channels, no service
                     boundary changes, and no new infrastructure
plan-eng-review      change is purely documentation or config with no
                     code changes
plan-doc-review      change is purely internal/infra with no user-facing
                     surface, no API changes, no new commands or config
security-review      change has no user input, no auth changes, no new
                     API endpoints, no secrets, no new K8s workloads
──────────────────────────────────────────────────────────────────────
```

**Default: run all reviewers.** Only skip if the skip condition is clearly and unambiguously met.
When in doubt, run it.

Present the triage result:

```
Triage complete
──────────────────────────────────────────────────────
plan-arch-review     RUN | SKIP (reason)
plan-eng-review      RUN | SKIP (reason)
plan-doc-review      RUN | SKIP (reason)
security-review      RUN | SKIP (reason)
──────────────────────────────────────────────────────
```

**STOP.** Ask the user to confirm the triage before proceeding. Only proceed after confirmation.

---

## Step 2: Board rounds

Run up to **3 rounds**. In each round:

1. Announce: "Starting Round N — running all reviewers in parallel."
2. Invoke all relevant reviewers concurrently — do not run them one at a time.
3. Collect all results. For each reviewer, record:
   - Issues found
   - Issues resolved (user accepted or plan amended)
   - Issues unresolved
   - Whether the plan was **amended** this round (any change to the plan doc)
   - Status: PASS | PASS WITH WARNINGS | FAIL

4. After all reviewers complete, show the round dashboard:

```
Round N complete
──────────────────────────────────────────────────────
plan-arch-review     ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
plan-eng-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
plan-doc-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
security-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
──────────────────────────────────────────────────────
Plan amended this round: YES → starting Round N+1 | NO → board complete
```

5. **Decide whether to iterate:**
   - If **any reviewer amended the plan** this round → start the next round (all reviewers
     re-review the updated plan, including ones that passed)
   - If **no reviewer amended the plan** this round → board is complete, proceed to summary
   - If any reviewer has status **FAIL** (unresolved blocking issues) → **stop**. Do not start
     another round. Tell the user which issues must be resolved before continuing.

6. If **Round 3 completes with amendments still happening**: stop. Tell the user the plan has
   not stabilised after 3 rounds and list the outstanding changes still being triggered.

---

## Step 3: Final summary

After the board completes (or is halted), produce the final summary:

```
FULL REVIEW — FINAL SUMMARY
============================================================
Plan:    {plan file or description}
Branch:  {branch}
Date:    {date}
Rounds:  {N completed}
------------------------------------------------------------
plan-arch-review     {✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP}  {N issues}
plan-eng-review      {✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP}  {N issues}
plan-doc-review      {✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP}  {N issues}
security-review      {✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP}  {N issues}
------------------------------------------------------------
ADRs written:          {N}  (in docs/adr/)
Test plan written:     {Y/N}  (in todo/ task file)
Doc gaps added:        {N}
Accepted warnings:     {N}
Blocking issues:       {N}
------------------------------------------------------------
VERDICT:  CLEAR TO BUILD | BLOCKED | CLEAR WITH WARNINGS | UNSTABLE
============================================================
```

**CLEAR TO BUILD** — all reviewers passed in the final round, no unresolved issues.

**CLEAR WITH WARNINGS** — all reviewers passed, but the user accepted risk on one or more issues.
List the accepted warnings explicitly so they can be revisited post-ship.

**BLOCKED** — one or more reviewers failed with unresolved issues. List the blocking issues and
which reviewer they belong to.

**UNSTABLE** — the plan did not stabilise within 3 rounds. List what was still changing and why.

---

## After the review

If verdict is **CLEAR TO BUILD** or **CLEAR WITH WARNINGS**:

> "You're clear to implement. When the code is done, run `/plan-closeout` to close out the task,
> apply the documentation updates identified by plan-doc-review, and sync TODO.md — then run
> `/prod-release` to promote through environments."

If verdict is **BLOCKED** or **UNSTABLE**:

> "Resolve the issues above, then re-run `/full-review`."

---

## Formatting rules

- Show the round dashboard after every round — never let the user lose track of where they are.
- Never batch issues across reviewers into a single question.
- One AskUserQuestion per issue, exactly as each underlying skill requires.
- If the user asks to skip a reviewer mid-round, use AskUserQuestion to confirm — skipping is
  accepting the risk that reviewer would have caught.
- If the user interrupts and resumes later, re-show the last round dashboard immediately so they
  can reorient.
- When a new round starts because the plan was amended, briefly summarise what changed:
  "Plan was amended in Round N: {summary of changes}. Starting Round N+1."
