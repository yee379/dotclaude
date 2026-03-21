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
  │  main session reads all outputs, collects Decisions Required    │
  │                                                                 │
  │  blocking decisions? ──────────────────── AskUserQuestion (×N) │
  │  judgement-calls?   ──────────────────── AskUserQuestion (×1) │
  │  defaulted?         ──────────────────── listed, no action    │
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

**Immediately after confirming the plan**, update the task file and `TODO.md`:
- Set `**Status:**` in the task file to `🔎 In Review`
- Update `TODO.md` — flip the status column to `🔎 In Review`

This marks the review as in-progress so project status is accurate throughout the board run.

**Main session context discipline — read this once and follow it for the entire run:**
- Store the plan as a **file path only**. Do not hold the full plan content in the main
  session's working memory across rounds — subagents read it directly from disk.
- After launching subagents, **do not re-read the plan file** unless you need to make a
  specific edit in response to a blocking decision.
- After consolidating a round, **drop the reviewer output content** from working memory.
  You only need the round dashboard summary going forward — the files remain on disk.
- Never paste full file contents into your own reasoning when a file path reference will do.
  The goal: main session context should grow by ~500 tokens per round, not ~10k.

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
plan-ux-review       change has no direct user-facing surface — pure
                     internal/infra, backend refactor, or platform-only
                     work with no new CLI, API, docs, or workflows that
                     scientists interact with directly
──────────────────────────────────────────────────────────────────────
```

**Default: run all reviewers.** Only skip if the skip condition is clearly and unambiguously met.
When in doubt, run it.

Present the triage result as plain text (not a code block) and immediately proceed to Step 2 — no confirmation needed:

   Triage complete
   ──────────────────────────────────────────────────────
   deep-research        RUN | SKIP (reason)
   plan-arch-review     RUN | SKIP (reason)
   plan-eng-review      RUN | SKIP (reason)
   plan-doc-review      RUN | SKIP (reason)
   security-review      RUN | SKIP (reason)
   plan-ux-review       RUN | SKIP (reason)
   ──────────────────────────────────────────────────────
   Starting Round 1...

---

## Step 2: Board rounds

Each board member runs as a **parallel subagent** — one agent per reviewer, all launched in a
single message. This gives each reviewer a clean, focused context window and true parallelism.

Run up to **3 rounds**. In each round:

1. Announce: "#NNN — Starting Round N — launching board subagents in parallel."
   (where NNN is the zero-padded TODO number, e.g. `#027 — Starting Round 1`)

2. Create the output directory: `todo/review/<slug>/` (where `<slug>` is the task file name
   without extension, e.g. `027-my-feature`).

3. **Prepare a trimmed plan excerpt for each reviewer.** Do not paste the full task file
   into every subagent — each reviewer only needs the sections relevant to its lens. This
   is the single most effective way to reduce subagent context pressure.

   | Reviewer | Sections to include |
   |---|---|
   | deep-research | Problem Statement, Goals, Design (full), Open Questions |
   | plan-arch-review | Problem Statement, Goals, Design (full), Non-Goals, Open Questions |
   | plan-eng-review | Problem Statement, Goals, Design (full), Implementation Plan, Implementation Checklist, Open Questions |
   | plan-doc-review | Problem Statement, Goals, Non-Goals, Implementation Plan (step titles only) |
   | security-review | Problem Statement, Design (full), Implementation Plan (step titles only), Open Questions |
   | plan-ux-review | Problem Statement, Goals, Non-Goals, Design (full), Open Questions |

   If the task file has no Design section or it is a stub, include the full file for all
   reviewers — there is nothing to trim.

4. **Launch all relevant reviewers as background subagents in a single message** using
   `run_in_background: true`. Record each agent's task ID.

   **Round 1:** paste the trimmed plan excerpt into each subagent prompt (see section table
   above). This is the only round where content is pasted — subagents have no prior context.

   **Round 2+:** do NOT paste plan content again. Pass only the file path and a one-line
   summary of what changed. The subagent reads the updated file directly from disk. This
   keeps the main session from accumulating large pastes across rounds.

   Each subagent receives:

