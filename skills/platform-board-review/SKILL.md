---
name: platform-board-review
description: Orchestrates the platform board review pipeline — runs platform-arch-review, platform-capacity-review, platform-security-review, platform-ops-review, platform-eng-review, and platform-doc-review in parallel, then re-runs the full board if any reviewer amends the plan. Iterates until all reviewers pass in the same round with no changes. Use when asked to "run a platform review", "gate this platform change", "board review this", or "is this ready to apply to the cluster?".
---

# Platform Board Review

Runs six board reviewers in parallel. If any reviewer amends the plan, the whole board re-reviews the updated plan. The round repeats until all reviewers pass in the same round without further changes. Maximum 3 rounds.

**Model routing:** Triage is `haiku`-eligible. Each reviewer runs at its own routing level — `platform-arch-review` and `platform-security-review` run at **`opus`**; capacity, ops, eng, and doc reviewers run at **`sonnet`**.

**This skill assumes a platform plan already exists.** If you don't have one yet, run `/platform-draft` first.

**This skill does not implement anything.** It convenes the board, tracks rounds, and tells you when you're clear to apply.

---

## The board model

```
/platform-board-review (main session)
      │
      ▼
  [Triage]      which reviewers are relevant for this change?
      │
      ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  ROUND N  (all reviewers launched as parallel subagents)        │
  │                                                                 │
  │  subagent: platform-arch-review     → platform/review/<slug>/round-N-ar.md │
  │  subagent: platform-capacity-review → platform/review/<slug>/round-N-cr.md │
  │  subagent: platform-security-review → platform/review/<slug>/round-N-sr.md │
  │  subagent: platform-ops-review      → platform/review/<slug>/round-N-or.md │
  │  subagent: platform-eng-review      → platform/review/<slug>/round-N-er.md │
  │  subagent: platform-doc-review      → platform/review/<slug>/round-N-dc.md │
  │                                                                 │
  │  main session reads all outputs, collects Decisions Required    │
  │  blocking decisions? ──────────────────── AskUserQuestion (×N) │
  │  judgement-calls?   ──────────────────── AskUserQuestion (×1)  │
  │                                                                 │
  │  if any subagent amended the plan ──────────────────────────────┤
  │                                                     next round  │
  └─────────────────────────────────────────────────────────────────┘
      │  all pass in same round, no amendments
      ▼
  [Clear to apply]
```

---

## Step 0: Locate the plan

1. **If the user named a task number** (e.g. "review platform 003"): glob `platform/<number>-*.md` and read it.
2. **Otherwise**: check `PLATFORM.md` for the in-progress task and read its file.

If no plan is found, stop:
> "No platform plan found. Run `/platform-draft` first to produce a design document, then come back to `/platform-board-review`."

Summarise the plan in 2-3 sentences so the user can confirm you've read the right thing.

**Immediately after confirming the plan**, update the task file and `PLATFORM.md`:
- Set `**Status:**` in the task file to `🔎 In Review`
- Update `PLATFORM.md` — flip the status column to `🔎 In Review`

**Context discipline:** Store the plan as a file path only. Do not hold full plan content in working memory across rounds — subagents read it from disk. After consolidating a round, drop reviewer output content from working memory.

---

## Step 1: Triage — which reviewers apply?

```
REVIEWER                  SKIP IF...
──────────────────────────────────────────────────────────────────
platform-arch-review      change is purely operational (tuning replicas,
                          updating a ConfigMap) with no topology or
                          boundary changes
platform-capacity-review  change removes workloads or is purely config
                          with no new resource consumption
platform-security-review  change has no new workloads, no RBAC changes,
                          no network policy changes, no new secrets
platform-ops-review       change is purely infrastructure with no new
                          failure modes and no runbook impact
platform-eng-review       change is purely documentation or config with
                          no manifest changes
platform-doc-review       change is purely internal infra with no
                          operator or user-facing surface area
──────────────────────────────────────────────────────────────────
```

