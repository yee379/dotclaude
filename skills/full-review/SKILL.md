---
name: full-review
description: Orchestrates the complete pre-implementation review pipeline — triage, then sequentially gates through plan-architect-review, plan-eng-review, plan-documentation-review, and security-review. Tracks gate status, surfaces a running dashboard, and tells you exactly what to do next. Use when asked to "run a full review", "review everything", or "gate this plan".
license: MIT
compatibility: opencode
---

# Full Review

Orchestrates the complete pre-implementation review pipeline against an existing plan. Each gate must pass before the next runs. You get a running dashboard so you always know where you are and what's left.

**Model routing:** Triage (Step 1) is Haiku-eligible — it's a classification task. Each gate (Steps 2+) runs at **Opus** — they require deep reasoning, cross-file analysis, and architectural judgment. Do not downgrade gate execution to Sonnet to save cost; the gates exist precisely because the decisions are hard.

**This skill assumes a plan already exists.** If you don't have one yet, run `/feature-plan` first.

**This skill does not implement anything.** It sequences reviews, tracks gate status, and tells you when you're clear to build.

---

## The pipeline

```
/full-review
      │
      ▼
  [Triage]         which gates are relevant for this change?
      │
      ▼
  [Gate 1]  /plan-architect-review   structural decisions, service boundaries,
      │                              data ownership, failure domains → ADR log
      ▼
  [Gate 2]  /plan-eng-review         implementation correctness, test coverage,
      │                              performance, edge cases → test plan artifact
      ▼
  [Gate 3]  /plan-documentation-review  which docs change, breaking change
      │                              upgrade guides, gaps added to plan
      ▼
  [Gate 4]  /security-review         secrets, auth, input validation, injection,
      │                              supply chain, Kubernetes workload security
      ▼
  [Clear to build]
      │
      ▼  (after implementation)
  /prod-release → /document-release
```

---

## Step 0: Locate the plan

Before anything else, find what's being reviewed:

1. Check for a plan file: `DESIGN.md`, `design-doc.md`, or any `.md` in `.claude/` describing the feature.
2. Check git: `git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~5)...HEAD --stat 2>/dev/null | head -30` — is there already code on this branch that implicitly defines the scope?
3. Check `TODOS.md` for the item being worked.

If no plan is found, **stop** and tell the user:
> "No plan found. Run `/feature-plan` first to produce a design document, then come back to `/full-review`."

If a plan is found, summarise it in 2-3 sentences so the user can confirm you've read the right thing before proceeding.

---

## Step 1: Triage — which gates apply?

Not every change needs every gate. Run triage first to avoid wasted effort.

For each gate, answer yes/no based on the plan:

```
GATE                        SKIP IF...
──────────────────────────────────────────────────────────────────────
plan-architect-review       change touches only a single existing service with
                            no new data stores, no new async channels, no service
                            boundary changes, and no new infrastructure
plan-eng-review             change is purely documentation or config with no
                            code changes
plan-documentation-review   change is purely internal/infra with no user-facing
                            surface, no API changes, no new commands or config
security-review             change has no user input, no auth changes, no new
                            API endpoints, no secrets, no new K8s workloads
──────────────────────────────────────────────────────────────────────
```

**Default: run all gates.** Only skip a gate if the skip condition is clearly and unambiguously met. When in doubt, run it.

Present the triage result:

```
Triage complete
───────────────────────────────────────────────
Gate 1  plan-architect-review    RUN | SKIP (reason)
Gate 2  plan-eng-review          RUN | SKIP (reason)
Gate 3  plan-documentation-review RUN | SKIP (reason)
Gate 4  security-review          RUN | SKIP (reason)
───────────────────────────────────────────────
```

**STOP.** Ask the user to confirm the triage before proceeding. Use AskUserQuestion if any gate's skip/run decision is debatable. Only proceed after confirmation.

---

## Step 2: Run gates sequentially

Run each gate in order. **Do not start the next gate until the current one is complete and the user has confirmed they are ready to proceed.**

For each gate that is marked RUN:

