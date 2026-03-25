---
name: platform-workflow
description: Institutional knowledge management for Kubernetes platform and infrastructure work. Tracks platform changes, operational health items, and infrastructure decisions as individual markdown files with a TODO.md priority index, linking planning artefacts to git branches, commits, and PRs. Use when asked to "track this platform change", "what platform work is outstanding?", "add this to the platform backlog", or "show me platform status".
---

# Platform Workflow

Maintain a `todo/` directory as a prioritised backlog where every platform change, operational health item, and infrastructure decision is a first-class document. The unit of concern here is **the cluster and its operational state**, not a single application codebase.

Items tracked here include: onboarding a new application to the cluster, infrastructure design changes, capacity upgrades, observability gaps, runbook coverage, security posture improvements, and support model changes.

## When to Activate

- Onboarding a new application or microservice to the cluster
- Planning infrastructure changes (namespace strategy, network policies, storage classes, etc.)
- Tracking operational health work (runbook gaps, monitoring coverage, alert tuning)
- Capacity planning and feasibility assessment
- After running `/platform-draft` or `/platform-board-review` — persist the output
- When picking up platform work started in a previous session
- When asked to "track this platform change", "what platform work is outstanding?", or "show me platform status"

---

## Responding to Status Queries

When asked for platform status (e.g. "show me platform status", "what platform work is outstanding?"):

1. Read `TODO.md` and output the full task table (or a summarised view if >10 rows)
2. Output the count summary line
3. State the next recommended action: *"The highest-priority open task is #002. Shall I continue it?"*

---

## The `todo/` Directory Structure

```
TODO.md                              ← priority index (source of truth)
todo/
├── 001-onboard-auth-service.md
├── 002-namespace-strategy.md
├── 003-observability-coverage-gap.md
├── 004-capacity-upgrade-q2.md
└── research/
    └── <slug>/                      ← research artefacts from /research-handbook
```

Task files are zero-padded to 3 digits (`001`–`999`). If you reach 999, extend to 4 digits consistently across all files and `TODO.md`.

### TODO.md — The Priority Index

```markdown
# Platform Tasks

| #   | Title                              | Priority   | Status          | Branch                      | PR   |
|-----|------------------------------------|------------|-----------------|-----------------------------|------|
| [001](todo/001-onboard-auth-service.md) | Onboard auth service | 🔴 P0 | 🚀 Applied | platform/onboard-auth | #12 |
| [002](todo/002-namespace-strategy.md)   | Namespace strategy   | 🟠 P1 | 🔄 In Progress | platform/namespace-strategy | — |
| [003](todo/003-observability-gap.md)    | Observability gap    | 🟡 P2 | ⬜ Open | — | — |

**Summary:** 1 applied · 1 in progress · 1 open

> Update this summary line whenever a task status changes.
> Count: Applied = 🚀 Applied; In Progress = 🔄 In Progress + 👀 PR Open + ✅ Merged; Open = all other non-❌ statuses.

## Archive

Tasks with status `🚀 Applied` or `❌ Won't Do` older than 90 days may be moved to an `## Archive` section at the bottom of `TODO.md`. Task files themselves remain in `todo/` permanently.

## Priority Key
- 🔴 P0 Critical — blocking, do immediately
- 🟠 P1 High — high value, do soon
- 🟡 P2 Medium — worth doing, schedule it
- 🔵 P3 Low — nice to have

## Status Key
- 📋 Preparing — task created, platform-draft not yet run
- ⬜ Open — platform-draft complete, awaiting /platform-board-review
- 🔎 In Review — platform-board-review board is actively running
- 🔍 Reviewed — plan approved by board, ready to implement
- 🔄 In Progress — active work
- 🏁 Implementation Done — complete, PR not yet raised
- 👀 PR Open — PR raised, awaiting review and merge
- ✅ Merged — merged to main, not yet applied to cluster
- 🚀 Applied — live in cluster
- ❌ Won't Do — cancelled, reason noted in task file
```

### Source of Truth

If the status in a task file disagrees with `TODO.md`, **the task file is authoritative**. Update `TODO.md` to match and note the discrepancy.

---

## Status Transitions

Legal status transitions — do not skip steps:

```
📋 Preparing  →  ⬜ Open           after /platform-draft completes
⬜ Open        →  🔎 In Review      when /platform-board-review starts
🔎 In Review   →  🔍 Reviewed       board verdict: CLEAR TO APPLY or CLEAR WITH WARNINGS
🔎 In Review   →  ⬜ Open           board verdict: BLOCKED or UNSTABLE (rework required)
🔍 Reviewed    →  🔄 In Progress    branch created, implementation begins
🔄 In Progress →  🏁 Done           all checklist items ticked, not yet PR'd
🏁 Done        →  👀 PR Open        PR raised
👀 PR Open     →  ✅ Merged         PR merged to main
✅ Merged      →  🚀 Applied        make apply succeeds and is verified
Any status    →  ❌ Won't Do       explicit cancellation decision
🚀 Applied    →  🔄 In Progress    reopen for follow-on work (do not reset; add new checklist items)
```

### Board Verdict → Status Mapping

| Board Verdict | Resulting Task Status |
|---|---|
| CLEAR TO APPLY | 🔍 Reviewed |
| CLEAR WITH WARNINGS | 🔍 Reviewed (warnings recorded in Board Review section) |
| BLOCKED | ⬜ Open (rework required — address findings before re-running board) |
| UNSTABLE | ⬜ Open (environment issue — resolve before re-running board) |

---

## Task File Format

```markdown
# PLATFORM #<N> — <Title>