**Default: run all reviewers.** Only skip if the skip condition is clearly and unambiguously met.

Present triage as plain text, then immediately proceed:

```
Triage complete
──────────────────────────────────────────────────────
platform-arch-review      RUN | SKIP (reason)
platform-capacity-review  RUN | SKIP (reason)
platform-security-review  RUN | SKIP (reason)
platform-ops-review       RUN | SKIP (reason)
platform-eng-review       RUN | SKIP (reason)
platform-doc-review       RUN | SKIP (reason)
──────────────────────────────────────────────────────
Starting Round 1...
```

---

## Step 2: Board rounds

Each board member runs as a **parallel subagent** — all launched in a single message with `run_in_background: true`.

Run up to **3 rounds**. In each round:

1. Announce: "#NNN — Starting Round N — launching board subagents in parallel."

2. Create output directory: `platform/review/<slug>/`

3. **Prepare a trimmed plan excerpt for each reviewer:**

   | Reviewer | Sections to include |
   |---|---|
   | platform-arch-review | Problem Statement, Goals, Platform Design (full), Non-Goals, Open Questions |
   | platform-capacity-review | Problem Statement, Goals, Platform Design (Capacity Assessment section), Non-Goals |
   | platform-security-review | Problem Statement, Platform Design (Security Posture section + topology), Open Questions |
   | platform-ops-review | Problem Statement, Goals, Platform Design (Operational Readiness section), Implementation Plan |
   | platform-eng-review | Problem Statement, Goals, Platform Design (full), Implementation Plan, Implementation Checklist |
   | platform-doc-review | Problem Statement, Goals, Non-Goals, Implementation Plan (step titles only) |

4. **Launch all relevant reviewers as background subagents in a single message.**

   Each subagent receives:

```
You are a [REVIEWER NAME] subagent in a platform board review.

Your role: [one-line role description]

Plan file: <path to platform task file>
[Round 1 only] Plan excerpt (sections relevant to your review):
<trimmed plan content>

[Round 2+ only] Plan was amended in Round N: <one-line summary of changes>
Read the plan file directly from disk: <path>

Context budget warning: you are running as a background subagent with a finite
context window. Prioritise ruthlessly. Write findings in bullet points, not prose.
Stop adding findings once output file exceeds ~800 lines.

Your job:
1. Perform a thorough review using the /[skill-name] skill guidelines.
2. Write findings incrementally to: platform/review/<slug>/round-<N>-<reviewer>.md

   Use this exact structure:

   ## Summary
   <3-5 bullet points — most important findings, written last>

   ## Issues
   <one line per issue: SEVERITY | area | description>

   ## Decisions Required
   <structured entries — see format below>

   ## Amendments
   <list of edits made to the plan file>

   ## Status
   PASS | PASS WITH WARNINGS | FAIL

3. If issues require plan changes, edit the plan file directly.
4. Return: issues found, decisions required, amendments made, status.

IMPORTANT: You cannot interact with the user. For any decision point, write a
structured entry in ## Decisions Required and continue with the best-default option.

## Decisions Required format

### Decision: <short title>
- **Severity:** blocking | judgement-call | defaulted
- **Question:** The exact question the user needs to answer.
- **Options:** A) ... B) ...
- **Assumed:** Which option you proceeded with and why.
- **Impact if wrong:** What changes if the user picks differently.
```

5. **Poll all background agents** until every one completes.

   After each poll, emit the status table:

   ```
   ⏳ #NNN Round N — in progress  (elapsed: Xs)
   ──────────────────────────────────────────────────────────────
   Reviewer                  Status          Early signal
   ──────────────────────────────────────────────────────────────
   platform-arch-review      ...
   platform-capacity-review  ...
   platform-security-review  ...
   platform-ops-review       ...
   platform-eng-review       ...
   platform-doc-review       ...
   ──────────────────────────────────────────────────────────────
   ```

   Wait **3 minutes** between polls.

