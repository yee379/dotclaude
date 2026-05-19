---
name: board-review
description: Orchestrates the board review pipeline for codebase and platform changes. Runs mode-appropriate reviewers in parallel, iterates until all pass in the same round. Use when asked to "run a full review", "board review this", "gate this plan", or "is this ready to apply/build?".
origin: ECC
---

# Board Review

Runs a board of parallel reviewers. If any reviewer amends the plan, the whole board re-reviews the updated plan. The round repeats until all reviewers pass in the same round without further changes. Maximum 3 rounds.

**This skill assumes a plan already exists.** If you don't have one yet, run `/codebase-draft-prd` (codebase) or `/platform-draft-prd` (platform) first.

**This skill does not implement anything.** It convenes the board, tracks rounds, and tells you when you're clear to proceed.

---

## Mode detection

| Signal in the plan or user message | Mode |
|---|---|
| `[INFRA]`, "cluster", "k8s", "Helm", "namespace", "workload", "PVC", "node", "kubectl" | **platform** |
| None of the above — software design, API, feature, refactor | **codebase** |

**At Step 0, read `references/[mode]-board.md`** (absolute path: `~/.claude/skills/board-review/references/[mode]-board.md`). All mode-specific configuration lives there: reviewer list, model routing, triage table, plan excerpt routing, priority hierarchy, round dashboard rows, final summary metrics, verdict labels, no-plan message, after-review next steps, and commit messages. Every step below that refers to "the loaded config" means that file.

---

## The board model

```
/board-review (main session)
      │
      ▼
  [Mode detect → load config]
      │
      ▼
  [Triage]      which reviewers are relevant for this change?
      │
      ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  ROUND N  (all reviewers launched as parallel subagents)        │
  │                                                                 │
  │  subagents → todo/review/<slug>/round-N-<code>.md each          │
  │                                                                 │
  │  main session reads all outputs, collects Decisions Required    │
  │                                                                 │
  │  blocking decisions? ──────────────────── AskUserQuestion (×N) │
  │  judgement-calls?   ──────────────────── AskUserQuestion (×1)  │
  │  defaulted?         ──────────────────── listed, no action     │
  │                                                                 │
  │  if any subagent amended the plan ──────────────────────────────┤
  │                                                     next round  │
  └─────────────────────────────────────────────────────────────────┘
      │  all pass in same round, no amendments
      ▼
  [Clear to proceed]
```

---

## Step 0: Locate the plan

1. **If the user named a task number** (e.g. "review 027", "board review #3"): glob `todo/<number>-*.md` and open the first match.
2. **Otherwise**, check in order:
   - `todo/` — find the in-progress task (`🔄 In Progress` in `TODO.md`) and read its file
   - `DESIGN.md` or `design-doc.md` in the repo root or `.claude/`
   - `git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~5)...HEAD --stat 2>/dev/null | head -30`

If no plan is found, **stop** using the no-plan message from the loaded config.

Summarise the plan in 2-3 sentences so the user can confirm you've read the right thing.

**Immediately after confirming the plan**, update the task file and `TODO.md`:
- Set `**Status:**` in the task file to `🔎 In Review`
- Update `TODO.md` — flip the status column to `🔎 In Review`

**Main session context discipline:**
- Store the plan as a **file path only**. Do not hold full plan content in working memory across rounds — subagents read it from disk.
- After launching subagents, do not re-read the plan file unless making a specific edit in response to a blocking decision.
- After consolidating a round, drop reviewer output content from working memory. Only keep the round dashboard summary.
- Never paste full file contents when a file path reference will do. Goal: main session context grows ~500 tokens per round, not ~10k.

---

## Step 1: Triage — which reviewers apply?

Use the triage table from the loaded config. **Default: run all reviewers.** Only skip if the skip condition is clearly and unambiguously met. When in doubt, run it.

Present the triage result as plain prose — **NOT inside backticks**. Immediately proceed to Step 2. Example:

```
Triage complete
──────────────────────────────────────────────────────
<reviewer name>    RUN | SKIP (reason)
...
──────────────────────────────────────────────────────
Starting Round 1...
```

IMPORTANT: Do not wrap this in ``` backticks. Emit it as raw text in your reply.

---

## Step 2: Board rounds

Each board member runs as a **parallel subagent** — all launched in a single message with `run_in_background: true`.

Run up to **3 rounds**. In each round:

1. Announce: "#NNN — Starting Round N — launching board subagents in parallel."

2. Create the output directory: `todo/review/<slug>/` (slug = task file name without extension).

3. **Prepare a trimmed plan excerpt for each reviewer** using the plan excerpt routing table from the loaded config. Do not paste the full task file into every subagent. If the task file has no Design/Platform Design section, include the full file for all reviewers.

4. **Launch all relevant reviewers as background subagents in a single message.**

   **Round 1:** paste the trimmed plan excerpt (only round where content is pasted).
   **Round 2+:** pass only the file path and a one-line summary of what changed.

   Each subagent receives:

```
You are a [REVIEWER NAME] subagent in a board review.

