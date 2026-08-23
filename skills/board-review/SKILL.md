---
name: board-review
description: Orchestrates the board review pipeline for codebase and platform changes. Runs mode-appropriate reviewers in parallel, iterates until all pass in the same round. Use when asked to "run a full review", "board review this", "gate this plan", or "is this ready to apply/build?".
origin: ECC
---

# Board Review

Runs a board of parallel reviewers. If a reviewer amends the plan in a way that changes what gets
built, the whole board re-reviews the updated plan. The round repeats until all reviewers pass in the
same round without further design changes. Maximum 3 rounds.

**The board reviews the design, not the prose.** Step 1.5 exists to strip out the self-inflicted
precision defects before Round 1, so reviewers spend their budget on the design and the round count
measures the design's stability rather than the text's polish.

**This skill assumes a plan already exists.** If you don't have one yet, run `/draft-prd` first.

**This skill does not implement anything.** It convenes the board, tracks rounds, and tells you when you're clear to proceed.

---

## Mode detection

| Signal in the plan or user message | Mode |
|---|---|
| `[INFRA]`, "cluster", "k8s", "Helm", "namespace", "workload", "PVC", "node", "kubectl" | **platform** |
| None of the above — software design, API, feature, refactor | **codebase** |

**At Step 0, read `references/[mode]-board.md`** (absolute path: `~/.claude/skills/board-review/references/[mode]-board.md`). All mode-specific configuration lives there: reviewer list, model routing, triage table, plan excerpt routing, priority hierarchy, round dashboard rows, final summary metrics, verdict labels, no-plan message, after-review next steps, and commit messages. Every step below that refers to "the loaded config" means that file.

`references/subagent-protocol.md` holds the write-as-you-go output contract that every reviewer
subagent follows (skeleton file, per-checkpoint appends, suppressed AskUserQuestion, summary
last). The reviewer skills load it themselves — cite it in the dispatch prompt if a reviewer
appears to be buffering its findings to the end instead of streaming them.

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
  [Precision gate]  measure ground truth · run the sweep · fix inline
      │             (Step 1.5 — before any reviewer launches)
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
  │  any `design:` amendment ───────────────────────────────────────┤
  │  (`precision:` only → verify the edits, do not spend a round)    │
  │                                                     next round  │
  └─────────────────────────────────────────────────────────────────┘
      │  all pass in same round, no design amendments
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

## Step 1.5: Precision gate — run BEFORE Round 1

**The board's budget is finite and shared. Anything a reviewer spends on the plan disagreeing with
itself is not spent on the design.** In one three-round review, ~48 of 53 final-round amendments were
self-inflicted precision defects; only ~5 were real design findings, and the plan was marked UNSTABLE
on amendment *count* while zero blocking issues existed. Reviewers were not the problem — they were
handed a plan that generated work.

Two things must happen before any reviewer launches. Both are cheap; skipping either costs a round.

### a. Establish ground truth yourself

**Measure every load-bearing fact the plan reasons over, from a primary source, and correct the plan
before briefing anyone.** A wrong number in the plan becomes a wrong number in the Round 1 brief,
which reviewers then treat as given — and every downstream finding built on it is wasted work that
looks like a finding. This is not hypothetical: a count fed to Rounds 1 and 2 as ground truth was
wrong, and manufactured most of Round 2.

- Query the live system, run the command, read the config file. Not the plan's own claim about it.
- **Never accept a contested fact on reviewer consensus.** Three reviewers agreeing is not evidence;
  one primary-source check is. Every count corrected in that review was corrected by a direct
  measurement, and two of the three wrong values had passed a full round unchallenged.
- Where a fact cannot be measured now, say so in the brief explicitly: "unverified — treat as an
  assumption, not a given."
- **This is not a gag order on reviewers.** The `## Measured facts` block records where a number
  came from so nobody re-derives it just to restate it — it does not put the number's validity
  out of scope. A reviewer can and should still ask whether the right thing was measured, whether
  it's representative (peak vs. average, one node vs. the fleet), or whether the command behind it
  actually measures what its label claims. That's a design finding, not a precision one — tag it
  `design:` and name the check that would settle it.

