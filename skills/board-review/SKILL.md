---
name: board-review
description: Orchestrates the board review pipeline for codebase and platform changes. Runs mode-appropriate reviewers in parallel, iterates until all pass in the same round. Use when asked to "run a full review", "board review this", "gate this plan", or "is this ready to apply/build?".
origin: ECC
---

# Board Review

Runs a board of parallel reviewers. If a reviewer amends the plan in a way that changes what gets
built, the whole board re-reviews. Repeats until all reviewers pass in the same round without
further design changes. Maximum 3 rounds.

**The board reviews the design, not the prose.** Step 1.5 strips self-inflicted precision defects
before Round 1, so reviewers spend their budget on the design and the round count measures the
design's stability rather than the text's polish.

**Assumes a plan already exists** — run `/draft-prd` first if not. **Implements nothing**: it
convenes the board, tracks rounds, and says when you are clear to proceed.

**Output formatting rule, applies to every dashboard and prompt block below: emit as raw text in
your reply, NOT wrapped in backticks.** The fenced blocks in this file show the shape only.

---

## Mode detection

| Signal in the plan or user message | Mode |
|---|---|
| `[INFRA]`, "cluster", "k8s", "Helm", "namespace", "workload", "PVC", "node", "kubectl" | **platform** |
| None of the above — software design, API, feature, refactor | **codebase** |

**At Step 0, read `references/[mode]-board.md`** (`~/.claude/skills/board-review/references/[mode]-board.md`).
All mode-specific configuration lives there: reviewer list, model routing, triage table, plan
excerpt routing, priority hierarchy, dashboard rows, summary metrics, verdict labels, no-plan
message, next steps, commit messages. "The loaded config" below means that file.

`references/subagent-protocol.md` holds the write-as-you-go output contract every reviewer
follows. The reviewer skills load it themselves — cite it in the dispatch prompt only if a
reviewer appears to be buffering findings to the end.

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

1. **Task number named** ("review 027", "board review #3"): glob `todo/<number>-*.md`, open the
   first match.
2. **Otherwise**, in order: `todo/` — the `🔄 In Progress` task in `TODO.md`; then `DESIGN.md` or
   `design-doc.md` in the repo root or `.claude/`; then
   `git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~5)...HEAD --stat 2>/dev/null | head -30`

No plan found → **stop** with the no-plan message from the loaded config.

Summarise the plan in 2–3 sentences so the user can confirm you read the right thing. Then set
`**Status:**` to `🔎 In Review` in both the task file and `TODO.md`.

**Main session context discipline:**
- Store the plan as a **file path only** — subagents read it from disk.
- After launching subagents, do not re-read the plan unless editing it for a blocking decision.
- After consolidating a round, drop reviewer output from working memory; keep only the dashboard.
- Never paste file contents where a path will do. Target: ~500 tokens of growth per round, not ~10k.

---

## Step 1: Triage

Use the triage table from the loaded config. **Default: run all reviewers.** Skip only if the skip
condition is clearly and unambiguously met.

```markdown
**Triage complete — <N> of <M> reviewers running.**

| Reviewer | Decision | Reason |
|---|---|---|
| <name> | ✅ run | — |
| <name> | ⊘ skip | <the skip condition that matched, quoted from the config> |

Starting Round 1.
```

A skipped reviewer always names the condition that skipped it. "SKIP" with no reason cannot be
audited later, and the default is to run.

---

## Step 1.5: Precision gate — BEFORE Round 1

**The board's budget is finite and shared. Anything a reviewer spends on the plan disagreeing
with itself is not spent on the design.** In one three-round review, ~48 of 53 final-round
amendments were self-inflicted precision defects; the plan was marked UNSTABLE on amendment
*count* while zero blocking issues existed. Both steps below are cheap; skipping either costs a
round.

### a. Establish ground truth yourself

**Measure every load-bearing fact the plan reasons over, from a primary source, and correct the
plan before briefing anyone.** A wrong number becomes a wrong Round 1 brief, which reviewers treat
as given — and every finding built on it is wasted work that looks like a finding.

