---
name: draft-prd
description: Structured planning before writing code or touching the cluster — user interview, problem framing, requirements or capacity assessment, system/infrastructure design, ADRs, trade-offs, delivery sequencing, and definition of done. Works for both software features (codebase mode) and Kubernetes/infrastructure changes (platform mode). Supports a Grill Mode for relentless adversarial discovery. Supersedes codebase-draft-prd and platform-draft-prd.
triggers:
  - "plan #\\d+"
  - "plan \\d+"
  - "plan todo #?\\d+"
  - "/draft-prd"
  - "write a prd"
  - "write-a-prd"
  - "create a prd"
  - "product requirements document"
  - "platform \\d+"
  - "platform #\\d+"
  - "grill me"
  - "grill this"
  - "/grill-me"
  - "stress-test this plan"
  - "interview me about"
---

# Draft PRD

A structured approach to planning before touching code or the cluster. Produces a clear spec, design decisions, ADRs, and a delivery sequence the board can gate against.

## Mode detection

**At the start of every run, detect the mode:**

| Signal | Mode |
|---|---|
| `[INFRA]`, "cluster", "k8s", "Helm", "namespace", "workload", "vcluster", "onboard", `platform/` in branch/path, or explicit `platform <number>` | **Platform** |
| Everything else — software feature, API, refactor, bug fix | **Codebase** |

State the detected mode: `> Mode: Codebase` or `> Mode: Platform`.

---

## Precision discipline — applies to every phase

**Load `references/precision-rules.md` before Phase 1 and keep it in force throughout.** It is not a
final polish step; the rules are cheap while writing and expensive to retrofit.

The nine rules in one line each:

1. **Never write a value you could derive** — state the command, endpoint, or accessor instead.
2. **State each rule normatively in exactly one place** — name it, reference the name elsewhere.
3. **Requirements say *where*, not just *what*** — insertion point, and every behaviour of anything
   being replaced.
4. **Slice placement follows a stated invariant** — not case-by-case judgement.
5. **Test specs are checked against the fixtures they would run on** — by running them.
6. **Claims are scoped to the strength that actually holds.**
7. **Rejected alternatives carry the fact that kills them.**
8. **Byte-level content is written as `\uXXXX` escapes**, never as glyphs.
9. **Length is a defect generator** — more copies, more drift, more amendments.

Why this is in the authoring skill rather than the review skill: a board review measures whether a
plan agrees with itself and with the repo. In one three-round review, ~48 of 53 final-round
amendments were the plan disagreeing with itself — self-inflicted, and each one displaced budget the
reviewers could have spent on real design defects. **Fix these as you go. Do not leave them for the
board.**

---

## When to Trigger

- `plan <number>` / `plan #<number>` / `platform <number>` — plan a specific task
- `/draft-prd` — explicit invocation
- "plan this out", "write a PRD", "create a PRD", "product requirements document"
- Before onboarding any new application to the cluster
- Before any significant infrastructure change
- "grill me", "grill this", `/grill-me`, "stress-test this plan", "interview me about" — **Grill Mode** (see below)

When a task number is given, glob `todo/<number>-*.md` to find the task file before starting.

---

## Workflow position

**Codebase:**
```
/draft-prd  ← YOU ARE HERE
      │
      ▼
/board-review → implementation → /codebase-closeout → /prod-release
```

**Platform:**
```
/draft-prd  ← YOU ARE HERE
      │
      ▼
/board-review → implementation → /prd-workflow (close out, mark 🚀 Applied)
```

---

## When to Use

- Planning a significant new feature or system change
- Making an architectural decision (database, service split, API design)
- Onboarding a new service to the cluster
- Capacity planning and infrastructure design
- Creating an RFC or design document for team review

---

## Pre-flight: Check for an existing task file

1. **If a task number was given**: glob `todo/<number>-*.md` and read it.
2. **If working from current branch** (codebase): check `TODO.md` for a matching `🔄 In Progress` or `⬜ Open` item and read its task file.
3. **If no task file exists**: create one via `/prd-workflow` before continuing.

If a task file already exists:
- Use its **Problem Statement** as Phase 1 input — do not re-derive from scratch.
- Use its **Goals** as the starting point for Phase 2.
- Check whether a **Design** section is already partially filled — start from there.
- Phase 0 research can usually be skipped unless the Design is empty *and* the technology is unfamiliar.

