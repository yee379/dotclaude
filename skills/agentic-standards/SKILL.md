---
name: agentic-standards
description: Operate as an agentic engineer using eval-first execution, decomposition, and cost-aware model routing.
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

- haiku: classification, boilerplate transforms, narrow edits, git operations
- opus: architecture, root-cause analysis, troubleshooting, multi-file invariants, research, investigations, reviews, planning
- sonnet: implementation and refactors, default model, everything else

## Session Strategy

- Continue session for closely-coupled units.
- Start fresh session after major phase transitions.
- Compact after milestone completion, not during active debugging.

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

## Architecture for Agent-Friendly Systems

Prefer architectures that are agent-friendly:
- explicit boundaries
- stable contracts
- typed interfaces
- deterministic tests

Avoid implicit behavior spread across hidden conventions.

## Hiring and Evaluation Signals

Strong AI-first engineers:
- decompose ambiguous work cleanly
- define measurable acceptance criteria
- produce high-signal prompts and evals
- enforce risk controls under delivery pressure