```
You are a [REVIEWER NAME] subagent in a board review.

Your role: [one-line role description — see below]

Plan file: <path to task file>
[Round 1 only] Plan excerpt (sections relevant to your review):
<trimmed plan content — see section table above>

[Round 2+ only] Plan was amended in Round N: <one-line summary of changes>
Read the plan file directly from disk: <path> — do not rely on any previously pasted content.

Context budget warning: you are running as a background subagent with a finite
context window. Prioritise ruthlessly:
- Complete your highest-value review sections first (see Priority hierarchy below)
- Write findings in bullet points, not prose — one line per issue
- Stop adding new findings once your output file exceeds ~800 lines
- If you must choose between covering more ground shallowly or fewer sections
  deeply, choose fewer sections deeply — shallow coverage adds noise, not signal

Priority hierarchy (most important first — never skip these):
- plan-arch-review: Step 0 scope assessment → service boundary diagram → ADRs
- plan-eng-review: Step 0 scope challenge → test diagram → critical gaps
- deep-research: assumption verification → dependency health → obsolescence
- plan-doc-review: mandatory doc list → gaps
- security-review: auth/authz → injection → secrets

Your job:
1. Perform a thorough [REVIEWER NAME] review using the /[skill-name] skill guidelines,
   following the priority hierarchy above.
2. Write your findings incrementally to: todo/review/<slug>/round-<N>-<reviewer>.md
   - Write partial findings as you go — after each section — so progress is not lost.
   - Use this exact structure (do not add extra sections):

     ## Summary
     <3-5 bullet points — the most important findings, written last>

     ## Issues
     <one line per issue: SEVERITY | area | description>
     e.g. blocking | auth | JWT expiry not validated on refresh endpoint

     ## Decisions Required
     <structured entries — see format below>

     ## Amendments
     <list of edits made to the plan file, one line each>

     ## Status
     PASS | PASS WITH WARNINGS | FAIL

   - Write ## Summary last, after all other sections are complete.
   - Keep each issue to one line. Save prose for the ## Decisions Required entries only.

3. If you identify issues that require changes to the plan, edit the plan file directly.
4. Return a structured summary:
   - Issues found (with severity: blocking | warning)
   - Decisions required (see below)
   - Amendments made (list any edits to the plan file)
   - Status: PASS | PASS WITH WARNINGS | FAIL

IMPORTANT — you are running as a background subagent. You cannot interact with the user.
Do NOT call AskUserQuestion. Instead, for any point where you would normally stop and ask
the user to decide, write a structured entry in the ## Decisions Required section of your
output file and continue with the best-default option, documenting your assumption explicitly.

## Decisions Required format

For each decision point, write:

### Decision: <short title>
- **Severity:** blocking | judgement-call | defaulted
- **Question:** The exact question the user needs to answer.
- **Options:** A) ... B) ... (C) ... if applicable)
- **Assumed:** Which option you proceeded with and why.
- **Impact if wrong:** What changes in the plan if the user picks a different option.

Severity levels:
- `blocking` — you cannot proceed or make a safe default; you have written a FAIL status
  and stopped reviewing this section. The main session MUST get a human answer before
  the next round.
- `judgement-call` — you made a reasonable default but the user should consciously accept
  it; different teams would answer differently. Does not block the round.
- `defaulted` — you made an obvious/safe default; flagging for transparency only. User
  does not need to respond unless they disagree.
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
- **plan-ux-review**: Evaluate the feature through the eyes of an S3DF scientist — discoverability,
  first-use clarity, documentation quality, error UX, and workflow fit. Only runs when the feature
  has direct user-facing surface area.

5. **Poll all background agents** until every one completes. Use the bundled helper script
   — do not construct ad-hoc bash commands inline:

   ```bash
   # SKILL_DIR is the directory containing this SKILL.md file
   bash $SKILL_DIR/poll-round.sh <review_dir> <round> <active_reviewer_codes...>
   # e.g.
   bash ~/.claude/skills/full-review/poll-round.sh todo/review/007-my-feature 1 dr ar er dc
   ```

   The script prints one status line per reviewer and exits `0` when all are done, `1` if
   any are still running. Reviewer codes: `dr` deep-research, `ar` plan-arch-review,
   `er` plan-eng-review, `dc` plan-doc-review, `sr` security-review.

   After each poll, emit the status table as plain text (not a code block):

   ⏳ #NNN Round N — in progress  (elapsed: Xs)
   ──────────────────────────────────────────────────────────────
   Reviewer             Status            Early signal
   ──────────────────────────────────────────────────────────────
   <poll-round.sh output here>
   ──────────────────────────────────────────────────────────────

   Wait **3 minutes** between polls. Do not call the script more frequently — each status
   table emitted costs tokens. Poll → render table → sleep 180 → repeat.

   **Handling truncated agents:** if an agent's TaskOutput indicates a context/timeout error,
   or its output file ends mid-section without a `## Status` line:
   - Mark it `⚠️ truncated` in the table
   - Read whatever partial output exists in its file
   - Note in the round dashboard which sections were completed vs missed
   - Do NOT re-run the agent automatically — present the partial findings and ask the user
     whether to re-run that reviewer alone before proceeding

