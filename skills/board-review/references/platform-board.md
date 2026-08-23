# Platform Board — Reviewer Configuration

## Reviewers and model routing

`codebase-arch-review` (platform mode) and `platform-security-review` run at **opus**.
`platform-capacity-review`, `platform-ops-review`, `platform-eng-review`, `doc-review` run at **sonnet**.

| Reviewer | Code | Model | Role |
|---|---|---|---|
| codebase-arch-review (platform mode) | `pa` | opus | Evaluate topology, service boundaries, data ownership, failure domains from a platform perspective. Write ADRs for significant decisions. |
| platform-capacity-review | `cr` | sonnet | Assess resource consumption, scaling headroom, storage growth, and quota impact. |
| platform-security-review | `ps` | opus | Check RBAC, network policies, secrets management, workload security, and compliance posture. |
| platform-ops-review | `po` | sonnet | Evaluate operational readiness — runbooks, alerting, rollback procedures, on-call impact. |
| platform-eng-review | `pe` | sonnet | Review manifest correctness, Helm chart quality, CI/CD integration, implementation checklist. |
| doc-review | `dc` | sonnet | Identify every doc that needs updating — runbooks, ADRs, operator guides, CHANGELOG. Add gaps to the plan. |

## Triage skip conditions

| Reviewer | Skip if… |
|---|---|
| codebase-arch-review | change is purely operational (tuning replicas, updating a ConfigMap) with no topology or boundary changes |
| platform-capacity-review | change removes workloads or is purely config with no new resource consumption |
| platform-security-review | change has no new workloads, no RBAC changes, no network policy changes, no new secrets |
| platform-ops-review | change is purely infrastructure with no new failure modes and no runbook impact |
| platform-eng-review | change is purely documentation or config with no manifest changes |
| doc-review | change is purely internal infra with no operator or user-facing surface area |

## Plan excerpt routing

| Reviewer | Sections to include |
|---|---|
| codebase-arch-review (platform mode) | Problem Statement, Goals, Platform Design (full), Non-Goals, Open Questions |
| platform-capacity-review | Problem Statement, Goals, Platform Design (Capacity Assessment section), Non-Goals |
| platform-security-review | Problem Statement, Platform Design (Security Posture section + topology), Open Questions |
| platform-ops-review | Problem Statement, Goals, Platform Design (Operational Readiness section), Implementation Plan |
| platform-eng-review | Problem Statement, Goals, Platform Design (full), Implementation Plan, Implementation Checklist |
| doc-review | Problem Statement, Goals, Non-Goals, Implementation Plan (step titles only) |

If the task file has no Platform Design section or it is a stub, include the full file for all reviewers.

## Priority hierarchy (for subagent prompts)

Most important sections first:

- codebase-arch-review: topology diagram → boundary changes → ADRs
- platform-security-review: RBAC review → network policies → secrets
- platform-eng-review: manifest correctness → checklist gaps
- platform-ops-review: runbook gaps → alert coverage
- platform-capacity-review: resource budget → quota impact
- doc-review: mandatory doc list → gaps

## Final summary metrics block

```
codebase-arch-review      {✅/⚠️/❌/—}  {N issues}
platform-capacity-review  {✅/⚠️/❌/—}  {N issues}
platform-security-review  {✅/⚠️/❌/—}  {N issues}
platform-ops-review       {✅/⚠️/❌/—}  {N issues}
platform-eng-review       {✅/⚠️/❌/—}  {N issues}
doc-review                {✅/⚠️/❌/—}  {N issues}
------------------------------------------------------------
ADRs written:          {N}
Runbook gaps:          {N}
Capacity blockers:     {N}
Accepted warnings:     {N}
Blocking issues:       {N}
Opportunities logged:  {N}  (non-blocking, in task file follow-ups)
```

## Round dashboard rows

```
codebase-arch-review      ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
platform-capacity-review  ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
platform-security-review  ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
platform-ops-review       ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
platform-eng-review       ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
doc-review                ✅/⚠️/❌/—/✂️   amended: Y/N   decisions: N
```

## Verdict labels

- **CLEAR TO APPLY** — all reviewers passed, no unresolved issues
- **CLEAR WITH WARNINGS** — all passed, user accepted risk on some issues; list accepted warnings
- **BLOCKED** — one or more reviewers failed; list blocking issues
- **UNSTABLE** — **`design:` amendments** were still happening in round 3; list what was still
  changing. Round 3 producing only `precision:` amendments is CLEAR (or CLEAR WITH WARNINGS), not
  UNSTABLE — a plan being polished is not a plan that failed to stabilise. Always state the ratio
  `N design / M precision` alongside the verdict.

## No-plan stop message

> "No platform plan found. Run `/draft-prd` first to produce a design document, then come back to `/board-review`."

## After-review: next steps

If verdict is CLEAR TO APPLY or CLEAR WITH WARNINGS:

```
✅ #NNN <title> — CLEAR TO APPLY

#NNN todo/<slug>.md
     ↓
/prd-workflow            ← track progress, keep TODO.md in sync
     ↓
/k8s-deploy          ← implement the changes
     ↓
/prd-workflow            ← close out, mark 🚀 Applied
```

If verdict is BLOCKED or UNSTABLE:
> "Resolve the issues above, then re-run `/board-review`."

## Commit messages

- CLEAR: `docs(platform): merge board review into #NNN [board-review]`
- BLOCKED: `docs(platform): merge blocked board review into #NNN [board-review]`
