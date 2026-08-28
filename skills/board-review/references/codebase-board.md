# Codebase Board — Reviewer Configuration

## Reviewers and model routing

All reviewers run at **opus**. Do not downgrade to Sonnet.

| Reviewer | Code | Role |
|---|---|---|
| research | `dr` | Fact-check plan assumptions, check dependency health, identify obsolescence risks and simplification opportunities. See `/research` Mode 2 guidelines. |
| codebase-arch-review | `ar` | Evaluate service boundaries, data ownership, consistency models, technology selection, failure domains. Write ADRs to `docs/adr/` for significant decisions. |
| codebase-eng-review | `er` | Review implementation correctness, test coverage, performance, edge cases. Produce a test plan artifact in the task file. |
| doc-review | `dc` | Identify every doc that needs updating — README, ARCHITECTURE, API docs, runbooks, CHANGELOG, ADRs, CONTRIBUTING. Add gaps to the plan. |
| security-review | `sr` | Check secrets, auth, input validation, injection vectors, supply chain, Kubernetes workload security. |
| codebase-ux-review | `ux` | Evaluate the feature through the eyes of an S3DF scientist — discoverability, first-use clarity, documentation quality, error UX, and workflow fit. |

`codebase-ux-review` is triage-gated — skip if the change has no direct user-facing surface area.

## Triage skip conditions

| Reviewer | Skip if… |
|---|---|
| research | the technology and approach are well-understood — no unknowns that would make the plan speculative |
| codebase-arch-review | change touches only a single existing service with no new data stores, no new async channels, no service boundary changes, and no new infrastructure |
| codebase-eng-review | change is purely documentation or config with no code changes |
| doc-review | change is purely internal/infra with no user-facing surface, no API changes, no new commands or config |
| security-review | change has no user input, no auth changes, no new API endpoints, no secrets, no new K8s workloads |
| codebase-ux-review | change has no direct user-facing surface — pure internal/infra, backend refactor, or platform-only work with no new CLI, API, docs, or workflows that scientists interact with directly |

## Plan excerpt routing

| Reviewer | Sections to include |
|---|---|
| research | Problem Statement, Goals, Design (full), Open Questions |
| codebase-arch-review | Problem Statement, Goals, Design (full), Non-Goals, Open Questions |
| codebase-eng-review | Problem Statement, Goals, Design (full), Implementation Plan, Implementation Checklist, Open Questions |
| doc-review | Problem Statement, Goals, Non-Goals, Implementation Plan (step titles only) |
| security-review | Problem Statement, Design (full), Implementation Plan (step titles only), Open Questions |
| codebase-ux-review | Problem Statement, Goals, Non-Goals, Design (full), Open Questions |

If the task file has no Design section or it is a stub, include the full file for all reviewers.

## Priority hierarchy (for subagent prompts)

Most important sections first — subagents complete these before lower-priority ones:

- codebase-arch-review: Step 0 scope assessment → service boundary diagram → ADRs
- codebase-eng-review: Step 0 scope challenge → test diagram → critical gaps
- research: assumption verification → dependency health → obsolescence
- doc-review: mandatory doc list → gaps
- security-review: auth/authz → injection → secrets

## Final summary metrics block

```
research        {✅/⚠️/❌/—}  {N issues}
codebase-arch-review     {✅/⚠️/❌/—}  {N issues}
codebase-eng-review      {✅/⚠️/❌/—}  {N issues}
doc-review               {✅/⚠️/❌/—}  {N issues}
security-review          {✅/⚠️/❌/—}  {N issues}
codebase-ux-review       {✅/⚠️/❌/—}  {N issues}
------------------------------------------------------------
ADRs written:          {N}  (in docs/adr/)
Test plan written:     {Y/N}  (in todo/ task file)
Doc gaps added:        {N}
Accepted warnings:     {N}
Blocking issues:       {N}
Opportunities logged:  {N}  (non-blocking, in task file follow-ups)
```

## Round dashboard rows

```
research        ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
codebase-arch-review     ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
codebase-eng-review      ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
doc-review               ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
security-review          ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
codebase-ux-review       ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
```

## Verdict labels

- **CLEAR TO BUILD** — all reviewers passed, no unresolved issues
- **CLEAR WITH WARNINGS** — all passed, user accepted risk on some issues; list accepted warnings
- **BLOCKED** — one or more reviewers failed; list blocking issues. A reviewer FAIL must name an
  **unresolved** defect — one it could not fix by amendment, or one left open for a human. A reviewer
  that found serious gaps and then amended them away has not failed; it has done its job, and the
  amendment already triggers another round on its own. Do not let a rubric score, an amendment count,
  or "re-score me next round" produce a FAIL: BLOCKED sends the task back to `⬜ Open`, which is a
  claim about the plan's viability, not about how much work the review did.
- **UNSTABLE** — **`design:` amendments** were still happening in round 3; list what was still
  changing. Round 3 producing only `precision:` amendments is CLEAR (or CLEAR WITH WARNINGS), not
  UNSTABLE — a plan being polished is not a plan that failed to stabilise. Always state the ratio
  `N design / M precision` alongside the verdict.

## No-plan stop message

> "No plan found. Run `/draft-prd` first to produce a design document, then come back to `/board-review`."

## After-review: next steps

If verdict is CLEAR TO BUILD or CLEAR WITH WARNINGS:

```
✅ #NNN <title> — CLEAR TO BUILD

#NNN todo/<slug>.md
     ↓
/prd-workflow            ← track progress, keep TODO.md in sync
     ↓
/tdd-standards       ← tests first, then implementation
     ↓
/closeout-prd #NNN   ← close out task, apply doc updates, sync TODO.md
     ↓
/prod-release        ← promote through environments
```

If verdict is BLOCKED or UNSTABLE:
> "Resolve the issues above, then re-run `/board-review`."

## Commit messages

- CLEAR: `docs(todo): merge board review into #NNN task file [board-review]`
- BLOCKED: `docs(todo): merge blocked board review into #NNN task file [board-review]`