All output should be written back into the task file — not into a separate document.

---

## Pre-flight: Interview Mode

Two modes. Detect from the trigger phrase:

| Trigger | Mode |
|---|---|
| "grill me", "grill this", `/grill-me`, "stress-test this plan", "interview me about" | **Grill Mode** — relentless, adversarial, every branch |
| All other triggers | **Standard Mode** — targeted, efficient, skip what's obvious |

---

### Standard Mode

Ask for a **brief initial description** of the problem. Keep this short — resolve details through exploration and follow-up.

**1. Explore first.** Read the codebase or cluster state, existing task files, tests, docs, ADRs, and anything referenced in the description. For platform work: check Helm charts, namespace manifests, runbooks, and prior board review decisions. Answer as many questions as you can without involving the user.

**2. Ask about what you cannot determine.** Targeted questions only — preference/priority decisions, trade-offs with no correct answer, conflicting signals, unknowns only the user can resolve. Ask one thread at a time.

**3. Surface conflicts explicitly.** If exploration reveals something that conflicts with the stated approach, raise it directly.

**4. Iterate until shared understanding.** Keep exploring and asking until you can restate the full plan and the user confirms it is correct. Do not proceed to Phase 1 until this point is reached.

Load `references/discovery-questions.md` and ask each question in order, waiting for answers before continuing. Do not skip this even when a task file exists — the task file captures *what*, not *why*.

---

### Grill Mode

Interview the user relentlessly about every aspect of the plan until you reach shared understanding. Walk down each branch of the decision tree, resolving dependencies one at a time. **Ask one question at a time. Wait for the answer before continuing.**

**Before asking anything:** explore the codebase or cluster state, read the task file and any existing design doc, and build a map of the decision tree — what are the load-bearing decisions, and what depends on each one? If a question can be answered by exploration, answer it yourself and confirm the finding rather than asking.

**Tell the user the scope upfront:**
> "I'll work through [N areas]: [list]. Starting with the most load-bearing decision."

**For each open question, in dependency order:**
1. State the question clearly — name the specific decision or assumption being tested.
2. Give your recommended answer based on what you've read, and why in one sentence. Make it a real recommendation, not a hedge.
3. Wait for the user's response.
4. If they confirm: lock it in, note it, move to the next dependent question.
5. If they correct or refine: update your model, check whether it invalidates any already-locked decisions, then continue.
6. If they're unsure: offer a concrete trade-off (option A vs B, one sentence each), then ask them to choose.

**Conflict rule:** when an answer contradicts a prior locked decision, stop and name it:
> "That conflicts with what we decided about X — [what was decided]. Which takes priority, or do we need to revise X?"
Resolve before continuing.

**Question quality:**
- One question = one decision. Never bundle two decisions.
- Concrete over abstract: "Postgres or Redis for session state?" not "what's your persistence strategy?"
- Load-bearing decisions first — ask about what other decisions depend on before those dependents.
- If a section has no open questions, say so and move on.

**On completion,** produce a locked-decisions summary before proceeding to the planning phases:

```
## Grill summary

### Locked decisions
- [decision]: [what was decided]

### Revised from initial plan
- [what changed and why]

### Still open
- [anything explicitly deferred with reason]
```

Ask whether to write the locked decisions into the task file's Design section now, or proceed directly to the planning phases with them as context.

---

## Phase 0 — Research

Runs in parallel with the pre-flight interview. Every lookup is an opportunity to answer a question before asking the user.

**What to explore:**
- Codebase: relevant source files, tests, existing similar features, library docs
- Platform: Helm charts, namespace manifests, operator docs, upstream changelogs
- Prior ADRs, design docs, or task files that touch this area
- Whether something already exists in the codebase/cluster that meets this need

**When to run `/research` or `/search-first`:**
- The technology, library, operator, or pattern is unfamiliar
- There are competing approaches and trade-offs are unclear
- A security, compliance, or regulatory question must be resolved before design

Save findings to `todo/research/<slug>/` and link from the task file's Design section.

---

## Phase 1 — Problem framing

