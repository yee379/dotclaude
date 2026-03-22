---
name: iterative-retrieval
description: Pattern for progressively refining context retrieval to solve the subagent context problem
origin: ECC
---

# Iterative Retrieval Pattern

Solves the "context problem" in multi-agent workflows where subagents don't know what context they need until they start working.

## When to Activate

- Spawning subagents that need codebase context they cannot predict upfront
- Building multi-agent workflows where context is progressively refined
- Encountering "context too large" or "missing context" failures in agent tasks
- Designing RAG-like retrieval pipelines for code exploration
- Optimizing token usage in agent orchestration

## The Problem

Subagents are spawned with limited context. They don't know:
- Which files contain relevant code
- What patterns exist in the codebase
- What terminology the project uses

Standard approaches fail:
- **Send everything**: Exceeds context limits
- **Send nothing**: Agent lacks critical information
- **Guess what's needed**: Often wrong

## The Solution: Iterative Retrieval

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

## Practical Examples

### Example 1: Bug Fix Context

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

### Example 2: Feature Implementation

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

## Integration with Agents

Use in agent prompts:

```markdown
When retrieving context for this task:
1. Start with broad keyword search
2. Evaluate each file's relevance (0-1 scale)
3. Identify what context is still missing
4. Refine search criteria and repeat (max 3 cycles)
5. Return files with relevance >= 0.7
```

## Best Practices

1. **Start broad, narrow progressively** - Don't over-specify initial queries
2. **Learn codebase terminology** - First cycle often reveals naming conventions
3. **Track what's missing** - Explicit gap identification drives refinement
4. **Stop at "good enough"** - 3 high-relevance files beats 10 mediocre ones
5. **Exclude confidently** - Low-relevance files won't become relevant

## Concrete Agent Tool Example

Use this pattern when orchestrating subagents in Claude Code:

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
- Pass only absolute file paths (not `~`-prefixed) to subagents
- Cap at 3 retrieval cycles — at cycle 3, proceed with best available context
- Only pass files with relevance >= 0.7 to the real task subagent
- Include the "already found, skip" list in round 2+ to avoid duplicates

## Related

- `multi-agent-handbook` skill — loop architectures that use iterative retrieval as a context phase