Your role: [one-line role from loaded config]

Plan file: <path to task file>
Output file: todo/review/<slug>/round-<N>-<code>.md

[Round 1 only] Plan excerpt (sections relevant to your review):
<trimmed plan content>

[Round 2+ only] Plan was amended in Round N: <one-line summary of changes>
Read the plan file directly from disk: <path> — do not rely on any previously pasted content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE-FIRST RULE — read this before doing anything else
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your FIRST action must be to create the output file with a skeleton:

  Write to: todo/review/<slug>/round-<N>-<code>.md

  Initial content:

    ## Summary
    _(written last — do not fill in yet)_

    ## Issues
    _(in progress)_

    ## Decisions Required
    _(in progress)_

    ## Amendments
    _(in progress)_

    ## Status
    IN PROGRESS

After writing the skeleton, proceed with your review.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Context budget warning: you are a background subagent with a finite context window.
Prioritise ruthlessly:
- Complete your highest-value sections first (see priority hierarchy in the loaded config)
- Write findings in bullet points, not prose — one line per issue
- Stop adding findings once your output file exceeds ~800 lines
- Fewer sections deeply > more sections shallowly

Your job:
1. Perform a thorough [REVIEWER NAME] review using the /[skill-name] skill guidelines.

2. Write findings incrementally — after EACH section completes, do NOT buffer:

   CHECKPOINT PATTERN after each section:
   a. Append the section's findings to ## Issues (one line per issue)
   b. Append any decision entries to ## Decisions Required
   c. Append any plan edits to ## Amendments
   d. Update ## Status (IN PROGRESS / FAIL / PASS WITH WARNINGS)

   Final structure:

     ## Summary
     <3-5 bullet points — most important findings, written LAST>

     ## Issues
     <SEVERITY | area | description>
     e.g. blocking | auth | JWT expiry not validated on refresh endpoint

     ## Decisions Required
     <structured entries — see format below>

     ## Amendments
     <list of edits made to the plan file, one line each>

     ## Status
     PASS | PASS WITH WARNINGS | FAIL

   Write ## Summary LAST only after all other sections are complete.

3. If issues require plan changes, edit the plan file directly, then append to ## Amendments.

4. Return: issues found, decisions required, amendments made, status.

IMPORTANT — you cannot interact with the user. Do NOT call AskUserQuestion. For any
decision point, write a structured entry in ## Decisions Required and continue with
the best-default option.

## Decisions Required format

### Decision: <short title>
- **Severity:** blocking | judgement-call | defaulted
- **Question:** The exact question the user needs to answer.
- **Options:** A) ... B) ...
- **Assumed:** Which option you proceeded with and why.
- **Impact if wrong:** What changes if the user picks differently.

Severity:
- `blocking` — cannot proceed safely; written FAIL and stopped. Main session must get human answer.
- `judgement-call` — reasonable default taken; user should consciously accept it.
- `defaulted` — obvious/safe default; flagging for transparency only.
```

5. **Poll all background agents** until every one completes:

   ```bash
   bash ~/.claude/skills/board-review/poll-round.sh <review_dir> <round> <active_reviewer_codes...>
   # e.g.
   bash ~/.claude/skills/board-review/poll-round.sh todo/review/027-my-feature 1 dr ar er dc sr
   ```

   The script prints one status line per reviewer and exits `0` when all are done, `1` if any are still running. Reviewer codes are defined in the loaded config.

   After each poll, emit the status table as plain prose — **NOT inside backticks**:

   ```
   ⏳ #NNN Round N — in progress  (elapsed: Xs)
   ──────────────────────────────────────────────────────────────
   Reviewer             Status            Early signal
   ──────────────────────────────────────────────────────────────
   <poll-round.sh output here>
   ──────────────────────────────────────────────────────────────
   ```

   Wait **3 minutes** between polls.

   **Handling truncated agents:** if an agent's output file ends mid-section without a `## Status` line:
   - Mark it `⚠️ truncated` in the table
   - Read whatever partial output exists
   - Do NOT re-run automatically — present partial findings and ask the user whether to re-run before proceeding

