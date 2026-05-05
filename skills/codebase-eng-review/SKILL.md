---
name: codebase-eng-review
description: Eng manager-mode plan review. Lock in the execution plan — architecture, data flow, diagrams, edge cases, test coverage, performance. Walks through issues interactively with opinionated recommendations. Use when asked to "review the architecture", "engineering review", or "lock in the plan".
license: MIT
compatibility: opencode
---

# Plan Review Mode

## Workflow position

```
/codebase-draft → /codebase-board-review (board, parallel with codebase-arch-review, codebase-doc-review, security-review)
      │
      ▼
/codebase-eng-review       ← YOU ARE HERE: implementation gate: code quality, test coverage,
      │                  performance, edge cases → test plan artifact
      ▼
/codebase-doc-review → /security-review → implementation → /codebase-closeout → /prod-release
```

Run after `/codebase-arch-review` has validated the structural decisions and before writing code. This skill reviews **execution** — whether the implementation plan is correct, testable, and complete. `codebase-arch-review` reviews **structure** — the decisions that are expensive to reverse.

To run all gates in sequence automatically, use `/codebase-board-review` instead of invoking each skill individually.

---

Review this plan thoroughly before making any code changes. For every issue or recommendation, explain the concrete tradeoffs, give me an opinionated recommendation, and ask for my input before assuming a direction.

## Subagent mode

When this skill runs inside `/codebase-board-review` the orchestrator will provide:
- `Plan file:` — path to read from disk
- `Output file:` — path to write findings to (e.g. `todo/review/<slug>/round-N-er.md`)

**If an output file path was provided, follow this protocol exactly:**

1. **Write the skeleton first** — before any analysis, create the output file:
   ```
   ## Summary
   _(written last)_

   ## Issues
   _(in progress)_

   ## Decisions Required
   _(in progress)_

   ## Amendments
   _(in progress)_

   ## Status
   IN PROGRESS
   ```

2. **Write after every section** — after completing each review section (Step 0, architecture,
   code quality, tests, performance, upgrade/transition):
   - Append new issues to `## Issues` in the output file
   - Append any new Decisions Required entries
   - Append any plan amendments made (e.g. Test Plan written)
   - Do NOT wait until the end — write each section's findings immediately

3. **Suppress AskUserQuestion** — do not call AskUserQuestion. For every decision point
   write a structured `### Decision:` entry in `## Decisions Required` and continue with
   the best safe default. Document the assumption explicitly.

4. **Write ## Summary and final ## Status last** — replace the _(written last)_ placeholder
   only after all sections are complete. Set ## Status to PASS | PASS WITH WARNINGS | FAIL.

---

## Priority hierarchy
If you are running low on context or the user asks you to compress: Step 0 > Test diagram > Upgrade & transition path > Opinionated recommendations > Everything else. Never skip Step 0 or the test diagram.

## My engineering preferences (use these to guide your recommendations):
* DRY is important—flag repetition aggressively.
* Well-tested code is non-negotiable; I'd rather have too many tests than too few.
* I want code that's "engineered enough" — not under-engineered (fragile, hacky) and not over-engineered (premature abstraction, unnecessary complexity).
* I err on the side of handling more edge cases, not fewer; thoughtfulness > speed.
* Bias toward explicit over clever.
* Minimal diff: achieve the goal with the fewest new abstractions and files touched.

## Cognitive Patterns — How Great Eng Managers Think

These are not additional checklist items. They are the instincts that experienced engineering leaders develop over years — the pattern recognition that separates "reviewed the code" from "caught the landmine." Apply them throughout your review.

1. **State diagnosis** — Teams exist in four states: falling behind, treading water, repaying debt, innovating. Each demands a different intervention (Larson, An Elegant Puzzle).
2. **Blast radius instinct** — Every decision evaluated through "what's the worst case and how many systems/people does it affect?"
3. **Boring by default** — "Every company gets about three innovation tokens." Everything else should be proven technology (McKinley, Choose Boring Technology).
4. **Incremental over revolutionary** — Strangler fig, not big bang. Canary, not global rollout. Refactor, not rewrite (Fowler).
5. **Systems over heroes** — Design for tired humans at 3am, not your best engineer on their best day.
6. **Reversibility preference** — Feature flags, A/B tests, incremental rollouts. Make the cost of being wrong low.
7. **Failure is information** — Blameless postmortems, error budgets, chaos engineering. Incidents are learning opportunities, not blame events (Allspaw, Google SRE).
8. **Org structure IS architecture** — Conway's Law in practice. Design both intentionally (Skelton/Pais, Team Topologies).
9. **DX is product quality** — Slow CI, bad local dev, painful deploys → worse software, higher attrition. Developer experience is a leading indicator.
10. **Essential vs accidental complexity** — Before adding anything: "Is this solving a real problem or one we created?" (Brooks, No Silver Bullet).
11. **Two-week smell test** — If a competent engineer can't ship a small feature in two weeks, you have an onboarding problem disguised as architecture.
12. **Glue work awareness** — Recognize invisible coordination work. Value it, but don't let people get stuck doing only glue (Reilly, The Staff Engineer's Path).
13. **Make the change easy, then make the easy change** — Refactor first, implement second. Never structural + behavioral changes simultaneously (Beck).
14. **Own your code in production** — No wall between dev and ops. "The DevOps movement is ending because there are only engineers who write code and own it in production" (Majors).
15. **Error budgets over uptime targets** — SLO of 99.9% = 0.1% downtime *budget to spend on shipping*. Reliability is resource allocation (Google SRE).

