---
name: agentic-standards
description: Standards for agentic engineering — eval-first execution, task decomposition, cost-aware model routing, and slop-free writing in agent-authored PRs, ADRs, docs, and review comments. Edits or audits drafts on request.
origin: ECC
---

# Agentic Standards

Use this skill for workflows where AI agents perform most implementation work and humans enforce quality and risk controls.

## Operating Principles

1. Define completion criteria before execution.
2. Decompose work into agent-sized units.
3. Route model tiers by task complexity.
4. Measure with evals and regression checks.

## Eval-First Loop

1. Define capability eval and regression eval.
2. Run baseline and capture failure signatures.
3. Execute implementation.
4. Re-run evals and compare deltas.

## Task Decomposition

Apply the 15-minute unit rule:
- each unit should be independently verifiable
- each unit should have a single dominant risk
- each unit should expose a clear done condition

## Model Routing

See `/multi-agent-handbook` Section 1 for the full model routing matrix. Summary:
- haiku: classification, boilerplate transforms, narrow edits, git operations
- sonnet: implementation and refactors, default model, everything else
- opus: architecture, root-cause analysis, troubleshoot, multi-file invariants, research, reviews, planning

## Session Strategy

- Continue session for closely-coupled units.
- Start fresh session after major phase transitions.
- Compact after milestone completion, not during active debugging.

## Work Isolation & Commit Discipline

- One worktree per work stream, each on its own new branch. Never mix unrelated tasks, parallel
  agents, or independent features in the same working tree or branch — `git worktree add -b
  <branch> <path>` a fresh worktree+branch per unit of work. A branch can't be checked out in two
  worktrees at once, so this also stops parallel agents from colliding on the same branch.
- Commit every major procedure as it completes: each eval-first loop, each task-decomposition
  unit, each phase transition. Uncommitted work does not count as done.
- Commit messages: ultra terse. One line, imperative, conventional-commit type prefix (`feat:`,
  `fix:`, `docs:`, `refactor:`, ...), subject only — no body, no restating the diff, no filler.
  Reserve a body only for an irreversible or high-risk change that needs a rollback note.

## Review Focus for AI-Generated Code

Prioritize:
- invariants and edge cases
- error boundaries
- security and auth assumptions
- hidden coupling and rollout risk

Do not waste review cycles on style-only disagreements when automated format/lint already enforce style.

## Cost Discipline

Track per task:
- model
- token estimate
- retries
- wall-clock time
- success/failure

Escalate model tier only when lower tier fails with a clear reasoning gap.

## Writing Standards for Agent-Authored Prose

Agents generate most of the prose in a repo: PR and commit descriptions, ADRs, design docs,
review comments, runbooks, incident write-ups, status summaries. Nobody edits it, so slop
accumulates where it is hardest to remove later.

Treat writing like code: it gets an eval. Before shipping prose others will read, run the
checklist in `references/no-ai-slop-eval.md`. If a check fails, fix it and run again.

The highest-value rules, applied to your own output:

1. Be concrete. "Cut deploy time from 40 minutes to 4" beats "improved efficiency."
2. Apply the portability test. A sentence that could move unchanged to another project is filler.
3. Show instead of labelling. Don't call a point important, surprising, or subtle. Demonstrate it.
4. Name sources. Replace "studies show" and "widely regarded as" with a citation or cut the claim.
5. End on the last concrete point. No summary recaps, no fake-profound kickers.
6. Let format follow content. No emoji headings, decorative bold, or headers over two sentences.

Never invent claims, numbers, or citations to satisfy a rule. If a fact is missing, ask.

Load `references/no-ai-slop.md` in full when:
- editing a draft the user supplies
- auditing a draft for slop without rewriting it (detect mode)
- writing a document long enough that the six rules above are not enough

Load `references/technical-prose.md` when generating a document that persists in the repo: an
ADR, PRD, todo task file, research report, runbook, incident write-up, review findings file, or
README section. The six rules and `no-ai-slop.md` both assume a human draft with a voice to
preserve; a document generated from scratch has neither, and needs the tense, evidence-marking,
and session-leakage rules that file supplies.

## Reference material

| Topic | File |
|---|---|
| Editing principles, banned words, slop patterns, edit/detect/self-check workflow | `references/no-ai-slop.md` |
| Pass/fail checklist to run after any rewrite | `references/no-ai-slop-eval.md` |
| Generative voice for persisted technical documents: reader model, tense, evidence marking, format choice | `references/technical-prose.md` |

## Architecture for Agent-Friendly Systems

Prefer architectures that are agent-friendly:
- explicit boundaries
- stable contracts
- typed interfaces
- deterministic tests

Avoid implicit behavior spread across hidden conventions.

