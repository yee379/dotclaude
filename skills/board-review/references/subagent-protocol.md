# Subagent Protocol — Reviewers Running Inside /board-review

Shared by `codebase-arch-review`, `codebase-eng-review`, `codebase-ux-review`, `doc-review`,
and `security-review`. The orchestrator provides two paths:

- `Plan file:` — path to read from disk
- `Output file:` — path to write findings to (e.g. `todo/review/<slug>/round-N-<xx>.md`)

**If an output file path was provided, follow this protocol exactly.**

## 1. Write the skeleton first

Before any analysis, create the output file:

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

## 2. Write after every checkpoint

Each skill names its own checkpoints (its review sections or scored dimensions). After each one:

- Append new issues/findings to `## Issues`
- Append any new `### Decision:` entries to `## Decisions Required`
- Append any plan amendments made
- Do NOT wait until the end — write each checkpoint's findings immediately

## 3. Suppress AskUserQuestion

Do not call AskUserQuestion. For every decision point, write a structured `### Decision:` entry
in `## Decisions Required` and continue with the best safe default, documenting the assumption
explicitly.

## 4. Write ## Summary and final ## Status last

Replace the `_(written last)_` placeholder only after all checkpoints are complete. Set
`## Status` to `PASS` | `PASS WITH WARNINGS` | `FAIL` — unless the skill defines its own
scoring thresholds, which take precedence.
