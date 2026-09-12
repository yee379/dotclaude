---
name: multi-agent-handbook
description: "Patterns and architectures for multi-agent systems — from simple sequential pipelines to RFC-driven DAG orchestration, including iterative context retrieval for subagents."
origin: ECC
---

# Multi-Agent Handbook

Patterns and reference implementations for running Claude Code in multi-agent systems — from
`claude -p` pipelines to RFC-driven DAG orchestration, plus iterative context retrieval for
subagents.

Use for: autonomous development workflows that run unattended · choosing a loop architecture ·
CI/CD-style continuous pipelines · parallel agents with merge coordination · context persistence
across iterations · quality gates and cleanup passes · subagents needing progressively refined
codebase context · "context too large" or "missing context" failures.

| Pattern | Complexity | Best for |
|---------|-----------|----------|
| [Sequential Pipeline](#1-sequential-pipeline) | Low | Daily dev steps, scripted workflows |
| [Infinite Agentic Loop](#2-infinite-agentic-loop) | Medium | Parallel content generation, spec-driven work |
| [Continuous Claude PR Loop](#3-continuous-claude-pr-loop) | Medium | Multi-day iterative projects with CI gates |
| [De-Sloppify](#4-de-sloppify) | Add-on | Quality cleanup after any Implementer step |
| [Ralphinho / RFC-driven DAG](#5-ralphinho--rfc-driven-dag-orchestration) | High | Large features, parallel units with a merge queue |
| [Iterative Context Retrieval](#6-iterative-context-retrieval) | Add-on | Feeding subagents the right context in an unfamiliar codebase |

> **NanoClaw REPL** — upstream ECC's persistent-loop harness (repeated `claude -p` with history in
> `~/.claude/claw/{session}.md`). **Not installed in this tree**; no `claw.js`, no `/claw`. Use
> Sequential Pipeline for scripted automation, or a plain interactive session for exploration.

## Choosing

```
Is the task a single focused change?
├─ Yes → Sequential Pipeline
└─ No → Is there a written spec/RFC?
         ├─ Yes → Do you need parallel implementation?
         │        ├─ Yes → Ralphinho (DAG orchestration)
         │        └─ No → Continuous Claude (iterative PR loop)
         └─ No → Do you need many variations of the same thing?
                  ├─ Yes → Infinite Agentic Loop
                  └─ No → Sequential Pipeline with de-sloppify
```

---

## 1. Sequential Pipeline

**The simplest loop.** Break development into a sequence of non-interactive `claude -p` calls,
each a focused step with a clear prompt.

> If you can't figure out a loop like this, it means you can't even drive the LLM to fix your code
> in interactive mode.

```bash
#!/bin/bash
set -e

for feature in "${features[@]}"; do
  claude -p "Implement $feature with full TDD. Be thorough with tests."
  claude -p "Cleanup pass: review changes in the working tree, remove test/code slop
             (see De-Sloppify below), run the test suite."
  claude -p "Run the full build, lint, type check, and test suite. Fix any failures.
             Do not add new features."
  claude -p "Create a conventional commit: 'feat: add $feature'"
done
```

**Design principles.** Each step is isolated — a fresh context window per call means no context
bleed. Order matters: each step builds on the filesystem state the last one left. `set -e` stops
the pipeline on failure. And **never use negative instructions** — add a separate cleanup pass
instead (§4).

**Model routing.** Claude Code resolves tiers to current IDs: `opus` for complex reasoning,
planning, and review; `sonnet` as the balanced default; `haiku` for simple transformations and
classification. Route by task, even inside a simple pipeline:

```bash
claude -p --model opus   "Analyze the codebase architecture and plan a caching layer..."
claude -p                "Implement the caching layer per docs/caching-plan.md..."
claude -p --model haiku  "Fix the import ordering in src/utils.ts"
claude -p --model opus   "Review all changes for security issues, races, and edge cases..."
```

**Context via files, not prompt length:**

```bash
echo "Focus areas: auth module, API rate limiting" > .claude-context.md
claude -p "Read .claude-context.md for priorities. Work through them in order."
rm .claude-context.md
```

**Tool restrictions** scope a pass to what it should be able to do:

```bash
claude -p --allowedTools "Read,Grep,Glob"        "Audit this codebase for vulnerabilities..."
claude -p --allowedTools "Read,Write,Edit,Bash"  "Implement the fixes from security-audit.md..."
```

---

## 2. Infinite Agentic Loop

**A two-prompt system** orchestrating parallel sub-agents for spec-driven generation (credit:
@disler).

```
PROMPT 1 (Orchestrator)              PROMPT 2 (Sub-Agents)
┌─────────────────────┐             ┌──────────────────────┐
│ Parse spec file      │             │ Receive full context  │
│ Scan output dir      │  deploys   │ Read assigned number  │
│ Plan iteration       │────────────│ Follow spec exactly   │
│ Assign creative dirs │  N agents  │ Generate unique output │
│ Manage waves         │             │ Save to output dir    │
└─────────────────────┘             └──────────────────────┘
```

The orchestrator reads a Markdown spec, scans existing output for the highest iteration number,
then launches N sub-agents — each receiving the full spec, a **unique assigned creative
direction**, a specific iteration number (so no conflicts), and a snapshot of existing iterations.

**Uniqueness comes from assignment, not self-differentiation.** Agents left to differentiate
themselves produce duplicate concepts.

Batching: 1–5 simultaneously · 6–20 in batches of 5 · infinite in waves of 3–5 with progressive
sophistication, until context is exhausted.

Full subagent prompt: `references/subagent-prompts.md` → "Infinite Agentic Loop". Create
`.claude/commands/infinite.md`, then:

```bash
/project:infinite specs/component-spec.md src/ 5
/project:infinite specs/component-spec.md src/ infinite
```

## 3. Continuous Claude PR Loop

**A production-grade shell script** running Claude Code in a continuous loop — creating PRs,
waiting for CI, merging automatically (credit: @AnandChowdhary). `SHARED_TASK_NOTES.md` bridges
context across iterations; CI failures recover via `gh run view`; a completion signal stops the
loop; `--worktree` enables parallel execution.

Load `references/continuous-claude.md` for installation, usage, and configuration flags.

## 4. De-Sloppify

**An add-on for any loop:** a dedicated cleanup step after each Implementer step.

Asked to implement with TDD, an LLM takes "write tests" too literally — tests that verify
TypeScript's type system works, defensive runtime checks the type system already guarantees, tests
for framework behaviour rather than business logic, error handling that obscures the code.

**The fix is a separate pass, not a constrained Implementer.** "Don't test type systems" in the
Implementer prompt makes the model hesitant about *all* testing: it skips legitimate edge cases
and quality degrades unpredictably. Let the Implementer be thorough, then:

```bash
claude -p "Review all changes in the working tree. Remove:
- Tests that verify language/framework behavior rather than business logic
- Redundant type checks the type system already enforces
- Over-defensive error handling for impossible states
- Console.log statements
- Commented-out code

Keep all business logic tests. Run the test suite after cleanup to ensure nothing breaks."
```

> Two focused agents outperform one constrained agent.

## 5. Ralphinho / RFC-driven DAG orchestration

**The most sophisticated pattern** (credit: @enitrat). Decomposes a spec into a dependency DAG,
runs each unit through a tiered quality pipeline (trivial/small/medium/large), and lands them via
an agent-driven merge queue with eviction and retry. Each stage runs in its own context window, so
the reviewer never wrote the code it reviews. State persists to SQLite; resumable from any point.

Load `references/ralphinho.md` for the architecture, decomposition rules, complexity tiers, and
the when-to-use decision table.

## 6. Iterative Context Retrieval

Subagents don't know what context they need until they start working. Sending everything blows the
window; guessing produces wrong answers. The fix is a bounded 4-phase loop — **DISPATCH** (broad
Glob/Grep) → **EVALUATE** (score each file 0–1 for relevance) → **REFINE** (adopt the codebase's
actual terminology, exclude dead ends, name the remaining gaps) → **LOOP** — capped at 3 cycles,
passing only files scoring ≥ 0.7 to the real task agent.

Load `references/iterative-retrieval.md` for phase detail, two worked examples, round-by-round
Agent-tool code, and the best-practice rules.

---

## Anti-patterns

1. **Infinite loops with no exit condition** — always set a max-runs, max-cost, max-duration, or
   completion signal.
2. **No context bridge between iterations** — every `claude -p` starts fresh. Use
   `SHARED_TASK_NOTES.md` or filesystem state.
3. **Retrying the same failure** — capture the error context and feed it to the next attempt
   rather than repeating the call.
4. **Negative instructions instead of a cleanup pass** (§4).
5. **All agents in one context window** — separate concerns into different processes. **The
   reviewer must never be the author**; this is why §5 gives each stage its own window, and why
   any loop benefits from an explicit verification pass (a separate `claude -p` review over the
   diff, or `/code-review` interactively) as a gate before commits.
6. **Ignoring file overlap in parallel work** — two agents that might edit the same file need a
   merge strategy: sequential landing, rebase, or conflict resolution.

## Credits

| Project | Author |
|---------|--------|
| Ralphinho | @enitrat |
| Infinite Agentic Loop | @disler |
| Continuous Claude | @AnandChowdhary |
| NanoClaw | ECC (upstream installs only) |