1. Announce the gate: "Starting Gate N: /skill-name"
2. Invoke the skill fully — do not abbreviate or summarise the review
3. When the skill completes, present the gate result:

```
Gate N complete: /skill-name
───────────────────────────────────
Issues found:    N
Resolved:        N
Unresolved:      N
Status:          PASS | FAIL | PASS WITH WARNINGS
───────────────────────────────────
```

4. If status is **FAIL** (unresolved blocking issues): **stop the pipeline**. Do not proceed to the next gate. Tell the user which issues must be resolved before continuing.

5. If status is **PASS WITH WARNINGS** (issues raised, user chose to accept risk): note the warnings, proceed, and carry them into the final summary.

6. If status is **PASS**: proceed to the next gate.

After each gate, show the running dashboard:

```
Pipeline status
───────────────────────────────────────────────────────
Gate 1  plan-architect-review     ✅ PASS | ⚠️ WARNINGS | ❌ FAIL | ⏳ PENDING | — SKIPPED
Gate 2  plan-eng-review           ✅ PASS | ⚠️ WARNINGS | ❌ FAIL | ⏳ PENDING | — SKIPPED
Gate 3  plan-documentation-review ✅ PASS | ⚠️ WARNINGS | ❌ FAIL | ⏳ PENDING | — SKIPPED
Gate 4  security-review           ✅ PASS | ⚠️ WARNINGS | ❌ FAIL | ⏳ PENDING | — SKIPPED
───────────────────────────────────────────────────────
```

---

## Step 3: Final summary

After all gates have run (or the pipeline has been halted), produce the final summary:

```
╔══════════════════════════════════════════════════════════════════╗
║                    FULL REVIEW — FINAL SUMMARY                  ║
╠══════════════════════════════════════════════════════════════════╣
║ Plan:     {plan file or description}                            ║
║ Branch:   {branch}                                              ║
║ Date:     {date}                                                ║
╠══════════════════════════════════════════════════════════════════╣
║ Gate 1  plan-architect-review     ✅/⚠️/❌/— {N issues}         ║
║ Gate 2  plan-eng-review           ✅/⚠️/❌/— {N issues}         ║
║ Gate 3  plan-documentation-review ✅/⚠️/❌/— {N issues}         ║
║ Gate 4  security-review           ✅/⚠️/❌/— {N issues}         ║
╠══════════════════════════════════════════════════════════════════╣
║ ADRs written:         N  (in .claude/adrs/)                     ║
║ Test plan written:    Y/N (in .claude/test-plans/)              ║
║ Doc gaps added to plan: N                                       ║
║ Accepted warnings:    N                                         ║
║ Blocking issues:      N                                         ║
╠══════════════════════════════════════════════════════════════════╣
║ VERDICT:  CLEAR TO BUILD | BLOCKED | CLEAR WITH WARNINGS        ║
╚══════════════════════════════════════════════════════════════════╝
```

**CLEAR TO BUILD** — all gates passed, no unresolved issues.

**CLEAR WITH WARNINGS** — all gates passed, but the user accepted risk on one or more issues. List the accepted warnings explicitly so they can be revisited post-ship.

**BLOCKED** — one or more gates failed with unresolved issues. List the blocking issues and which gate they belong to.

---

## After the review

If verdict is **CLEAR TO BUILD** or **CLEAR WITH WARNINGS**:

> "You're clear to implement. When the code is done, run `/prod-release` to promote through environments, then `/document-release` to apply the documentation updates identified in Gate 3."

If verdict is **BLOCKED**:

> "Resolve the blocking issues above, then re-run `/full-review` or continue from Gate N using `/skill-name` directly."

---

## Formatting rules

- Show the pipeline dashboard after every gate completion — never let the user lose track of where they are.
- Never batch issues across gates into a single question.
- One AskUserQuestion per issue, exactly as each underlying skill requires.
- If the user asks to skip a gate mid-pipeline, use AskUserQuestion to confirm — skipping a gate is accepting the risk it would have caught.
- If the user interrupts and resumes later, re-show the dashboard immediately so they can reorient.