- **Check for a `## Feasibility checks` table first** (from `/draft-prd` Phase 2.5). If present,
  re-verify its entries — rerun the commands it names — rather than re-deriving from scratch. Rows
  it left unresolved still need a real measurement; a present-but-stale table is not a pass.
- For anything else: query the live system, run the command, read the config file. Not the plan's
  claim about it.
- **Never accept a contested fact on reviewer consensus.** Three reviewers agreeing is not
  evidence; one primary-source check is. Two of three wrong values in that review had already
  passed a full round unchallenged.
- Where a fact cannot be measured now, say so in the brief: "unverified — treat as an assumption."

**Carry this into the Round 1 dispatch:** the `## Measured facts` block records where a number came
from so nobody re-derives it. It does **not** put the number's validity out of scope. A reviewer
should still ask whether the right thing was measured, whether it is representative (peak vs
average, one node vs the fleet), or whether the command measures what its label claims — that is a
`design:` finding, and it should name the check that would settle it.

### b. Run the plan's own precision sweep

Load `~/.claude/skills/draft-prd/references/precision-rules.md` and work its self-check against
the plan. **Fix what it finds now**, in the main session: stale citations, duplicated values, rules
stated three times, unscoped universal claims, requirements with no insertion point, slices with no
placement invariant. `/draft-prd` Phase 11 should have done this; it is repeated here because the
gate belongs where the cost is paid, and plans arrive from elsewhere.

### c. Run the slop sweep

Load `~/.claude/skills/agentic-standards/references/no-ai-slop-eval.md` and work its checks
against the plan. **Fix what it finds now**, in the main session: importance puffery, weasel
attribution, interpretive metadiscourse, faux-insight setups, summary-recap endings, formatting
slop. Precision rules catch a plan that is *wrong*; this catches one that is *unreadable*, and a
reviewer who spends budget decoding prose has less left for the design.

Load the full `no-ai-slop.md` only if the eval alone is not enough to fix what it flags. Do not
rewrite the author's voice, and do not invent facts to satisfy a check — if a claim has no
source, flag it rather than sourcing it.

```markdown
**Precision gate — #NNN**

| Check | Result | Detail |
|---|---|---|
| Ground truth | <N> facts measured, <M> corrections | <source>; <K> reused from `draft-prd` Feasibility, <J> re-measured |
| Precision sweep | <N> items fixed | <breakdown> |
| Slop sweep | <N> items fixed | <breakdown> |
| Plan length | <L> lines | — |
```

If the gate made substantive corrections, **say what they were** — the plan the user approved has
changed. If it found nothing, say that too.

---

## Step 2: Board rounds

Each board member runs as a **parallel subagent** — all launched in a single message with
`run_in_background: true`, which is what makes them harness-tracked so item 5 can wait on
completion notifications instead of polling. Up to **3 rounds**.

1. Announce: "#NNN — Starting Round N — launching board subagents in parallel."

2. Create `todo/review/<slug>/` (slug = task file name without extension).

3. **Prepare a trimmed plan excerpt per reviewer** using the excerpt routing table from the loaded
   config. Do not paste the full task file into every subagent. If the task file has no
   Design/Platform Design section, include the full file for all reviewers.

4. **Launch all relevant reviewers as background subagents in a single message.** Round 1 pastes
   the trimmed excerpt (the only round where content is pasted); Round 2+ passes the file path and
   a one-line summary of what changed.

   **State the round's bar verbatim in the dispatch prompt.** A reviewer given no bar defaults to
   Round-1 breadth every time, which is what keeps plans amending forever:

   | Round | Bar to state verbatim |
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
Read the plan file directly from disk: <path> — do not rely on previously pasted content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE-FIRST RULE — read this before doing anything else
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your FIRST action must be to create the output file with this skeleton:

  Write to: todo/review/<slug>/round-<N>-<code>.md

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

Then proceed with your review.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Context budget: you are a background subagent with a finite context window.
- Complete your highest-value sections first (priority hierarchy in the loaded config)
- Findings as bullet points, one line per issue — not prose
- Stop adding findings once the output file exceeds ~800 lines
- Fewer sections deeply > more sections shallowly