> **Priority:** 🟡 P2 — Medium
> **Status:** 🔄 In Progress
> **Branch:** `platform/<slug>`
> **PR:** #<number> (or — if not yet raised)
> **Created:** YYYY-MM-DD
> **Applied:** — (fill in date when live in cluster)

---

## Problem Statement

What is wrong, missing, or at risk today on the platform?
Don't describe the solution here — describe the pain.

### What fails or is absent today

| Scenario | Current state | Desired state |
|----------|---------------|---------------|
| Auth service onboarded | No namespace, no RBAC | Fully isolated, monitored, runbook exists |

---

## Goals

1. Service runs in dedicated namespace with correct RBAC
2. Network policy restricts ingress/egress to known endpoints
3. Runbook covers all failure modes
4. Monitoring dashboard and alerts configured

## Non-Goals

What this task deliberately does not do.

---

## Platform Design

> *Populated by `/platform-draft`. Output is written into Architecture/Topology, Key Decisions, and Capacity Assessment subsections below. Overwrite placeholder text — do not append.*

### Architecture / Topology

```
Namespace: auth
  ├── Deployment: auth-api (2→10 replicas, HPA)
  ├── Service: ClusterIP :8080
  ├── NetworkPolicy: ingress=api-gateway, egress=postgres,vault
  ├── ServiceAccount: auth-api (Vault role: auth-api-prod)
  └── HPA: min:2 max:10 cpu:70%
```

### Key Decisions

Record every "we chose X over Y because Z".

### Capacity Assessment

| Resource | Current headroom | After this change | Remaining |
|----------|-----------------|-------------------|-----------|
| CPU | 40% | +2 cores | 35% |
| Memory | 55% | +4 GiB | 48% |

### Operational Readiness

- [ ] Runbook written
- [ ] Monitoring dashboard exists
- [ ] Alerts configured
- [ ] On-call rotation updated

---

## Implementation Plan

> *Populated by `/platform-draft`. Overwrite placeholder steps below.*

### Step 1 — Namespace and RBAC
### Step 2 — Helm chart / manifests
### Step 3 — Network policy
### Step 4 — Secrets / Vault integration
### Step 5 — Monitoring and alerts
### Step 6 — Runbook
### Step 7 — Smoke test in staging
### Step 8 — Promote to production

---

## Implementation Checklist

- [ ] Step 1 done
- [ ] ...
- [ ] Runbook reviewed by on-call engineer
- [ ] Smoke test passed in staging
- [ ] Applied to production

---

## Problems & Solutions

### Problem: <description>
**Encountered:** YYYY-MM-DD
**Root cause:** ...
**Solution:** ...
**Lesson:** ...

---

## Open Questions

1. **Should X or Y?** — Recommendation: X, because Z.

---

## Board Review

> *Populated by `/platform-board-review` after the board completes. Do not fill manually.*

**Verdict:** CLEAR TO APPLY | CLEAR WITH WARNINGS | BLOCKED | UNSTABLE
**Date:** YYYY-MM-DD
**Rounds:** N

| Reviewer | Result | Amended | Key findings |
|---|---|---|---|
| platform-arch-review | — | — | — |
| platform-capacity-review | — | — | — |
| platform-security-review | — | — | — |
| platform-ops-review | — | — | — |
| platform-eng-review | — | — | — |
| platform-doc-review | — | — | — |

**Accepted warnings:** none
**ADRs written:** 0

---

## Deployment Log

> *Appended after each `make apply`. Never overwrite — one entry per apply.*

### Applied YYYY-MM-DD — <description>

