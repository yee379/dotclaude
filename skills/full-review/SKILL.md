---
name: full-review
description: Orchestrates the board review pipeline — runs deep-research, plan-arch-review, plan-eng-review, plan-doc-review, and security-review in parallel, then re-runs the full board if any reviewer amends the plan. Iterates until all reviewers pass in the same round with no changes. Use when asked to "run a full review", "review everything", or "gate this plan".
license: MIT
compatibility: opencode
---

# Full Review

Runs the five plan reviewers as a **board** — in parallel, not sequentially. If any reviewer
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
/full-review (main session)
      │
      ▼
  [Triage]      which reviewers are relevant for this change?
      │
      ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  ROUND N  (all reviewers launched as parallel subagents)        │
  │                                                                 │
  │  subagent: deep-research     → todo/review/<slug>/round-N-dr.md │
  │  subagent: plan-arch-review  → todo/review/<slug>/round-N-ar.md │
  │  subagent: plan-eng-review   → todo/review/<slug>/round-N-er.md │
  │  subagent: plan-doc-review   → todo/review/<slug>/round-N-dc.md │
  │  subagent: security-review   → todo/review/<slug>/round-N-sr.md │
  │                                                                 │
  │  main session reads all outputs, consolidates                   │
  │                                                                 │
  │  if any subagent amended the plan ──────────────────────────────┤
  │                                                     next round  │
  └─────────────────────────────────────────────────────────────────┘
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

1. **If the user named a task number** (e.g. "review 027", "full review of #3"): read
   `todo/<number>-*.md` directly — glob `todo/027-*.md` (or zero-padded equivalent) and open
   the first match. This is always the right file; do not search elsewhere first.
2. **Otherwise**, check in order:
   - `todo/` — find the in-progress task (`🔄 In Progress` in `TODO.md`) and read its file
   - `DESIGN.md` or `design-doc.md` in the repo root or `.claude/`
   - `git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~5)...HEAD --stat 2>/dev/null | head -30` — code already on the branch may implicitly define scope

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
deep-research        the technology and approach are well-understood —
                     no unknowns that would make the plan speculative
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

Present the triage result and immediately proceed to Step 2 — no confirmation needed:

```
Triage complete
──────────────────────────────────────────────────────
deep-research        RUN | SKIP (reason)
plan-arch-review     RUN | SKIP (reason)
plan-eng-review      RUN | SKIP (reason)
plan-doc-review      RUN | SKIP (reason)
security-review      RUN | SKIP (reason)
──────────────────────────────────────────────────────
Starting Round 1...
```

---

## Step 2: Board rounds

Each board member runs as a **parallel subagent** — one agent per reviewer, all launched in a
single message. This gives each reviewer a clean, focused context window and true parallelism.

Run up to **3 rounds**. In each round:

1. Announce: "Starting Round N — launching board subagents in parallel."

2. Create the output directory: `todo/review/<slug>/` (where `<slug>` is the task file name
   without extension, e.g. `027-my-feature`).

3. **Launch all relevant reviewers as subagents in a single message.** Each subagent receives:

```
You are a [REVIEWER NAME] subagent in a board review.

Your role: [one-line role description — see below]

Plan file: <path to task file>
Plan content:
<full contents of the task file pasted here>

Your job:
1. Perform a thorough [REVIEWER NAME] review of this plan using the /[skill-name] skill guidelines.
2. Write your findings incrementally to: todo/review/<slug>/round-<N>-<reviewer>.md
   - Write partial findings as you go so progress is not lost if interrupted.
   - Structure: ## Issues, ## Amendments (changes made to the plan file), ## Status (PASS | PASS WITH WARNINGS | FAIL)
3. If you identify issues that require changes to the plan, edit the plan file directly.
4. Return a structured summary:
   - Issues found (with severity: blocking | warning)
   - Amendments made (list any edits to the plan file)
   - Status: PASS | PASS WITH WARNINGS | FAIL
```

Reviewer roles:
- **deep-research**: Fact-check plan assumptions, check dependency health, identify obsolescence
  risks and simplification opportunities. See `/deep-research` Mode 2 guidelines.
- **plan-arch-review**: Evaluate service boundaries, data ownership, consistency models,
  technology selection, failure domains. Write ADRs to `docs/adr/` for significant decisions.
- **plan-eng-review**: Review implementation correctness, test coverage, performance, edge cases.
  Produce a test plan artifact in the task file.
- **plan-doc-review**: Identify every doc that needs updating — README, ARCHITECTURE, API docs,
  runbooks, CHANGELOG, ADRs, CONTRIBUTING. Add gaps to the plan.
- **security-review**: Check secrets, auth, input validation, injection vectors, supply chain,
  Kubernetes workload security.

4. **Wait for all subagents to complete**, then read each `todo/review/<slug>/round-N-<reviewer>.md`
   file and consolidate results. For each reviewer record:
   - Issues found
   - Amendments made to the plan
   - Status: PASS | PASS WITH WARNINGS | FAIL

5. Show the round dashboard:

```
Round N complete
──────────────────────────────────────────────────────
deep-research        ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
plan-arch-review     ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
plan-eng-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
plan-doc-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
security-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP   amended: Y/N
──────────────────────────────────────────────────────
Plan amended this round: YES → starting Round N+1 | NO → board complete
```

6. **Decide whether to iterate — automatically, no prompt needed:**
   - If **any reviewer amended the plan** this round → immediately start the next round (all
     reviewers re-review the updated plan, including ones that passed)
   - If **no reviewer amended the plan** this round → board is complete, proceed to summary
   - If any reviewer has status **FAIL** (unresolved blocking issues) → **stop**. Do not start
     another round. Tell the user which issues must be resolved before continuing.

7. If **Round 3 completes with amendments still happening**: stop. Tell the user the plan has
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
deep-research        {✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP}  {N issues}
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

> "You're clear to implement. For the implementation phase:
> - Use `/project-management` to track progress in the task file and keep TODO.md in sync
> - Use `/tdd-workflow` to drive code quality — tests first, then implementation
> - Use `/code-review` at any point if you want a mid-implementation sanity check
>
> When the code is done, run `/plan-closeout` to close out the task, apply the documentation
> updates identified by plan-doc-review, and sync TODO.md — then run `/prod-release` to promote
> through environments."

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