Your job:
1. Perform a thorough [REVIEWER NAME] review using the /[skill-name] skill guidelines.

2. Write findings incrementally. After EACH section completes — never buffer:
   a. Append the section's findings to ## Issues (one line each)
   b. Append non-defect ideas — feasibility doubts, simpler alternatives, things worth
      doing but not required — to ## Opportunities (one line each)
   c. Append decision entries to ## Decisions Required
   d. Append plan edits to ## Amendments
   e. Leave ## Status as IN PROGRESS — do not touch it until step 4

   **Exactly one `## Status` heading must ever exist in the file** — the one from the
   skeleton, edited in place once at the end. Appending a fresh `## Status` block at a
   checkpoint leaves a stale `IN PROGRESS` line below the real verdict, which makes
   `poll-round.sh`'s preview column contradict its own icon.

   Final structure:

     ## Summary
     <3-5 bullets — most important findings, written LAST>

     ## Issues
     <SEVERITY | area | description>
     e.g. blocking | auth | JWT expiry not validated on refresh endpoint

     ## Opportunities
     <one line each — non-defect ideas. These do NOT count toward the design:/precision:
     ratio and do NOT drive round iteration; the orchestrator carries them into the task
     file's follow-ups.>
     e.g. the retry loop could use the existing backoff helper in utils/retry.py

     ## Decisions Required
     <structured entries — format below>

     ## Amendments
     <one line each, EACH TAGGED design: or precision:>

     ## Status
     PASS | PASS WITH WARNINGS | FAIL

   ## Amendment classification — tag every amendment

   - `design:`    — the plan as written would produce wrong, unsafe, or unbuildable
                    behaviour. Fixing it changes what gets built.
   - `precision:` — the plan disagrees with itself or the repo: stale citation, duplicated
                    value, rule restated inconsistently, over-scoped claim, misplaced slice
                    row. Fixing it changes only the text.

   End the section with: `TOTAL: N design, M precision`

   This tag drives the board's stabilisation decision and must be honest both ways. A
   design defect tagged `precision:` ships a real bug. A precision fix tagged `design:`
   forces an unnecessary round.

   Ceiling: if about to make more than ~10 precision amendments, make the most valuable
   ones and record the rest as ONE issue line — "N further precision defects of the same
   class" — rather than N amendments. A hundred cosmetic edits and one real finding are
   not the same signal, and the board cannot tell them apart in an undifferentiated list.

3. If issues require plan changes, edit the plan file directly, then append to ## Amendments.

4. Return: issues found, decisions required, amendments made, status.

IMPORTANT — you cannot interact with the user. Do NOT call AskUserQuestion. For any
decision point, write a structured entry in ## Decisions Required and continue with the
best-default option.
```

**`## Decisions Required` entry format:**

```
### Decision: <short title>
- **Severity:** blocking | judgement-call | defaulted
- **Question:** The exact question the user needs to answer.
- **Options:** A) ... B) ...
- **Assumed:** Which option you proceeded with and why.
- **Impact if wrong:** What changes if the user picks differently.
```

- `blocking` — cannot proceed safely; wrote FAIL and stopped. Main session must get a human answer.
- `judgement-call` — reasonable default taken; user should consciously accept it.
- `defaulted` — obvious/safe default; flagged for transparency only.