**Questions to answer:**
1. What problem does this solve? (not "implement X" — the underlying need)
2. What does success look like? (measurable outcome)
3. What is explicitly out of scope?
4. What are the constraints? (timeline, existing tech/topology, compliance, team size)
5. Who are the stakeholders and what do they care about?

**Output:**
```
Problem: [what is broken, missing, or at risk today]
Goal: [what we want to be true after this ships/applies]
Success metric: [how we'll know it worked]
Out of scope: [what we are NOT doing]
Constraints: [time, tech/topology, compliance, team]
```

---

## Phase 1.5 — User Stories [Codebase only]

Write a long, numbered list covering all actors and all aspects of the feature:

```
As a <actor>, I want <feature>, so that <benefit>
```

Be **extremely extensive** — cover happy paths, error paths, edge cases, admin flows, and every actor. Check this list with the user before proceeding.

---

## Phase 2 — Requirements [Codebase] / Feasibility & Capacity [Platform]

### [Codebase] Requirements

**Functional requirements** — what the system must do, and **where**:
```
FR-1: [requirement]
      Where: [function/module, and position relative to existing gates —
              "before the cold-store 503 check", not just "in _authorize"]
```

A requirement that names *what* but not *where* gets implemented in the wrong place, or read three
different ways by three reviewers. If the change **replaces** an existing function, enumerate every
behaviour of the old one and state explicitly whether the new one keeps it — a dropped behaviour
nobody listed is how a silent allow→deny regression ships (precision rule 3).

**Non-functional requirements** — how well it must do it:
```
NFR-1: [requirement]
```

Any NFR that defines a **set** (error reasons, states, labels, metric values) gets a `Produced by`
column naming the code path that emits each member. A set whose members come from different paths is
two sets wearing one name, and its count will be wrong.

**Acceptance criteria** — definition of done (testable):
```
AC-1: Given [context], when [action], then [outcome]
      Verified by: [test name + fixture, or the exact command that checks it]
```

Every AC that names a test must name its **fixture** and the guards that fixture must pass. Then run
the tests you claim will change and paste the real output — the list is an executable fact, not a
prediction (precision rule 5).

See `references/prd-examples.md` for FR/NFR/AC examples.

**Measured facts block.** If the plan reasons over any measured quantity (a count, a size, a
utilisation), put every one of them in a single dated block with the exact command that produced
each, and state that no other section may re-quote them:

```
## Measured facts — measured YYYY-MM-DD, re-derive before implementing

| Fact | Value | How it was measured |
|---|---|---|
| <name> | <value> | <exact command / endpoint> |

Quantities that are easy to conflate get one row each, named distinctly.
No other section restates these values; they reference this block by name.
```

### [Platform] Feasibility & Capacity

Answer: **can the cluster handle this?**

| Resource | Current utilisation | Change adds | Headroom after | Safe? |
|----------|-------------------|-------------|----------------|-------|
| CPU | X% | +N cores | Y% | ✅/⚠️/❌ |
| Memory | X% | +N GiB | Y% | ✅/⚠️/❌ |
| PVCs / storage | N in use | +N | N remaining | ✅/⚠️/❌ |
| LoadBalancer IPs | N | +N | N remaining | ✅/⚠️/❌ |
| Namespace count | N | +1 | — | ✅/⚠️/❌ |

**Safety thresholds:** Flag any resource above 75% after the change. Flag above 90% as blocking.

Beyond raw compute — does the change also require: new StorageClasses, Vault roles, OIDC config, observability capacity, DNS records, TLS certificates?

---

## Phase 3 — Architecture Decision Records (ADRs)

For each significant decision, write a short ADR using the format from `~/.claude/skills/codebase-arch-review/references/adr-template.md`.

**Every ADR records the rejected alternatives and, for each, the specific fact that kills it** — the
import cycle, the unreachable branch, the measurement. A decision recorded without its rejected
alternatives gets re-litigated: reviewers independently propose the options you already closed, and
you spend a round re-explaining rather than reviewing (precision rule 7).

See `references/prd-examples.md` for ADR examples in both codebase and platform modes.

---

## Phase 3.5 — Module Design [Codebase] / Migration Path [Platform]

### [Codebase] Module Design