6. **Surface decisions before the round dashboard:**

   a. **Blocking decisions** — one at a time, wait for user answer before proceeding to next.

   ```
   🛑 BLOCKING DECISION <M> of <total> — <reviewer>
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ❓ <the question>

   Options:
     A) ...
     B) ...

   ⚠️  The review cannot proceed until this is answered.
   ```

   b. **Judgement-call decisions** — all together in one list after blocking decisions are resolved.

   c. **Defaulted decisions** — list as plain text, no action required.

7. **Show the round dashboard:**

   ```
   #NNN Round N complete
   ──────────────────────────────────────────────────────────────────
   platform-arch-review      ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
   platform-capacity-review  ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
   platform-security-review  ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
   platform-ops-review       ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
   platform-eng-review       ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
   platform-doc-review       ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
   ──────────────────────────────────────────────────────────────────
   Plan amended this round: YES → starting Round N+1 | NO → board complete
   ```

8. **Decide whether to iterate:**
   - Any reviewer amended the plan → start next round (only re-run reviewers that amended or were truncated)
   - No amendments → board complete
   - Any FAIL with unresolved blocking issues → stop, list issues
   - Any truncated reviewer → ask user whether to re-run before deciding

9. If **Round 3 completes with amendments still happening**: stop. Tell the user the plan has not stabilised.

---

## Step 3: Final summary

```
PLATFORM BOARD REVIEW — FINAL SUMMARY  #NNN Round N
============================================================
Plan:    {plan file}
Branch:  {branch}
Date:    {date}
Rounds:  {N completed}
------------------------------------------------------------
platform-arch-review      {✅/⚠️/❌/—}  {N issues}
platform-capacity-review  {✅/⚠️/❌/—}  {N issues}
platform-security-review  {✅/⚠️/❌/—}  {N issues}
platform-ops-review       {✅/⚠️/❌/—}  {N issues}
platform-eng-review       {✅/⚠️/❌/—}  {N issues}
platform-doc-review       {✅/⚠️/❌/—}  {N issues}
------------------------------------------------------------
ADRs written:          {N}
Runbook gaps:          {N}
Capacity blockers:     {N}
Accepted warnings:     {N}
Blocking issues:       {N}
------------------------------------------------------------
Decisions resolved:    {N blocking} / {N judgement-call} / {N defaulted}
Unresolved decisions:  {N}
------------------------------------------------------------
VERDICT:  CLEAR TO APPLY | BLOCKED | CLEAR WITH WARNINGS | UNSTABLE
============================================================
```

**CLEAR TO APPLY** — all reviewers passed, no unresolved issues.
**CLEAR WITH WARNINGS** — all passed, user accepted risk on some issues.
**BLOCKED** — one or more reviewers failed. List blocking issues.
**UNSTABLE** — plan did not stabilise in 3 rounds.

---

## After the review

If verdict is **CLEAR TO APPLY** or **CLEAR WITH WARNINGS**:

1. Append a `## Board Review` section to the task file.
2. Delete the review artefact directory: `rm -rf platform/review/<slug>/`
3. Update the task file and `PLATFORM.md`: status → `🔍 Reviewed`
4. Commit: `git add platform/<slug>.md PLATFORM.md && git commit -m "docs(platform): merge board review into #NNN [platform-board-review]"`

Then tell the user:

```
✅ #NNN <title> — CLEAR TO APPLY

#NNN platform/<slug>.md
     ↓
/platform-workflow   ← track progress, keep PLATFORM.md in sync
     ↓
/k8s-deploy          ← implement the changes
     ↓
/platform-workflow   ← close out, mark 🚀 Applied
```

If verdict is **BLOCKED** or **UNSTABLE**:

1. Append the board review section with verdict and blocking issues.
2. Delete the review artefact directory.
3. Status → `⬜ Open` (revert to pre-review).
4. Commit.

> "Resolve the issues above, then re-run `/platform-board-review`."