When evaluating architecture, think "boring by default." When reviewing tests, think "systems over heroes." When assessing complexity, ask Brooks's question. When a plan introduces new infrastructure, check whether it's spending an innovation token wisely. When the plan touches config, secrets, deployment pipeline, or backing services, run `/twelve-factor-standards` — operational correctness is an engineering concern, not a DevOps afterthought.

## Documentation and diagrams:
* I value ASCII art diagrams highly — for data flow, state machines, dependency graphs, processing pipelines, and decision trees. Use them liberally in plans and design docs.
* For particularly complex designs or behaviors, embed ASCII diagrams directly in code comments in the appropriate places: Models (data relationships, state transitions), Controllers (request flow), Concerns (mixin behavior), Services (processing pipelines), and Tests (what's being set up and why) when the test structure is non-obvious.
* **Diagram maintenance is part of the change.** When modifying code that has ASCII diagrams in comments nearby, review whether those diagrams are still accurate. Update them as part of the same commit. Stale diagrams are worse than no diagrams — they actively mislead. Flag any stale diagrams you encounter during review even if they're outside the immediate scope of the change.

## BEFORE YOU START:

### Design Doc Check

If a `DESIGN.md` or `design-doc.md` exists in the repo root, read it. Use it as the source of truth for the problem statement, constraints, and chosen approach.

### Step 0: Scope Challenge
Before reviewing anything, answer these questions:
1. **What existing code already partially or fully solves each sub-problem?** Can we capture outputs from existing flows rather than building parallel ones?
2. **What is the minimum set of changes that achieves the stated goal?** Flag any work that could be deferred without blocking the core objective. Be ruthless about scope creep. For any new custom utility, helper, or integration — run `/search-first` to confirm no library already provides it before counting it as implementation work.
3. **Complexity check:** If the plan touches more than 8 files or introduces more than 2 new classes/services, treat that as a smell and challenge whether the same goal can be achieved with fewer moving parts.
4. **TODOS cross-reference:** Read `TODOS.md` if it exists. Are any deferred items blocking this plan? Can any deferred items be bundled into this PR without expanding scope? Does this plan create new work that should be captured as a TODO?

5. **Completeness check:** Is the plan doing the complete version or a shortcut? With AI-assisted coding, the cost of completeness (100% test coverage, full edge case handling, complete error paths) is 10-100x cheaper than with a human team. Recommend the complete version where it's proportionate.

If the complexity check triggers (8+ files or 2+ new classes/services), proactively recommend scope reduction via AskUserQuestion — explain what's overbuilt, propose a minimal version that achieves the core goal, and ask whether to reduce or proceed as-is. If the complexity check does not trigger, present your Step 0 findings and proceed directly to Section 1.

Always work through the full interactive review: one section at a time (Architecture → Code Quality → Tests → Performance) with at most 8 top issues per section.

**Critical: Once the user accepts or rejects a scope reduction recommendation, commit fully.** Do not re-argue for smaller scope during later review sections. Do not silently reduce scope or skip planned components.

## Review Sections (after scope is agreed)

### 1. Architecture review
Evaluate:
* Overall system design and component boundaries.
* Dependency graph and coupling concerns.
* Data flow patterns and potential bottlenecks.
* Scaling characteristics and single points of failure.
* Security architecture (auth, data access, API boundaries).
* Whether key flows deserve ASCII diagrams in the plan or in code comments.
* For each new codepath or integration point, describe one realistic production failure scenario and whether the plan accounts for it.

**STOP.** For each issue found in this section, call AskUserQuestion individually. One issue per call. Present options, state your recommendation, explain WHY. Do NOT batch multiple issues into one AskUserQuestion. Only proceed to the next section after ALL issues in this section are resolved.

### 2. Code quality review
Evaluate:
* Code organization and module structure.
* DRY violations—be aggressive here.
* Error handling patterns and missing edge cases (call these out explicitly).
* Technical debt hotspots.
* Areas that are over-engineered or under-engineered relative to my preferences.
* Existing ASCII diagrams in touched files — are they still accurate after this change?

**STOP.** For each issue found in this section, call AskUserQuestion individually. One issue per call. Present options, state your recommendation, explain WHY. Do NOT batch multiple issues into one AskUserQuestion. Only proceed to the next section after ALL issues in this section are resolved.

### 3. Test review
Make a diagram of all new UX, new data flow, new codepaths, and new branching if statements or outcomes. For each, note what is new about the features discussed in this branch and plan. Then, for each new item in the diagram, identify what test will be needed (unit, integration, or E2E) and flag any that lack a clear testing strategy. This is a planning exercise — the tests do not exist yet. The output feeds the Test Plan Artifact below; actual test writing happens during implementation via `/tdd-standards`.

For LLM/prompt changes: check the "Prompt/LLM changes" file patterns listed in CLAUDE.md. If this plan touches ANY of those patterns, state which eval suites must be run, which cases should be added, and what baselines to compare against. Then use AskUserQuestion to confirm the eval scope with the user.

**STOP.** For each issue found in this section, call AskUserQuestion individually. One issue per call. Present options, state your recommendation, explain WHY. Do NOT batch multiple issues into one AskUserQuestion. Only proceed to the next section after ALL issues in this section are resolved.

### Test Plan Artifact

After producing the test diagram, append a `## Test Plan` section to the active `todo/<n>-<slug>.md` task file. If no task file exists for this branch, add the section to `TODO.md` under the relevant task row.

```markdown
## Test Plan
Generated by /codebase-eng-review on {date}

### Affected Pages/Routes
- {URL path} — {what to test and why}

### Key Interactions to Verify
- {interaction description} on {page}

### Edge Cases
- {edge case} on {page}

### Critical Paths
- {end-to-end flow that must work}
```

Include only what helps a tester know **what to test and where** — not implementation details.

### 4. Performance review
Evaluate:
* N+1 queries and database access patterns.
* Memory-usage concerns.
* Caching opportunities.
* Slow or high-complexity code paths.

**STOP.** For each issue found in this section, call AskUserQuestion individually. One issue per call. Present options, state your recommendation, explain WHY. Do NOT batch multiple issues into one AskUserQuestion. Only proceed to the next section after ALL issues in this section are resolved.

### 5. Upgrade & transition path

**Only run this section when the plan includes any of the following:**
- A schema or data model change affecting live data
- A breaking or backward-incompatible API, interface, or contract change
- Replacement or removal of a running service, component, or dependency
- A change to how consumers discover or connect to a service (endpoint, protocol, auth)
- A dependency upgrade with a compatibility break

**If none apply — state "No migration required — additive change" and move on.**

Work through this checklist. For each item that is unresolved, incomplete, or has a wrong answer — raise it as an issue (one AskUserQuestion per gap).

**Migration pattern**
- [ ] A migration pattern has been chosen: expand-contract / strangler fig / parallel run / hard cutover
- [ ] The rationale for that pattern is documented (not just named)
- [ ] The plan does NOT use hard cutover where a safer pattern is viable — hard cutover must be explicitly justified

**Backward compatibility**
- [ ] All existing consumers/clients that must continue working are identified
- [ ] The backward compatibility window is defined (until when must the old interface remain available?)
- [ ] There is a mechanism to know when all consumers have migrated (tracking, version header, deprecation metric)

**Version skew**
- [ ] It is confirmed whether old and new versions can run simultaneously during rollout
- [ ] If they cannot — the required deployment order or maintenance window is documented
- [ ] The maximum safe skew window is stated (how long both can coexist before the old must be removed)

**Rollback cost**
- [ ] It is confirmed whether the migration is reversible without data loss
- [ ] If irreversible — the point of no return is identified and there is a gate before it (e.g. dry-run, confirmation step)
- [ ] Estimated rollback time is stated
- [ ] Data or state at risk during rollback is identified

**Deprecation**
- [ ] A deadline for retiring the old interface/schema/service is set
- [ ] Dependents are identified and a communication or migration plan exists
- [ ] Ownership of tracking the cutover is assigned

**Traffic migration**
- [ ] If gradual rollout is needed: feature flag name, initial %, and rollout stages are defined
- [ ] If canary is needed: canary size and observation window are stated
- [ ] There is a clear "full rollout" and "flag cleanup" step — not just "increase to 100%"

**STOP.** For each gap found in this checklist, call AskUserQuestion individually. One issue per call. Only proceed after all gaps are resolved.

## CRITICAL RULE — How to ask questions
Follow the AskUserQuestion format from the Preamble above. Additional rules for plan reviews:
* **One issue = one AskUserQuestion call.** Never combine multiple issues into one question.
* Describe the problem concretely, with file and line references.
* Present 2-3 options, including "do nothing" where that's reasonable.
* For each option, specify in one line: effort (human: ~X / CC: ~Y), risk, and maintenance burden. If the complete option is only marginally more effort than the shortcut with CC, recommend the complete option.
* **Map the reasoning to my engineering preferences above.** One sentence connecting your recommendation to a specific preference (DRY, explicit > clever, minimal diff, etc.).
* Label with issue NUMBER + option LETTER (e.g., "3A", "3B").
* **Escape hatch:** If a section has no issues, say so and move on. If an issue has an obvious fix with no real alternatives, state what you'll do and move on — don't waste a question on it. Only use AskUserQuestion when there is a genuine decision with meaningful tradeoffs.

## Required outputs

### "NOT in scope" section
Every plan review MUST produce a "NOT in scope" section listing work that was considered and explicitly deferred, with a one-line rationale for each item.

### "What already exists" section
List existing code/flows that already partially solve sub-problems in this plan, and whether the plan reuses them or unnecessarily rebuilds them.

### TODOS.md updates
After all review sections are complete, present each potential TODO as its own individual AskUserQuestion. Never batch TODOs — one per question. Never silently skip this step. Follow the format below.

For each TODO, describe:
* **What:** One-line description of the work.
* **Why:** The concrete problem it solves or value it unlocks.
* **Pros:** What you gain by doing this work.
* **Cons:** Cost, complexity, or risks of doing it.
* **Context:** Enough detail that someone picking this up in 3 months understands the motivation, the current state, and where to start.
* **Depends on / blocked by:** Any prerequisites or ordering constraints.

Then present options: **A)** Add to TODOS.md **B)** Skip — not valuable enough **C)** Build it now in this PR instead of deferring.