### b. Run the plan's own precision sweep

Load `~/.claude/skills/draft-prd/references/precision-rules.md` and work its self-check against the
plan. **Fix what it finds now**, in the main session, before Round 1 — stale citations, duplicated
values, rules stated in three places, unscoped universal claims, requirements with no insertion
point, slices with no stated placement invariant.

`/draft-prd` Phase 11 should already have done this. It is repeated here because the gate belongs
where the cost is paid, and plans arrive from elsewhere.

Report as plain prose, NOT backticks:

```
Precision gate — #NNN
──────────────────────────────────────────────────────
Ground truth measured:  <N facts, from <source>>  (<M corrections made>)
Precision sweep:        <N items fixed>  (<breakdown>)
Plan length:            <L lines>
──────────────────────────────────────────────────────
```

If the gate makes substantive corrections, **say what they were** — the user needs to know the plan
they approved has changed. If it finds nothing, say that too.

---

## Step 2: Board rounds

Each board member runs as a **parallel subagent** — all launched in a single message with `run_in_background: true`. Launching this way is what makes them harness-tracked, which is what lets Step 5 wait on completion notifications instead of polling.

Run up to **3 rounds**. In each round:

1. Announce: "#NNN — Starting Round N — launching board subagents in parallel."

2. Create the output directory: `todo/review/<slug>/` (slug = task file name without extension).

3. **Prepare a trimmed plan excerpt for each reviewer** using the plan excerpt routing table from the loaded config. Do not paste the full task file into every subagent. If the task file has no Design/Platform Design section, include the full file for all reviewers.

4. **Launch all relevant reviewers as background subagents in a single message.**

   **Round 1:** paste the trimmed plan excerpt (only round where content is pasted).
   **Round 2+:** pass only the file path and a one-line summary of what changed.

   **State the round's bar in the dispatch prompt.** Each round has a different job, and a reviewer
   given no bar defaults to Round-1 breadth every time — which is what keeps plans amending forever:

   | Round | Bar to state verbatim in the prompt |
   |---|---|
   | 1 | "Full review. Raise anything that would change the design or the delivery order. Also include feasibility doubts and simpler/cheaper alternatives even where the plan as written would work — record these in `## Opportunities`, not as amendments; they cost nothing toward round iteration." |
   | 2 | "Reconciliation round. The plan was amended since you last saw it. Verify the amendments are correct and self-consistent. Do NOT re-raise matters settled in Round 1, and do NOT open new lines of enquiry unless an amendment created the problem." |
   | 3 | "Final round. Amend ONLY for a defect that would cause the implementation to be wrong, unsafe, or unbuildable. Wording, ordering, and stylistic improvements are explicitly out of scope — leave them. If you find nothing of that severity, return PASS with no amendments." |

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

    ## Opportunities
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
   b. Append any non-defect ideas — feasibility doubts, simpler/cheaper alternatives,
      things worth doing but not required — to ## Opportunities (one line each)
   c. Append any decision entries to ## Decisions Required
   d. Append any plan edits to ## Amendments
   e. Update ## Status (IN PROGRESS / FAIL / PASS WITH WARNINGS)

   Final structure:

     ## Summary
     <3-5 bullet points — most important findings, written LAST>

     ## Issues
     <SEVERITY | area | description>
     e.g. blocking | auth | JWT expiry not validated on refresh endpoint

     ## Opportunities
     <one line each — non-defect improvement ideas. These do NOT count toward the
     design:/precision: amendment ratio and do NOT drive round iteration; they are
     carried into the task file's follow-ups by the orchestrator.>
     e.g. the retry loop could be replaced by the existing backoff helper in utils/retry.py

     ## Decisions Required
     <structured entries — see format below>

     ## Amendments
     <one line each, EACH TAGGED design: or precision: — see classification below>

     ## Status
     PASS | PASS WITH WARNINGS | FAIL

   Write ## Summary LAST only after all other sections are complete.

   ## Amendment classification — tag every amendment

   Prefix each line in ## Amendments with exactly one tag:

   - `design:`    — the plan, as written, would produce wrong, unsafe, or unbuildable
                    behaviour. Fixing it changes what gets built.
   - `precision:` — the plan disagrees with itself or with the repo: a stale citation, a
                    duplicated value, a rule restated inconsistently, an over-scoped claim,
                    a misplaced slice row. Fixing it changes only the text.

   End the section with a count line: `TOTAL: N design, M precision`

   This tag drives the board's stabilisation decision, so it must be honest in both
   directions. A design defect tagged `precision:` gets a plan shipped with a real bug in
   it. A precision fix tagged `design:` forces an unnecessary round.

   Ceiling on precision amendments: if you are about to make more than ~10, stop, make the
   most valuable ones, and record the rest as ONE issue line — "N further precision defects
   of the same class, listed below" — rather than N amendments. A hundred cosmetic edits and
   one real finding are not the same signal, and the board cannot tell them apart if they
   arrive as an undifferentiated list.

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

