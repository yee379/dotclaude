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
- Append any plan amendments made, each tagged per §2a
- Do NOT wait until the end — write each checkpoint's findings immediately

## 2a. Tag every amendment `design:` or `precision:`

Each line in `## Amendments` carries exactly one prefix:

- `design:` — the plan as written would produce wrong, unsafe, or unbuildable behaviour. Fixing it
  changes what gets built.
- `precision:` — the plan disagrees with itself or with the repo: stale citation, duplicated value,
  a rule restated inconsistently, an over-scoped claim, a row in the wrong delivery slice. Fixing it
  changes only the text.

End the section with `TOTAL: N design, M precision`.

The orchestrator decides whether to spend another round based on the `design:` count alone, so the
tag must be honest both ways: a design defect tagged `precision:` ships a real bug; a precision fix
tagged `design:` forces a needless round.

**Precision ceiling.** Past ~10 precision amendments, stop editing and collapse the remainder into a
single `## Issues` line — "N further precision defects of the same class" — with the list beneath it.
An undifferentiated wall of cosmetic edits is indistinguishable from instability, and it gets plans
blocked that nobody found fault with.

## 3. Suppress AskUserQuestion

Do not call AskUserQuestion. For every decision point, write a structured `### Decision:` entry
in `## Decisions Required` and continue with the best safe default, documenting the assumption
explicitly.

## 4. Write ## Summary and final ## Status last

Replace the `_(written last)_` placeholder only after all checkpoints are complete. Set
`## Status` to `PASS` | `PASS WITH WARNINGS` | `FAIL` — unless the skill defines its own
scoring thresholds, which take precedence.