6. Once all agents are complete, consolidate:

   ```bash
   bash ~/.claude/skills/board-review/consolidate-round.sh <review_dir> <round> <reviewer_codes...>
   ```

   The script extracts STATUS, AMENDED, DECISIONS, BLOCKING, and a ≤10-line SUMMARY per reviewer. Only read a reviewer's full output file if the script's SUMMARY is insufficient (e.g. a blocking decision needs its full text). Never read full files speculatively.

7. **Surface decisions before the round dashboard.** Group by severity:

   a. **`blocking` decisions first** — one at a time, in order. As plain prose, NOT backticks:

   ```
   🛑 BLOCKING DECISION <M> of <total> — <reviewer name>
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ❓ <the question>

   Options:
     A) ...
     B) ...

   ⚠️  The review cannot proceed until this is answered.
   ```

   Wait for the user's answer. Mark resolved, update the plan file, note in reviewer output. Do not re-present answered decisions.

   b. **`judgement-call` decisions** — all together after blocking decisions are resolved. As plain prose:

   ```
   🤔 JUDGEMENT CALLS — please confirm or override  (<N> decisions)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   1. [<reviewer>] <question> → defaulted to: <assumed>
   2. [<reviewer>] <question> → defaulted to: <assumed>

   Reply "ok" to accept all defaults, or specify overrides by number.
   ```

   c. **`defaulted` decisions** — list as plain text: `ℹ️  <N> minor defaults taken.`

8. **Show the round dashboard** as plain prose, NOT backticks:

   ```
   #NNN Round N complete
   ──────────────────────────────────────────────────────────────────
   <rows from loaded config>
   ──────────────────────────────────────────────────────────────────
   Decisions resolved this round: N blocking / N judgement-call / N defaulted
   Plan amended this round: YES → starting Round N+1 | NO → board complete
   ```

   Status symbols: `✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC`

9. **Decide whether to iterate — automatically:**
   - Any reviewer amended the plan → start next round; re-run only reviewers that amended or were truncated
   - No amendments → board complete
   - Any FAIL with unresolved blocking issues → stop; list issues
   - Any truncated reviewer → ask user whether to re-run before deciding
   - Round 3 with amendments still happening → stop; plan has not stabilised

---

## Step 3: Final summary

As plain prose, NOT backticks:

```
BOARD REVIEW — FINAL SUMMARY  #NNN Round N
============================================================
Plan:    {plan file}
Branch:  {branch}
Date:    {date}
Rounds:  {N completed}
------------------------------------------------------------
<metrics block from loaded config>
------------------------------------------------------------
Decisions resolved:    {N blocking} / {N judgement-call} / {N defaulted}
Unresolved decisions:  {N}
------------------------------------------------------------
VERDICT:  <verdict from loaded config>
============================================================
```

Verdict definitions (from loaded config): CLEAR TO BUILD / CLEAR TO APPLY / CLEAR WITH WARNINGS / BLOCKED / UNSTABLE.

---

## After the review

**All reviewer output must be persisted into the task file before the artefact directory is deleted.**

1. **Append a `## Board Review` section to `todo/<slug>.md`:**

   **Part A — Summary table:**
   ```markdown
   ## Board Review

   **Verdict:** <verdict>
   **Date:** YYYY-MM-DD
   **Rounds:** N

   | Reviewer | Result | Amended | Key findings |
   |---|---|---|---|
   | <reviewer rows from loaded config> |

   **Accepted warnings:** <list or "none">
   **Unresolved decisions:** <N> (or "none")
   ```

   **Part B — Full reviewer output** (one collapsible block per reviewer that ran):
   ```markdown
   ### Reviewer output

   <details>
   <summary><reviewer name> — Round N (<status>)</summary>

   <!-- paste full contents of todo/review/<slug>/round-N-<code>.md here -->

   </details>
   ```

   For multi-round reviews, include only the final round's output per reviewer.
   If truncated: `⚠️ Truncated — output is partial; sections reached: <list>`

2. **Delete the review artefact directory** — only after the task file is written:
   ```bash
   rm -rf todo/review/<slug>/
   ```

3. **Update the task file and `TODO.md`:**
   - CLEAR verdict: status → `🔍 Reviewed` in both files
   - BLOCKED or UNSTABLE: status → `⬜ Open`; add a note on what blocked the review

4. **Commit** using the commit message format from the loaded config.

5. Tell the user the verdict using the after-review next steps from the loaded config.

---

## Formatting rules

- Show the round dashboard after every round.
- Never batch issues across reviewers into a single question.
- If the user asks to skip a reviewer mid-round, use AskUserQuestion to confirm — skipping is accepting the risk that reviewer would have caught.
- If the user interrupts and resumes later, re-show the last round dashboard immediately.
- When starting a new round: "Plan was amended in Round N: {summary}. Starting Round N+1."