**Command:** `KUBECONFIG=~/.kube/contexts/ai-playground/prod make apply`
**Outcome:** ✅ Success | ⚠️ Partial | ❌ Failed
**Pod status:** (paste `kubectl get pods` snippet)
**Verification:** (what was checked — health, tool list, logs, end-to-end test)
**Issues encountered:** none | (description + resolution)
**Rollback taken:** no | yes — rolled back to <sha> because <reason>
```

---

## Workflow

### Bootstrap (fresh project with no TODO.md)

If `TODO.md` does not exist:
1. Create `TODO.md` with the header template and an empty task table
2. Create the `todo/` directory
3. Proceed to Starting a New Task

---

### Starting a New Task

1. Check `TODO.md` — what's the next available number?
2. Create `todo/<number>-<slug>.md` from the template above
3. Fill in at minimum: Problem Statement and Goals
4. Add a row to `TODO.md` — set priority, status `📋 Preparing`, branch `—`, PR `—`
5. Update the Summary line in `TODO.md`
6. Ask: "Shall I run `/platform-draft` now to flesh out the design?"
7. Once `/platform-draft` completes: set status to `⬜ Open` in both task file and `TODO.md`, then ask: "Shall I run `/platform-board-review`?"
8. After board review completes:
   - Map the verdict to a status using the Board Verdict → Status Mapping table
   - Update status in both task file and `TODO.md`
   - If CLEAR TO APPLY or CLEAR WITH WARNINGS: proceed to step 9
   - If BLOCKED or UNSTABLE: address findings, then re-run `/platform-board-review` from step 7
9. After CLEAR TO APPLY / CLEAR WITH WARNINGS:
   - Create branch: `git checkout -b platform/<slug>`
   - Set status to `🔄 In Progress` in both task file and `TODO.md`; fill in the Branch column
   - Update Summary line in `TODO.md`
   - Begin implementation

---

### Resuming a Task from a Previous Session

1. Read `TODO.md` — identify tasks with status `🔄 In Progress` or `🔍 Reviewed`
2. Read the full task file for the relevant item
3. Check the Implementation Checklist — find the first unticked item
4. Confirm the current branch with `git branch --show-current`; check out the task branch if needed
5. Resume from the first unticked checklist item — do not re-run completed steps

---

### During Work

- After hitting a problem — add a `### Problem:` entry to `## Problems & Solutions` immediately; if the problem was diagnosed with `/k8s-troubleshooting`, record the findings here
- Tick checklist items as they complete
- At end of session — update checklist and status in the task file **and mirror the status change in `TODO.md`**; update the Summary line

---

### Raising a PR

After all Implementation Checklist items are complete and the staging smoke test passes:

1. Push branch: `git push -u origin platform/<slug>`
2. Raise PR — title format: `platform: #<N> <title>`
3. PR body should link to the task file: `See todo/<N>-<slug>.md`
4. Set status to `👀 PR Open` in task file and `TODO.md`; fill in the PR column
5. Update Summary line in `TODO.md`
6. After merge: set status to `✅ Merged`; note the merge commit SHA in the task file

---

### Deploying — record the outcome in the task file

After every `make apply` (or equivalent), **immediately update the task file** with what happened. Do not wait until the task is fully closed. Append a new entry to `## Deployment Log` — never overwrite; each apply gets its own entry:

```markdown
### Applied YYYY-MM-DD — <short description>

**Command:** `KUBECONFIG=~/.kube/contexts/ai-playground/prod make apply`
**Outcome:** ✅ Success | ⚠️ Partial | ❌ Failed
**Pod status:** `kubectl get pods` snippet or summary
**Verification:** what was checked post-apply (health endpoint, tool list, logs, etc.)
**Issues encountered:** none | description of any problem and how it was resolved
**Rollback taken:** no | yes — rolled back to <sha> because <reason>
```

If the apply **failed or was partial**, also:
- Document the exact error
- Note what state the cluster is left in
- Add a checklist item for the fix needed before re-applying

---

### Closing a Task

When the change is fully applied and verified in the cluster:

1. Add a final `## Deployment Log` entry with outcome and verification steps
2. Set `**Status:**` to `🚀 Applied`, set `**Applied:**` to today's date
3. Update `TODO.md` — flip the status column to `🚀 Applied`, update Summary line
4. Tick off all remaining `## Implementation Checklist` items
5. Commit: `git commit -m "deploy(platform): #<n> <title> applied"`

Task files are **never deleted** — they are permanent institutional memory.

---

### P0 Emergency (bypassing board review)

For critical outage response where waiting for `/platform-board-review` is not viable:

1. Create the task file and `TODO.md` row as normal — status `📋 Preparing`
2. Create branch: `platform/hotfix-<slug>`
3. Set status to `🔄 In Progress` immediately
4. Implement and apply
5. Run `/platform-board-review` **retrospectively** after the cluster is stable
6. Record the rationale for bypassing in the task file's `## Key Decisions` section

---

## Branch Naming

| Task type | Branch prefix | Example |
|-----------|--------------|---------|
| New onboarding | `platform/` | `platform/onboard-auth-service` |
| Infrastructure change | `platform/` | `platform/namespace-strategy` |
| Operational health | `platform/` | `platform/observability-gap` |
| P0 emergency hotfix | `platform/hotfix-` | `platform/hotfix-ingress-down` |

---

## Integration with Other Skills

| Skill | How it integrates |
|-------|------------------|
| `/platform-draft` | Run first; output written into `## Platform Design` (Architecture, Key Decisions, Capacity Assessment) and `## Implementation Plan`. Overwrite placeholder text — do not append. |
| `/platform-board-review` | Gate the design before applying to cluster; board verdict mapped to task status via the Board Verdict → Status Mapping table |
| `/k8s-deploy` | How-to skill invoked during implementation; **write deployment outcome back to task file `## Deployment Log` after every apply** |
| `/k8s-troubleshooting` | Invoked when an incident needs diagnosis; record findings as a `### Problem:` entry in `## Problems & Solutions` |
| `/research-handbook` | Research findings saved to `todo/research/<slug>/`; link from the task file's `## Open Questions` or `## Platform Design` section |
| `/codebase-scout` | May surface platform-level tech debt — log it here as a new task |