Sketch the major modules to **build or modify**. Look for deep modules — significant functionality behind a simple, rarely-changing interface.

For each module: name, responsibility, interface (what in / what out), new or modification, testable in isolation?

See `references/prd-examples.md` for the module design format.

Check this list with the user before continuing. Ask which modules they want tests written for.

If this change requires data migration or schema changes, load `references/migration-checklist.md` and select the appropriate pattern (expand-contract / strangler fig / hard cutover).

### [Platform] Migration & Transition Path

**Only required when the plan includes:** topology changes, operator/CRD upgrades, storage class migration, DNS/endpoint changes affecting live traffic, or a Kubernetes version upgrade.

**If none apply:** note "No migration required — additive change" and skip.

Load `references/migration-template.md` and fill in each applicable field.

---

## Phase 4 — System / Infrastructure Design

### [Codebase] System Design

Diagram the data flow and component interactions. Include: data model changes (SQL), API contract (endpoints, request/response shapes), and any background processing paths.

See `references/prd-examples.md` for system design diagram and API contract format.

### [Platform] Infrastructure Design

Diagram the namespace topology and component relationships: Deployments, Services, NetworkPolicies, ServiceAccounts, HPA settings, Ingress rules.

Include Helm/manifest changes: new charts, new values files, modified manifests.

See `references/prd-examples.md` for infrastructure design diagram format.

---

## Phase 5 — Operational Readiness [Platform only]

| Readiness item | Exists today | Action required |
|----------------|-------------|-----------------|
| Runbook | ❌ | Write |
| Monitoring dashboard | ❌ | Create |
| Latency/error rate alerts | ❌ | Add Prometheus rules |
| Pod restart alert | ❌ | Add alert |
| On-call rotation updated | ❌ | Add to rotation doc |
| Capacity baseline recorded | ❌ | Document in task file |
| Backup policy | ✅ | No action |

### Smoke tests, integration tests, end-to-end tests [Platform only]

"It deployed" is not the same as "it works." Scripted tests are mandatory — manual curl-and-eyeball is not a gate.

Load `references/smoke-test-template.md` and fill in each section. Every production change requires a pre-apply baseline entry.

---

## Phase 6 — Security Posture [Platform only]

| Security concern | Action |
|-----------------|--------|
| RBAC | Define Role + RoleBinding, namespace-scoped |
| Network policy | Write NetworkPolicy (default-deny + explicit allow) |
| Secrets injection | Configure Vault role + policy |
| Image scanning | Verify CI pipeline scans on push |
| Pod security | Add securityContext (nonRoot, readOnly, drop ALL) |
| mTLS | Verify PeerAuthentication in namespace |

---

## Phase 7 — Trade-off Analysis

For each significant choice, explicitly state what you're giving up.

See `references/prd-examples.md` for trade-off format.

---

## Phase 8 — Delivery Sequencing

Break into shippable slices — each must be independently deployable and useful on its own.

**State the placement invariant before listing any slice**, then check every row against it:

> **Placement invariant:** every artefact — requirement, acceptance criterion, doc edit, test —
> lands in the slice where its statement first becomes true. Not the slice that motivated it, and
> not the slice where it was noticed.

Write the invariant into the plan itself, not just apply it silently. With the rule stated, a
misplaced row is self-evident to any reader; without it, each misplacement has to be independently
rediscovered — the same one gets caught by three different reviewers across two rounds, which reads
as three findings and burns three reviewers' budget.

**Then state build-order prerequisites explicitly.** "Everything else may ship in any order" is
almost always false: anything consuming a new module depends on the slice that creates it. Name the
edges, or say there are none and be right.

See `references/prd-examples.md` for slice format examples (codebase and platform).

---

## Phase 9 — Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|

See `references/prd-examples.md` for risk register examples.

---

## Phase 10 — Definition of Done

### [Codebase]

- [ ] All acceptance criteria pass in staging
- [ ] Unit tests cover happy path + all error cases
- [ ] Integration/E2E test covers the full user flow
- [ ] Load test passes NFR targets (latency, concurrency)
- [ ] Security review completed (auth, input validation, no PII leaks)
- [ ] Database migration tested against production-sized dataset
- [ ] Rollback plan documented and tested
- [ ] Monitoring: alerts configured for error rate and latency
- [ ] Runbook updated for on-call
- [ ] API documentation updated
- [ ] Feature flag in place for gradual rollout