5. **Wait for the harness to tell you they finished. Do not poll on a timer.**

   Background subagents are harness-tracked: when one exits you are re-invoked with a task
   notification naming it. That notification *is* the process ending — a stronger signal than
   inspecting a file the agent is still writing.

   - Do **not** `sleep`, schedule a wakeup, or re-run a status check on an interval.
   - **Count notifications.** The round is complete at one per launched reviewer.
   - Between notifications, do nothing. Do not consolidate early on a partial set.

   `poll-round.sh` is a **renderer and a fallback**, not the completion signal. Run it once per
   notification to draw the dashboard:

   ```bash
   bash ~/.claude/skills/board-review/poll-round.sh <review_dir> <round> <active_reviewer_codes...>
   # e.g.
   bash ~/.claude/skills/board-review/poll-round.sh todo/review/027-my-feature 1 dr ar er dc sr
   ```

   It prints one line per reviewer and exits `0` only when every file carries a **terminal**
   `## Status` (`PASS` / `PASS WITH WARNINGS` / `FAIL`). `IN PROGRESS` counts as running — a
   reviewer's first action is the skeleton, so the file existing means *started*, never *finished*.

   **The exit code and leading icon are the verdict; the trailing preview text is not.** That
   preview is the file's last non-blank line and can read `IN PROGRESS` next to a terminal icon if
   a reviewer left a stray duplicate `## Status`. Where icon and preview seem to conflict, read
   `grep -n '^## Status' -A1 <file>` — the exit code already told you the truth.

   ```markdown
   **⏳ #NNN Round N — <N> of <M> reported**

   <poll-round.sh output verbatim — it emits the header row and the column rule itself>
   ```

   Paste the script's rows unaltered. Re-typing them by hand is how the status vocabulary drifts:
   one round reads `⚠️ WARN` and the next `✅ PASS WITH WARNINGS` for the same state.

   **Both signals must agree before consolidating:** all reviewers notified AND `poll-round.sh`
   exits `0`. Disagreement is itself the finding:
   - **Notified, no terminal status** → died or ran out of context mid-write. Mark `✂️ truncated`,
     read the partial output, do **not** re-run automatically — ask the user.
   - **Terminal status, never notified** (session interrupted and resumed) → trust the file; note
     the agent was not observed exiting.
   - **Neither, nothing for a long time** → check the agent is alive. Only here is an explicit
     status check worth running.

6. Consolidate:

   ```bash
   bash ~/.claude/skills/board-review/consolidate-round.sh <review_dir> <round> <reviewer_codes...>
   ```

   It extracts STATUS, AMENDED, DECISIONS, BLOCKING, OPPORTUNITIES, and a ≤10-line SUMMARY per
   reviewer. Read a reviewer's full file only when the SUMMARY is insufficient — never
   speculatively.

6.5. **Cross-check new claims for a doc-answerable verification gap.** A reviewer can introduce a
   claim or ADR in the same round another runs in parallel, so nobody fact-checks it that round —
   and unless something asks again, nobody ever does.

   Scan this round's `## Amendments`, `## Decisions Required`, and any new ADR text for language
   flagging an unverified mechanism claim: "verify in dev/live before believing", "assumption, not
   confirmed", "cannot be inferred", "should be confirmed positively", or an ADR resting on how a
   tool/library/platform *behaves* rather than on this repo's state.

   For each: **is it a claim about someone else's documented system** (a cloud API, a CNI's policy
   semantics, a library, a spec) **rather than this repo's live state** (which only
   `kubectl`/`git`/a real request settles)? If yes, route it to a `research` subagent in
   Verification mode (≤4 claims per dispatch) before the cheap-check test in item 9. Fold a
   confirmed or contradicted answer into the plan and the reviewer's decision entry, marked
   resolved with its source. An unverified result stays open and still needs the live check — this
   narrows what needs a cluster round-trip, it does not replace it.

   Skip entirely if no amendment, decision, or ADR this round contains that language. Most won't.

7. **Surface decisions before the dashboard**, grouped by severity.

   a. **`blocking` first** — one at a time, in order:

   Each one is an `AskUserQuestion` call: `header` names the subject in 12 characters or fewer, one
   option per candidate, the recommended option first with `(Recommended)` suffixed, and each
   option's `description` carrying what it costs. Where the tool is unavailable, write it:

   ```markdown
   **🛑 Blocking decision <M> of <total>** — <reviewer name> · review halted until answered

   <the question>

   | Option | Consequence |
   |---|---|
   | <A> | <what it costs, and what it unblocks> |
   | <B> | <what it costs, and what it unblocks> |
   ```

   Wait for the answer. Mark resolved, update the plan file, note in the reviewer output. Never
   re-present an answered decision.

   b. **`judgement-call`** — all together, after blocking are resolved:

   ```markdown
   **🤔 Judgement calls — <N> defaults taken, confirm or override**

   | # | Reviewer | Question | Defaulted to |
   |---|---|---|---|
   | 1 | <reviewer> | <question> | <assumed answer> |
   | 2 | <reviewer> | <question> | <assumed answer> |

   Reply "ok" to accept all, or name the numbers to override.
   ```

   c. **`defaulted`** — one line: `ℹ️ <N> minor defaults taken.`