5. **Wait for the harness to tell you they finished. Do not poll on a timer.**

   Background subagents are harness-tracked: when one exits, you are re-invoked with a
   task notification naming that agent. That notification *is* the process ending — a
   strictly stronger signal than inspecting a file the agent is still writing to.

   - Do **not** `sleep`, do **not** schedule a wakeup, do **not** re-run a status check on a
     fixed interval. A timed loop tells you nothing the notification won't, and every wake
     re-reads the session context.
   - **Count notifications.** The round is complete when you have one per launched reviewer.
   - Between notifications, do nothing. Do not start Step 6 early on a partial set.

   `poll-round.sh` is a **renderer and a fallback**, not the completion signal. Run it once per
   notification to draw the dashboard for the user:

   ```bash
   bash ~/.claude/skills/board-review/poll-round.sh <review_dir> <round> <active_reviewer_codes...>
   # e.g.
   bash ~/.claude/skills/board-review/poll-round.sh todo/review/027-my-feature 1 dr ar er dc sr
   ```

   It prints one line per reviewer and exits `0` only when every file carries a **terminal**
   `## Status` (`PASS` / `PASS WITH WARNINGS` / `FAIL`). `IN PROGRESS` counts as running:
   a reviewer's first action is writing the skeleton, so the file existing means *started*,
   never *finished*. Reviewer codes are defined in the loaded config.

   Emit its output as plain prose — **NOT inside backticks**:

   ```
   ⏳ #NNN Round N — in progress  (N of M reviewers reported)
   ──────────────────────────────────────────────────────────────
   Reviewer             Status            Early signal
   ──────────────────────────────────────────────────────────────
   <poll-round.sh output here>
   ──────────────────────────────────────────────────────────────
   ```

   **Reconciliation — the two signals must agree before Step 6.** All reviewers notified AND
   `poll-round.sh` exits `0`. If they disagree, the disagreement is the finding:

   - **Notified but no terminal status** → the agent died or ran out of context mid-write.
     Mark it `⚠️ truncated`, read the partial output, and do NOT re-run automatically —
     present the partial findings and ask the user whether to re-run.
   - **Terminal status but never notified** (e.g. the session was interrupted and resumed) →
     trust the file; note that the agent was not observed exiting.
   - **Neither, and nothing has arrived for a long time** → check the agent is still alive
     before assuming it is working. Only here is an explicit status check worth running.

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
   Amendments this round: N design / M precision
   Plan amended this round: YES → starting Round N+1 | NO → board complete
   ```

   Status symbols: `✅ PASS | ⚠️ WARN | ❌ FAIL | — SKIP | ✂️ TRUNC`

9. **Decide whether to iterate — automatically. Key on `design:` amendments, not raw count:**
   - Any **`design:`** amendment → start next round; re-run only reviewers that amended or were truncated
   - **`precision:` amendments only** → note them and continue to the *next* round only if one of them
     changed a normative statement. Pure text corrections do not require the board to re-look — the
     main session verifies the edits are correct and the board is complete.
   - No amendments → board complete
   - Any FAIL with unresolved blocking issues → stop; list issues
   - Any truncated reviewer → ask user whether to re-run before deciding
   - **Round 3 with `design:` amendments still happening → stop; plan has not stabilised (UNSTABLE).**
     Round 3 producing only `precision:` amendments is **not** UNSTABLE — it is a plan being polished.
     Verdict on the design's state, and say plainly which it was.

   **A plan is never marked UNSTABLE on volume alone.** State the ratio in the verdict: `N design / M
   precision`. If the design amendments are zero and no reviewer raised a blocking issue, the plan is
   buildable and the verdict must say so — otherwise the board blocks work it did not actually find
   fault with, and the amendment count becomes a self-fulfilling ceiling.

   **A `design:` amendment does not automatically mean a full reviewer round.** Before starting one,
   check each remaining open item (unresolved `judgement-call`/`defaulted` decision, or a `design:`
   amendment nobody has re-reviewed) against this test: **can it be closed by a cheap, mechanical check
   run once in the main session — grep, `git log`, reading a file, checking a manifest, asking the
   user one question — rather than by re-running a reviewer's judgement?**
   - If yes for every open item, run those checks directly (no subagent), fold the answers into the
     plan, and mark the board complete on this round — a check that resolves a decision is not an
     amendment requiring re-review, it is closing a question a reviewer explicitly left open. Example:
     a reviewer defaults to "assume consumer X is live, block on it" because it can't verify deployment
     state from docs — `git log`/`kubectl get` on the actual manifest resolves that outright; there is
     nothing left for a second round of judgement to add.
   - If any open item genuinely requires re-applying a reviewer's expertise against the amended text
     (a `design:` change whose correctness a domain reviewer, not a grep, has to judge) — start the
     next round, scoped to only those reviewers.
   - Don't manufacture a check to avoid a round that's actually needed, and don't manufacture a round
     for something a `grep` already answers. State which test each open item passed and why in the
     round dashboard, so the choice is auditable, not just asserted.

   **If a reconciliation pass rewrote the plan between rounds, review its diff — not the whole plan
   again.** A reconciler is unreviewed work by an author under time pressure, and it is a reliable
   source of new defects: in one review it introduced two HIGH-severity bugs, and the following
   round's findings clustered in exactly the material it had added. Point one reviewer at
   `git diff` for the reconciliation commit. That is cheaper than a full round and catches more.

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
Amendments:            {N design} / {M precision}   ← the ratio, always
------------------------------------------------------------
VERDICT:  <verdict from loaded config>
============================================================
```