### [Platform]

- [ ] All acceptance criteria pass in staging
- [ ] Capacity headroom verified post-deploy (no resource above 80%)
- [ ] NetworkPolicy tested — permitted traffic works, denied traffic blocked
- [ ] **Pre-change baseline recorded** — smoke test run before any apply
- [ ] **Smoke tests pass** after each slice in staging (scripted, not manual)
- [ ] **Integration tests pass** — cross-service and cross-namespace interactions verified
- [ ] **End-to-end tests pass** — full system flow exercised, not just health checks
- [ ] **Negative-path tests pass** — blocked traffic/access confirmed blocked
- [ ] **Rollback smoke test defined and tested**
- [ ] Runbook written and reviewed by at least one on-call engineer
- [ ] Monitoring dashboard live and correct
- [ ] Alerts configured and tested
- [ ] On-call rotation updated if applicable
- [ ] Security review passed
- [ ] ADRs written for significant decisions

---

## Phase 11 — Precision sweep [mandatory, both modes]

**Run this before handing off to `/board-review`. It is not optional and it is not a formality.**

Open `references/precision-rules.md`, work the self-check at the bottom, and **fix what it finds
now**. This is the whole point: a defect fixed here costs one edit; the same defect fixed via the
board costs a reviewer's budget, a round of amendments, a re-review of the amended text, and often a
second defect introduced by the amendment.

The sweep is mechanical — every line is checkable without judgement:

- **Re-verify every `file:line` citation against the file as it is now**, and replace with a symbol
  reference wherever the exact line does not matter. Citations written during Phase 0 have already
  drifted by Phase 10.
- **Grep for every number in the plan.** Each is either in the `## Measured facts` block with its
  command, or derived at implementation time. Any number appearing in two places is a defect even if
  both copies currently agree.
- **Grep for each normative rule's keywords** to find restatements. Where prose and a table both
  state a rule, delete one or mark which is normative.
- **Run the tests the plan claims will change**, and correct the list from real output.
- **Grep for universal quantifiers** — "always", "never", "every", "only", "any order", "strictly",
  "monotonically" — and scope or delete each one.
- **Check the line count.** Over ~400 lines, cut by referencing the repo instead of quoting it.

Then report to the user in one line:

> "Precision sweep: fixed N items (M stale citations, K duplicated values, J unscoped claims,
> …). Plan is at L lines."

If it fixed nothing, say that explicitly — it is a real signal, not an empty result.

---

## Status update on completion

When `/draft-prd` finishes writing the plan into the task file, **immediately**:

1. Set `**Status:**` in the task file to `⬜ Open`
2. Update the matching row in `TODO.md` to `⬜ Open`
3. Do **not** set status to `🔍 Reviewed` — that is reserved for after `/board-review` passes.

Then prompt:

> "Plan written and status set to ⬜ Open. Ready to run `/board-review` to gate this through the board before [implementation / applying to the cluster]?"

---

## Output template

```
# [Feature / Platform Change]: [Name]

## Problem & Goal
## [User Stories (codebase) | Capacity Assessment (platform)]
## Requirements (FR + NFR + AC) [codebase] | Feasibility (platform)
## Module Design (codebase) | Migration Path (platform)
## System Design (codebase) | Infrastructure Design (platform)
## ADRs
## Operational Readiness + Security Posture [platform]
## Trade-offs
## Delivery Slices
## Risk Register
## Definition of Done
## Measured facts (dated, with the command for each)
```

Keep it concise — the goal is alignment, not documentation theatre.
A good plan is one page; a great plan is two pages with diagrams.

**This is a constraint, not an aspiration.** Length is not rigour — it is drift surface. Every
restated fact, duplicated rule, and quoted code block is a copy that can disagree with the original,
and disagreeing-with-itself is exactly the property the board tests. A 2,850-line plan for a P2 fix
generated 53 review amendments, of which roughly five were real design findings. At ~400 lines,
stop and cut: reference the repo instead of quoting it, delete every restatement, and trust the
reader to follow a symbol reference.