6. Once all agents are complete (or truncated), consolidate using the bundled helper script
   — do not construct ad-hoc bash or read files manually:

   ```bash
   bash ~/.claude/skills/full-review/consolidate-round.sh <review_dir> <round> <reviewer_codes...>
   # e.g.
   bash ~/.claude/skills/full-review/consolidate-round.sh todo/review/007-my-feature 1 dr ar er dc sr
   ```

   The script extracts STATUS, AMENDED, DECISIONS, BLOCKING, and a ≤10-line SUMMARY for
   each reviewer — the minimum needed to build the round dashboard and surface decisions.
   Only read a reviewer's full output file directly if the script's SUMMARY is insufficient
   to determine the next action (e.g. a blocking decision needs its full text). Never read
   full files speculatively.

   For each reviewer record:
   - Status (from STATUS line)
   - Decisions required (BLOCKING count > 0 → read ## Decisions Required from that file only)
   - Amendments made (from AMENDED line)
   - Summary bullets (from SUMMARY section)

6. **Surface decisions before the round dashboard.** If any reviewer wrote `## Decisions Required`
   entries, present them to the user now — before showing the round dashboard or deciding whether
   to iterate. Group by severity:

   a. **`blocking` decisions first** — work through them one at a time, in order. For each:

      1. Present the decision as plain text (not a code block):

         🛑 BLOCKING DECISION <M> of <total> — <reviewer name>
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         ❓ <the question>

         Options:
           A) ...
           B) ...

         ⚠️  The review cannot proceed until this is answered.

      2. Wait for the user's answer.
      3. **Mark this decision resolved.** Update the plan file to reflect the choice.
         Note the answer in the reviewer's output file.
      4. **Do not re-present this decision again.** Move immediately to the next unresolved
         blocking decision (M+1), or to the judgement-call step if all blocking decisions
         are answered.

      Never re-show a decision the user has already answered. Track which decisions have
      been resolved and which remain. If the user has answered decision 1, present decision
      2 — not decision 1 again.

   b. **`judgement-call` decisions** — present all of them together in a single numbered list
      after blocking decisions are resolved. Ask the user to confirm, override, or accept the
      defaults. One confirmation call covers all judgement-calls in a round.

      Format the judgement-call group as plain text (not a code block):

      🤔 JUDGEMENT CALLS — please confirm or override  (<N> decisions)
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      1. [<reviewer>] <question> → defaulted to: <assumed>
      2. [<reviewer>] <question> → defaulted to: <assumed>
      ...

      Reply "ok" to accept all defaults, or specify overrides by number.

   c. **`defaulted` decisions** — list them as plain text (not a code block):

      ℹ️  <N> minor defaults taken — see reviewer output files for details.

      No user action required unless they want to override.

   Only after all blocking decisions are answered and judgement-calls are confirmed, proceed to
   the round dashboard.

7. Show the round dashboard as plain text (not a code block):

   #NNN Round N complete
   ──────────────────────────────────────────────────────────────────
   deep-research        ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC   amended: Y/N   decisions: N
   plan-arch-review     ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC   amended: Y/N   decisions: N
   plan-eng-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC   amended: Y/N   decisions: N
   plan-doc-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC   amended: Y/N   decisions: N
   security-review      ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC   amended: Y/N   decisions: N
   plan-ux-review       ✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC   amended: Y/N   decisions: N
   ──────────────────────────────────────────────────────────────────
   Decisions resolved this round: N blocking / N judgement-call / N defaulted
   Plan amended this round: YES → starting Round N+1 | NO → board complete

`✂️ TRUNC` — agent hit context limit; note which sections were reached vs missed.

8. **Decide whether to iterate — automatically, no prompt needed:**
   - If **any reviewer amended the plan** this round → start the next round. In Round 2+,
     only re-run reviewers that either **amended the plan** or **were truncated** in the
     previous round — reviewers that passed cleanly do not need to re-review unless the
     amendments touch their domain. State which reviewers are being skipped and why.
   - If **no reviewer amended the plan** this round → board is complete, proceed to summary
   - If any reviewer has status **FAIL** (unresolved blocking issues) → **stop**. Do not start
     another round. Tell the user which issues must be resolved before continuing.
   - If any reviewer is **truncated** → ask the user whether to re-run it alone before
     deciding on the round outcome. A truncated reviewer is not a pass.

