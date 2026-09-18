---
name: strategic-compact
description: Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary auto-compaction.
origin: ECC
---

# Strategic Compact Skill

Suggests manual `/compact` at strategic points rather than arbitrary auto-compaction. Use in long
sessions near context limits, multi-phase tasks (research → plan → implement → test), when
switching between unrelated tasks, and when responses degrade under context pressure.

## How it works

`suggest-compact.js` runs on PreToolUse (Edit/Write): it counts tool invocations, suggests at a
threshold (`COMPACT_THRESHOLD`, default 50), then reminds every 25 calls after that.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "node ~/.claude/skills/strategic-compact/suggest-compact.js" }]
      },
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "node ~/.claude/skills/strategic-compact/suggest-compact.js" }]
      }
    ]
  }
}
```

## When to compact

| Phase transition | Compact? | Why |
|-----------------|----------|-----|
| Research → Planning | Yes | Research context is bulky; the plan is the distilled output |
| Planning → Implementation | Yes | Plan lives in TodoWrite or a file; free context for code |
| Implementation → Testing | Maybe | Keep if tests reference recent code; compact if switching focus |
| Debugging → Next feature | Yes | Debug traces pollute context for unrelated work |
| After a failed approach | Yes | Clear the dead-end reasoning before trying something new |
| Mid-implementation | No | Losing variable names, file paths, and partial state is costly |

## What survives

| Persists | Lost |
|----------|------|
| CLAUDE.md instructions | Intermediate reasoning and analysis |
| TodoWrite task list | File contents you previously read |
| MemPalace drawers (`mcp__mempalace__*`) | Multi-step conversation context |
| Git state (commits, branches) | Tool call history and counts |
| Files on disk | Nuanced user preferences stated verbally |

## Practices

1. **The hook tells you *when*; you decide *if*.**
2. **Write before compacting** — save key context to a file or a MemPalace drawer
   (`mcp__mempalace__mempalace_add_drawer`) so it stays retrievable instead of living only in
   context. Recover it with `mcp__mempalace__mempalace_search` (keywords, not a sentence).
3. **Compact with a summary** — `/compact Focus on implementing auth middleware next`
