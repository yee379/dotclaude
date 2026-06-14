---
name: multi-agent-handbook
description: "Patterns and architectures for multi-agent systems — from simple sequential pipelines to RFC-driven DAG orchestration, including iterative context retrieval for subagents."
origin: ECC
---

# Multi-Agent Handbook

Patterns, architectures, and reference implementations for running Claude Code in multi-agent systems. Covers everything from simple `claude -p` pipelines to full RFC-driven multi-agent DAG orchestration, plus iterative context retrieval for subagents.

## When to Use

- Setting up autonomous development workflows that run without human intervention
- Choosing the right loop architecture for your problem (simple vs complex)
- Building CI/CD-style continuous development pipelines
- Running parallel agents with merge coordination
- Implementing context persistence across loop iterations
- Adding quality gates and cleanup passes to autonomous workflows
- Spawning subagents that need progressively refined codebase context
- Solving "context too large" or "missing context" failures in agent tasks

## Loop Pattern Spectrum

From simplest to most sophisticated:

| Pattern | Complexity | Best For |
|---------|-----------|----------|
| [Sequential Pipeline](#1-sequential-pipeline-claude--p) | Low | Daily dev steps, scripted workflows |
| [NanoClaw REPL](#2-nanoclaw-repl) | Low | Interactive persistent sessions |
| [Infinite Agentic Loop](#3-infinite-agentic-loop) | Medium | Parallel content generation, spec-driven work |
| [Continuous Claude PR Loop](#4-continuous-claude-pr-loop) | Medium | Multi-day iterative projects with CI gates |
| [De-Sloppify Pattern](#5-the-de-sloppify-pattern) | Add-on | Quality cleanup after any Implementer step |
| [Ralphinho / RFC-Driven DAG](#6-ralphinho--rfc-driven-dag-orchestration) | High | Large features, multi-unit parallel work with merge queue |

---

## 1. Sequential Pipeline (`claude -p`)

**The simplest loop.** Break daily development into a sequence of non-interactive `claude -p` calls. Each call is a focused step with a clear prompt.

### Core Insight

> If you can't figure out a loop like this, it means you can't even drive the LLM to fix your code in interactive mode.

The `claude -p` flag runs Claude Code non-interactively with a prompt, exits when done. Chain calls to build a pipeline:

```bash
#!/bin/bash
# daily-dev.sh — Sequential pipeline for a feature branch

set -e

# Step 1: Implement the feature
claude -p "Read the spec in docs/auth-spec.md. Implement OAuth2 login in src/auth/. Write tests first (TDD). Do NOT create any new documentation files."

# Step 2: De-sloppify (cleanup pass)
claude -p "Review all files changed by the previous commit. Remove any unnecessary type tests, overly defensive checks, or testing of language features (e.g., testing that TypeScript generics work). Keep real business logic tests. Run the test suite after cleanup."

# Step 3: Verify
claude -p "Run the full build, lint, type check, and test suite. Fix any failures. Do not add new features."

# Step 4: Commit
claude -p "Create a conventional commit for all staged changes. Use 'feat: add OAuth2 login flow' as the message."
```

### Key Design Principles

1. **Each step is isolated** — A fresh context window per `claude -p` call means no context bleed between steps.
2. **Order matters** — Steps execute sequentially. Each builds on the filesystem state left by the previous.
3. **Negative instructions are dangerous** — Don't say "don't test type systems." Instead, add a separate cleanup step (see [De-Sloppify Pattern](#5-the-de-sloppify-pattern)).
4. **Exit codes propagate** — `set -e` stops the pipeline on failure.

### Variations

**With model routing:**
```bash
# Model tiers (Claude Code resolves these to current IDs automatically):
#   opus   — most capable; use for complex reasoning, planning, and review
#   sonnet — balanced; default for most tasks
#   haiku  — fastest/cheapest; use for simple transformations and classification

# Research with opus (deep reasoning)
claude -p --model opus "Analyze the codebase architecture and write a plan for adding caching..."

# Implement with sonnet (fast, capable)
claude -p "Implement the caching layer according to the plan in docs/caching-plan.md..."

# Review with opus (thorough)
claude -p --model opus "Review all changes for security issues, race conditions, and edge cases..."
```

**With environment context:**
```bash
# Pass context via files, not prompt length
echo "Focus areas: auth module, API rate limiting" > .claude-context.md
claude -p "Read .claude-context.md for priorities. Work through them in order."
rm .claude-context.md
```

**With `--allowedTools` restrictions:**
```bash
# Read-only analysis pass
claude -p --allowedTools "Read,Grep,Glob" "Audit this codebase for security vulnerabilities..."

# Write-only implementation pass
claude -p --allowedTools "Read,Write,Edit,Bash" "Implement the fixes from security-audit.md..."
```

---

## 2. NanoClaw REPL

**ECC's built-in persistent loop.** Calls `claude -p` with full conversation history persisted to `~/.claude/claw/{session}.md`. Best for interactive exploration; use Sequential Pipeline for scripted automation.

```bash
node scripts/claw.js                                                    # default session
CLAW_SESSION=my-project CLAW_SKILLS=tdd-standards,security-review node scripts/claw.js
```

See the `/claw` command for full documentation.

---

## 3. Infinite Agentic Loop

**A two-prompt system** that orchestrates parallel sub-agents for specification-driven generation. Developed by disler (credit: @disler).

### Architecture: Two-Prompt System

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

### The Pattern

1. **Spec Analysis** — Orchestrator reads a specification file (Markdown) defining what to generate
2. **Directory Recon** — Scans existing output to find the highest iteration number
3. **Parallel Deployment** — Launches N sub-agents, each with:
   - The full spec
   - A unique creative direction
   - A specific iteration number (no conflicts)
   - A snapshot of existing iterations (for uniqueness)
4. **Wave Management** — For infinite mode, deploys waves of 3-5 agents until context is exhausted

### Implementation via Claude Code Commands

Create `.claude/commands/infinite.md`:

See `references/subagent-prompts.md` — "Infinite Agentic Loop" for the full subagent prompt.

**Invoke:**
```bash
/project:infinite specs/component-spec.md src/ 5
/project:infinite specs/component-spec.md src/ infinite
```

### Batching Strategy

| Count | Strategy |
|-------|----------|
| 1-5 | All agents simultaneously |
| 6-20 | Batches of 5 |
| infinite | Waves of 3-5, progressive sophistication |

### Key Insight: Uniqueness via Assignment

Don't rely on agents to self-differentiate. The orchestrator **assigns** each agent a specific creative direction and iteration number. This prevents duplicate concepts across parallel agents.

---

## 4. Continuous Claude PR Loop

**A production-grade shell script** that runs Claude Code in a continuous loop, creating PRs, waiting for CI, and merging automatically. Created by AnandChowdhary (credit: @AnandChowdhary).

Key features: `SHARED_TASK_NOTES.md` bridges context across iterations; automatic CI failure recovery via `gh run view`; completion signal stops the loop; `--worktree` enables parallel execution.

Load `references/continuous-claude.md` for the full installation, usage examples, and configuration flags.

---

## 5. The De-Sloppify Pattern

**An add-on pattern for any loop.** Add a dedicated cleanup/refactor step after each Implementer step.

### The Problem

When you ask an LLM to implement with TDD, it takes "write tests" too literally:
- Tests that verify TypeScript's type system works (testing `typeof x === 'string'`)
- Overly defensive runtime checks for things the type system already guarantees
- Tests for framework behavior rather than business logic
- Excessive error handling that obscures the actual code

### Why Not Negative Instructions?

Adding "don't test type systems" or "don't add unnecessary checks" to the Implementer prompt has downstream effects:
- The model becomes hesitant about ALL testing
- It skips legitimate edge case tests
- Quality degrades unpredictably

### The Solution: Separate Pass

Instead of constraining the Implementer, let it be thorough. Then add a focused cleanup agent:

```bash
# Step 1: Implement (let it be thorough)
claude -p "Implement the feature with full TDD. Be thorough with tests."

# Step 2: De-sloppify (separate context, focused cleanup)
claude -p "Review all changes in the working tree. Remove:
- Tests that verify language/framework behavior rather than business logic
- Redundant type checks that the type system already enforces
- Over-defensive error handling for impossible states
- Console.log statements
- Commented-out code

Keep all business logic tests. Run the test suite after cleanup to ensure nothing breaks."
```

### In a Loop Context

```bash
for feature in "${features[@]}"; do
  # Implement
  claude -p "Implement $feature with TDD."

  # De-sloppify
  claude -p "Cleanup pass: review changes, remove test/code slop, run tests."

  # Verify
  claude -p "Run build + lint + tests. Fix any failures."

  # Commit
  claude -p "Commit with message: feat: add $feature"
done
```

### Key Insight

> Rather than adding negative instructions which have downstream quality effects, add a separate de-sloppify pass. Two focused agents outperform one constrained agent.

---

## 6. Ralphinho / RFC-Driven DAG Orchestration

**The most sophisticated pattern.** An RFC-driven, multi-agent pipeline that decomposes a spec into a dependency DAG, runs each unit through a tiered quality pipeline (trivial/small/medium/large), and lands them via an agent-driven merge queue with eviction + retry. Created by enitrat (credit: @enitrat).

Each stage runs in its own context window — the reviewer never wrote the code it reviews, eliminating author bias. Full state persisted to SQLite; resumable from any point.

Load `references/ralphinho.md` for the full architecture, decomposition rules, complexity tiers, and when-to-use decision table.

---

## Choosing the Right Pattern

### Decision Matrix

```
Is the task a single focused change?
├─ Yes → Sequential Pipeline or NanoClaw
└─ No → Is there a written spec/RFC?
         ├─ Yes → Do you need parallel implementation?
         │        ├─ Yes → Ralphinho (DAG orchestration)
         │        └─ No → Continuous Claude (iterative PR loop)
         └─ No → Do you need many variations of the same thing?
                  ├─ Yes → Infinite Agentic Loop (spec-driven generation)
                  └─ No → Sequential Pipeline with de-sloppify
```

### Combining Patterns

These patterns compose well:

1. **Sequential Pipeline + De-Sloppify** — The most common combination. Every implement step gets a cleanup pass.

2. **Continuous Claude + De-Sloppify** — Add `--review-prompt` with a de-sloppify directive to each iteration.

3. **Any loop + Verification** — Use ECC's `/verify` command as a quality gate before commits.

4. **Ralphinho's tiered approach in simpler loops** — Even in a sequential pipeline, you can route simple tasks to `haiku` and complex tasks to `opus`:
   ```bash
   # Simple formatting fix
   claude -p --model haiku "Fix the import ordering in src/utils.ts"

   # Complex architectural change
   claude -p --model opus "Refactor the auth module to use the strategy pattern"
   ```

---

## Anti-Patterns

### Common Mistakes

1. **Infinite loops without exit conditions** — Always have a max-runs, max-cost, max-duration, or completion signal.

2. **No context bridge between iterations** — Each `claude -p` call starts fresh. Use `SHARED_TASK_NOTES.md` or filesystem state to bridge context.

3. **Retrying the same failure** — If an iteration fails, don't just retry. Capture the error context and feed it to the next attempt.

4. **Negative instructions instead of cleanup passes** — Don't say "don't do X." Add a separate pass that removes X.

5. **All agents in one context window** — For complex workflows, separate concerns into different agent processes. The reviewer should never be the author.

6. **Ignoring file overlap in parallel work** — If two parallel agents might edit the same file, you need a merge strategy (sequential landing, rebase, or conflict resolution).

---

## References

| Project | Author | Link |
|---------|--------|------|
| Ralphinho | enitrat | credit: @enitrat |
| Infinite Agentic Loop | disler | credit: @disler |
| Continuous Claude | AnandChowdhary | credit: @AnandChowdhary |
| NanoClaw | ECC | `/claw` command in this repo |

---

## 7. Iterative Context Retrieval

Solves the "context problem" in multi-agent workflows where subagents don't know what context they need until they start working.

### The Problem

Subagents are spawned with limited context. They don't know:
- Which files contain relevant code
- What patterns exist in the codebase
- What terminology the project uses

Standard approaches fail:
- **Send everything**: Exceeds context limits
- **Send nothing**: Agent lacks critical information
- **Guess what's needed**: Often wrong

### The Solution: Iterative Retrieval

A 4-phase loop that progressively refines context:

```
┌─────────────────────────────────────────────┐
│                                             │
│   ┌──────────┐      ┌──────────┐            │
│   │ DISPATCH │─────▶│ EVALUATE │            │
│   └──────────┘      └──────────┘            │
│        ▲                  │                 │
│        │                  ▼                 │
│   ┌──────────┐      ┌──────────┐            │
│   │   LOOP   │◀─────│  REFINE  │            │
│   └──────────┘      └──────────┘            │
│                                             │
│        Max 3 cycles, then proceed           │
└─────────────────────────────────────────────┘
```

**Phase 1 — DISPATCH:** Broad initial search for candidate files using Glob/Grep on likely patterns and keywords.

**Phase 2 — EVALUATE:** Assess each file: is it directly relevant (0.8–1.0), related (0.5–0.7), tangential (0.2–0.4), or irrelevant (<0.2)?

**Phase 3 — REFINE:** Add terminology discovered in high-relevance files; exclude confirmed-irrelevant paths; add focus areas for identified gaps.

**Phase 4 — LOOP:** Repeat with refined criteria. Stop early if 3+ high-relevance files found with no critical gaps. Hard cap: 3 cycles.

### Practical Examples

#### Example 1: Bug Fix Context

```
Task: "Fix the authentication token expiry bug"

Cycle 1:
  DISPATCH: Search for "token", "auth", "expiry" in src/**
  EVALUATE: Found auth.ts (0.9), tokens.ts (0.8), user.ts (0.3)
  REFINE: Add "refresh", "jwt" keywords; exclude user.ts

Cycle 2:
  DISPATCH: Search refined terms
  EVALUATE: Found session-manager.ts (0.95), jwt-utils.ts (0.85)
  REFINE: Sufficient context (2 high-relevance files)

Result: auth.ts, tokens.ts, session-manager.ts, jwt-utils.ts
```

#### Example 2: Feature Implementation

```
Task: "Add rate limiting to API endpoints"

Cycle 1:
  DISPATCH: Search "rate", "limit", "api" in routes/**
  EVALUATE: No matches - codebase uses "throttle" terminology
  REFINE: Add "throttle", "middleware" keywords

Cycle 2:
  DISPATCH: Search refined terms
  EVALUATE: Found throttle.ts (0.9), middleware/index.ts (0.7)
  REFINE: Need router patterns

Cycle 3:
  DISPATCH: Search "router", "express" patterns
  EVALUATE: Found router-setup.ts (0.8)
  REFINE: Sufficient context

Result: throttle.ts, middleware/index.ts, router-setup.ts
```

### Integration with Agents

Use in agent prompts:

```markdown
When retrieving context for this task:
1. Start with broad keyword search
2. Evaluate each file's relevance (0-1 scale)
3. Identify what context is still missing
4. Refine search criteria and repeat (max 3 cycles)
5. Return files with relevance >= 0.7
```

### Concrete Agent Tool Example

```
// Round 1 — broad search
Agent(
  subagent_type: "general-purpose",
  prompt: `Search the codebase for files relevant to: "<task>".
Use Glob and Grep. Return a JSON array:
[{"path": "...", "relevance": 0.0-1.0, "reason": "...", "gaps": ["..."]}]`
)

// Round 1 result example:
// [
//   {"path": "src/auth/token.ts",   "relevance": 0.9, "reason": "JWT handling", "gaps": ["refresh logic"]},
//   {"path": "src/auth/session.ts", "relevance": 0.7, "reason": "session store", "gaps": []},
//   {"path": "src/user/profile.ts", "relevance": 0.2, "reason": "tangential",   "gaps": []}
// ]

// Extract gaps from high-relevance files (relevance >= 0.7)
// gaps = ["refresh logic"]
// Drop low-relevance files: profile.ts excluded

// Round 2 — targeted gap search
Agent(
  subagent_type: "general-purpose",
  prompt: `Search for files covering these gaps: ["refresh logic"].
Already found (skip): src/auth/token.ts, src/auth/session.ts
Return JSON: [{"path": "...", "relevance": 0.0-1.0, "reason": "...", "gaps": ["..."]}]`
)

// Round 2 result example:
// [{"path": "src/auth/refresh.ts", "relevance": 0.95, "reason": "token refresh endpoint", "gaps": []}]

// Sufficient context — no critical gaps remain. Dispatch real task.
Agent(
  subagent_type: "general-purpose",
  prompt: `Task: <task>

Relevant files (read these first):
- src/auth/token.ts      (JWT handling)
- src/auth/session.ts    (session store)
- src/auth/refresh.ts    (token refresh)

<full task instructions>`
)
```

**Key rules:**
- Pass only relative file paths to subagents
- Cap at 3 retrieval cycles — at cycle 3, proceed with best available context
- Only pass files with relevance >= 0.7 to the real task subagent
- Include the "already found, skip" list in round 2+ to avoid duplicates

### Best Practices

1. **Start broad, narrow progressively** — Don't over-specify initial queries
2. **Learn codebase terminology** — First cycle often reveals naming conventions
3. **Track what's missing** — Explicit gap identification drives refinement
4. **Stop at "good enough"** — 3 high-relevance files beats 10 mediocre ones
5. **Exclude confidently** — Low-relevance files won't become relevant