8. **Round dashboard:**

   ```markdown
   **#NNN Round N complete**

   | Reviewer | Result | Amendments | Key finding |
   |---|---|---|---|
   | <name> | ✅ PASS | — | <one line, or "—"> |
   | <name> | ⚠️ WARN | 4 design / 5 precision | <one line> |

   **Decisions resolved:** <N> blocking · <N> judgement-call · <N> defaulted
   **Amendments:** <N> design / <M> precision
   **Plan amended:** YES — starting Round N+1 | NO — board complete
   ```

   The `Amendments` column splits design from precision per reviewer, which is what the iterate
   decision in item 9 keys on. A single total hides the distinction the rule depends on.

   **Status vocabulary — these six strings, nothing else**, so a hand-written row and a script row
   read alike. `poll-round.sh` emits the first five; `⊘ skip` is triage-only, since a skipped
   reviewer is never passed to the script:

   | Symbol | Means |
   |---|---|
   | ✅ PASS | Terminal, no warnings |
   | ⚠️ WARN | Terminal, PASS WITH WARNINGS |
   | ❌ FAIL | Terminal, blocking issues open |
   | ⏳ running | Started, no terminal status yet |
   | 🔵 queued | Launched, no output file yet |
   | ⊘ skip | Triaged out, with the reason |

   Two more mark a defect rather than a state: `✂️ truncated` for a reviewer that died mid-write,
   and `❓ unknown` for a status string that matches none of the above. Never write
   `✅ PASS WITH WARNINGS` — the tick and the warning contradict each other, and `⚠️ WARN` is the
   one string for that state.

9. **Decide whether to iterate — automatically, keyed on `design:` amendments, not raw count:**
   - Any **`design:`** amendment → run the cheap-check test below before launching a round.
   - **`precision:` only** → continue to a further round only if one changed a normative
     statement. Otherwise the main session verifies the edits and the board is complete.
   - No amendments → board complete.
   - Any FAIL with unresolved blocking issues → stop; list them.
   - Any truncated reviewer → ask the user before deciding.
   - **Round 3 still producing `design:` amendments → stop, UNSTABLE.** Round 3 producing only
     `precision:` amendments is **not** UNSTABLE — that is a plan being polished. Say which it was.

   **A plan is never marked UNSTABLE on volume alone.** State the ratio in the verdict:
   `N design / M precision`. If design amendments are zero and no reviewer raised a blocking
   issue, the plan is buildable and the verdict must say so — otherwise the board blocks work it
   did not find fault with, and the amendment count becomes a self-fulfilling ceiling.

   **Cheap-check test.** For each open item (unresolved `judgement-call`/`defaulted` decision, or
   a `design:` amendment nobody re-reviewed), ask: **can it be closed by a cheap mechanical check
   in the main session — grep, `git log`, reading a file or manifest, one question to the user —
   rather than by re-running a reviewer's judgement?**
   - Yes for every open item → run the checks directly (no subagent), fold in the answers, mark
     the board complete this round. Closing a question a reviewer explicitly left open is not an
     amendment requiring re-review. Example: a reviewer defaults to "assume consumer X is live"
     because docs cannot settle deployment state; `git log`/`kubectl get` resolves it outright.
   - Any item genuinely needs a domain reviewer's judgement against the amended text → start the
     next round, re-running only reviewers that amended, were truncated, or must re-judge it.
   - Do not manufacture a check to dodge a needed round, or a round for something `grep` answers.
     State which test each open item passed, in the dashboard, so the choice is auditable.

   **If a reconciliation pass rewrote the plan between rounds, review its diff — not the whole
   plan.** A reconciler is unreviewed work by an author under time pressure and a reliable source
   of new defects: in one review it introduced two HIGH-severity bugs, and the next round's
   findings clustered in exactly the material it had added. Point one reviewer at `git diff` for
   the reconciliation commit — cheaper than a round, and it catches more.