9. If **Round 3 completes with amendments still happening**: stop. Tell the user the plan has
   not stabilised after 3 rounds and list the outstanding changes still being triggered.

---

## Step 3: Final summary

After the board completes (or is halted), produce the final summary as plain text (not a code block):

   FULL REVIEW — FINAL SUMMARY  #NNN Round N
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
   plan-ux-review       {✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP}  {N issues}
   ------------------------------------------------------------
   ADRs written:          {N}  (in docs/adr/)
   Test plan written:     {Y/N}  (in todo/ task file)
   Doc gaps added:        {N}
   Accepted warnings:     {N}
   Blocking issues:       {N}
   ------------------------------------------------------------
   Decisions resolved:    {N blocking} / {N judgement-call} / {N defaulted}
   Unresolved decisions:  {N}  ← non-zero means the plan has open assumptions
   ------------------------------------------------------------
   VERDICT:  CLEAR TO BUILD | BLOCKED | CLEAR WITH WARNINGS | UNSTABLE
   ============================================================

**CLEAR TO BUILD** — all reviewers passed in the final round, no unresolved issues.

**CLEAR WITH WARNINGS** — all reviewers passed, but the user accepted risk on one or more issues.
List the accepted warnings explicitly so they can be revisited post-ship.

**BLOCKED** — one or more reviewers failed with unresolved issues. List the blocking issues and
which reviewer they belong to.

**UNSTABLE** — the plan did not stabilise within 3 rounds. List what was still changing and why.

---

## After the review

If verdict is **CLEAR TO BUILD** or **CLEAR WITH WARNINGS**:

1. **Merge review artefacts into the task file.** Append a `## Board Review` section to
   `todo/<slug>.md` with a condensed summary of the board's findings:

   ```markdown
   ## Board Review

   **Verdict:** CLEAR TO BUILD | CLEAR WITH WARNINGS
   **Date:** YYYY-MM-DD
   **Rounds:** N

   | Reviewer | Result | Amended | Key findings |
   |---|---|---|---|
   | deep-research | ✅ PASS | N | <one-line summary> |
   | plan-arch-review | ✅ PASS | Y | <one-line summary> |
   | plan-eng-review | ✅ PASS | N | <one-line summary> |
   | plan-doc-review | ✅ PASS | N | <one-line summary> |
   | security-review | ⚠️ WARN | N | <one-line summary> |

   **Accepted warnings:** <list any warnings the user accepted, or "none">
   **ADRs written:** <N> (in docs/adr/)
   ```

2. **Delete the review artefact directory:**
   ```bash
   rm -rf todo/review/<slug>/
   ```

3. **Update the task file and `TODO.md`:**
   - Set `**Status:**` in the task file to `🔍 Reviewed`
   - Update `TODO.md` — flip the status column to `🔍 Reviewed`

4. **Commit everything together:**
   ```bash
   git add todo/<slug>.md TODO.md
   git commit -m "docs(todo): merge board review into #NNN task file [full-review]"
   ```

Then tell the user (substituting the actual TODO number and slug):

   ✅ #NNN <title> — CLEAR TO BUILD

   #NNN todo/<slug>.md
        ↓
   /project-management   ← track progress, keep TODO.md in sync
        ↓
   /tdd-workflow         ← tests first, then implementation
        ↓
   /plan-closeout #NNN   ← close out task, apply doc updates, sync TODO.md
        ↓
   /prod-release         ← promote through environments

If verdict is **BLOCKED** or **UNSTABLE**:

1. **Merge review artefacts into the task file.** Append a `## Board Review` section as above,
   but with verdict BLOCKED or UNSTABLE and a clear list of blocking issues.

2. **Delete the review artefact directory:**
   ```bash
   rm -rf todo/review/<slug>/
   ```

3. **Update the task file and `TODO.md`:**
   - Set `**Status:**` in the task file back to `⬜ Open`
   - Update `TODO.md` — flip the status column back to `⬜ Open`
   - Add a note in the task file's Problems & Solutions section describing what blocked the
     review and which issues must be resolved before re-running.

4. **Commit everything together:**
   ```bash
   git add todo/<slug>.md TODO.md
   git commit -m "docs(todo): merge blocked board review into #NNN task file [full-review]"
   ```

Then tell the user:

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