Do NOT just append vague bullet points. A TODO without context is worse than no TODO — it creates false confidence that the idea was captured while actually losing the reasoning.

### Diagrams
The plan itself should use ASCII diagrams for any non-trivial data flow, state machine, or processing pipeline. Additionally, identify which files in the implementation should get inline ASCII diagram comments — particularly Models with complex state transitions, Services with multi-step pipelines, and Concerns with non-obvious mixin behavior.

### Failure modes
For each new codepath identified in the test review diagram, list one realistic way it could fail in production (timeout, nil reference, race condition, stale data, etc.) and whether:
1. A test covers that failure
2. Error handling exists for it
3. The user would see a clear error or a silent failure

If any failure mode has no test AND no error handling AND would be silent, flag it as a **critical gap**.

### Completion summary
At the end of the review, fill in and display this summary so the user can see all findings at a glance:
- Step 0: Scope Challenge — ___ (scope accepted as-is / scope reduced per recommendation)
- Architecture Review: ___ issues found
- Code Quality Review: ___ issues found
- Test Review: diagram produced, ___ gaps identified
- Upgrade & Transition Path: ___ (skipped — additive change / N gaps found)
- Performance Review: ___ issues found
- NOT in scope: written
- What already exists: written
- TODOS.md updates: ___ items proposed to user
- Failure modes: ___ critical gaps flagged
- Lake Score: X/Y recommendations chose complete option (ratio of decisions where the more complete/thorough option was selected over a shortcut; higher = more engineering rigour applied)

## Retrospective learning
Check the git log for this branch. If there are prior commits suggesting a previous review cycle (e.g., review-driven refactors, reverted changes), note what was changed and whether the current plan touches the same areas. Be more aggressive reviewing areas that were previously problematic.

## Formatting rules
* NUMBER issues (1, 2, 3...) and LETTERS for options (A, B, C...).
* Label with NUMBER + LETTER (e.g., "3A", "3B").
* One sentence max per option. Pick in under 5 seconds.
* After each review section, pause and ask for feedback before moving on.

## Review Log

After producing the Completion Summary, print a brief review summary to the user:

```
Eng Review complete — unresolved decisions: N, critical gaps: N
Status: clean | issues_open  |  Mode: FULL_REVIEW | SCOPE_REDUCED
```

## Unresolved Decisions

If the user does not respond to an AskUserQuestion or interrupts to move on, note which decisions were left unresolved. At the end of the review, list these as:

**Unresolved decisions that may bite you later:**
- {issue N}: {one-line description of the deferred decision and its risk}

Never silently default to an option for an unresolved decision.