---

## Step 3: Final summary

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

Verdicts (from loaded config): CLEAR TO BUILD / CLEAR TO APPLY / CLEAR WITH WARNINGS / BLOCKED /
UNSTABLE.

**Take each reviewer's status from its own `## Status` section.** `consolidate-round.sh` extracts
the first `PASS` token, reporting `PASS WITH WARNINGS` as `PASS`; `poll-round.sh`'s Early signal column
truncates at 60 characters and can read like a status. Where a script and a reviewer's file disagree, the file wins.

**Report an unfavourable verdict straight**, including where your own earlier prediction was
wrong. Separate the mechanical test from your judgement: "the amendment rule says UNSTABLE; zero
blocking issues were raised and two reviewers state the plan is buildable as written" is the
honest report, and both halves matter.

---

## After the review

**All reviewer output must be persisted into the task file before the artefact directory is
deleted.**

1. **Append `## Board Review` to `todo/<slug>.md`.**

   Part A — summary table:
   ```markdown
   ## Board Review

   **Verdict:** <verdict>
   **Date:** YYYY-MM-DD
   **Rounds:** N

   | Reviewer | Result | Amended | Key findings |
   |---|---|---|---|
   | <name> | ✅ PASS | — | <one line, or "—"> |
   | <name> | ⚠️ WARN | 4 design / 5 precision | <one line> |

   **Accepted warnings:** <list or "none">
   **Unresolved decisions:** <N> (or "none")
   **Amendments:** <N design / M precision>
   ```

   **Write every deferred follow-up into the task file at the moment it is deferred** — never
   "raised as a follow-up, see the reviewer output". Step 3 deletes the artefact directory:
   three doc issues were deferred by reference in one review and two were unrecoverable
   afterwards, including from the transcript. A follow-up not in a surviving file was lost.

   **Roll every reviewer's `## Opportunities` into `## Follow-ups (non-blocking)`,
   deduplicated** — simplifications, alternatives, feasibility doubts that did not rise to an
   amendment. They do not affect the verdict or round count; they exist so a reviewer's good idea
   is not thrown away for not being required to ship.

   Part B — full reviewer output, one collapsible block each:
   ```markdown
   ### Reviewer output

   <details>
   <summary><reviewer name> — Round N (<status>)</summary>

   <!-- paste full contents of todo/review/<slug>/round-N-<code>.md here -->

   </details>
   ```

   Multi-round reviews include only the final round per reviewer. If truncated:
   `⚠️ Truncated — output is partial; sections reached: <list>`

2. **Append one line to `todo/board-review-history.log`** (create if absent). This is the only
   place the amendment ratio is tracked across reviews, so whether the precision gate is actually
   shrinking rounds is answerable later rather than guessed:
   ```
   YYYY-MM-DD #NNN <codebase|platform> rounds=N verdict=<verdict> amendments=<design>/<precision>
   ```

3. **Delete the artefact directory** — only after the task file is written:
   `rm -rf todo/review/<slug>/`

4. **Update the task file and `TODO.md`:** CLEAR → `🔍 Reviewed` in both. BLOCKED or UNSTABLE →
   `⬜ Open`, with a note on what blocked it.

5. **Commit** using the message format from the loaded config, then tell the user the verdict
   using the after-review next steps from the loaded config.

---

## Formatting rules

- Show the round dashboard after every round.
- Never batch issues across reviewers into one question.
- If the user asks to skip a reviewer mid-round, confirm via AskUserQuestion — skipping is
  accepting the risk that reviewer would have caught.
- If the user interrupts and resumes, re-show the last round dashboard immediately.
- Starting a new round: "Plan was amended in Round N: {summary}. Starting Round N+1."