Verdict definitions (from loaded config): CLEAR TO BUILD / CLEAR TO APPLY / CLEAR WITH WARNINGS / BLOCKED / UNSTABLE.

**Take each reviewer's status from its own `## Status` section.** `consolidate-round.sh` extracts the
first `PASS` token it finds, which reports `PASS WITH WARNINGS` as `PASS` — the summary table said a
reviewer passed clean when its own file said otherwise. Likewise `poll-round.sh`'s "Early signal"
column truncates and can read like a status; it is not one. Where the scripts and a reviewer's file
disagree, the file wins.

**Report an unfavourable verdict straight.** If the plan did not stabilise, say so — including where
your own earlier prediction about the review was wrong. Separate the protocol's mechanical test from
your judgement on the design: "the amendment rule says UNSTABLE; zero blocking issues were raised and
two reviewers state the plan is buildable as written" is the honest report, and both halves matter.

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
   **Amendments:** <N design / M precision>
   ```

   **Write every deferred follow-up into the task file at the moment it is deferred** — never
   "raised as a follow-up, see the reviewer output". The artefact directory is deleted by step 2,
   and anything living only there is gone: three doc issues were deferred by reference in one
   review and two of them were unrecoverable afterwards, including from the session transcript.
   A follow-up not written down in a surviving file was not deferred; it was lost.

   **Roll every reviewer's `## Opportunities` into a `## Follow-ups (non-blocking)` list in the
   task file, deduplicated.** These are constructive ideas — simplifications, alternatives,
   feasibility doubts — that didn't rise to a `design:` or `precision:` amendment. They do not
   affect the verdict or round count; they exist so a good idea a reviewer had isn't thrown away
   just because it wasn't required to ship.

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
