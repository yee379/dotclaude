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

Planning before touching code or the cluster. Produces a spec, design decisions, ADRs, and a
delivery sequence the board can gate against.

Use for: a significant feature or system change, an architectural decision (database, service
split, API design), onboarding a service to the cluster, capacity planning, or an RFC for team
review. When a task number is given, glob `todo/<number>-*.md` for the task file first.

## Mode detection

| Signal | Mode |
|---|---|
| `[INFRA]`, "cluster", "k8s", "Helm", "namespace", "workload", "vcluster", "onboard", `platform/` in branch/path, explicit `platform <number>` | **Platform** |
| Everything else — software feature, API, refactor, bug fix | **Codebase** |

State it: `> Mode: Codebase` or `> Mode: Platform`.

**Workflow position** — `/draft-prd` → `/board-review` → implementation → `/closeout-prd` →
`/prod-release`. In platform mode the tail is `/prd-workflow` (close out, mark 🚀 Applied).

---

## Precision discipline — applies to every phase

**Load `references/precision-rules.md` before Phase 1 and keep it in force throughout.** These
rules are cheap while writing and expensive to retrofit.

1. **Never write a value you could derive** — state the command, endpoint, or accessor instead.
   Number *words* count; derive reference targets rather than composing plausible ones.
2. **State each rule normatively in exactly one place** — name it, reference the name elsewhere.
3. **Requirements say *where*, not just *what*** — insertion point (including clause order), every
   behaviour of anything being replaced, and every *instance* of a mechanism being replaced.
   Finish the audit; do not defer it into the plan.
4. **Slice placement follows a stated invariant** — not case-by-case judgement.
5. **Run anything you can run** — the tests you claim will flip, the mechanism you recommend, and
   any claim made while presenting options to the user.
6. **Claims are scoped to the strength that actually holds.**
7. **Rejected alternatives carry the fact that kills them.**
8. **Byte-level content is written as `\uXXXX` escapes**, never as glyphs.
9. **Length is a defect generator** — more copies, more drift, more amendments.

Precision rules keep the plan from contradicting itself. For the prose itself — tense, marking a
fact as verified, derived, or assumed, and choosing a table over bullets — use
`~/.claude/skills/agentic-standards/references/technical-prose.md`.

This lives in the authoring skill because a board review measures whether a plan agrees with
itself. In one three-round review, ~48 of 53 final-round amendments were the plan disagreeing with
itself — each one displacing budget the reviewers could have spent on real design defects.
**Fix these as you go.**

---

## Pre-flight

**Existing task file:**
1. Task number given — glob `todo/<number>-*.md` and read it.
2. Working from a branch (codebase) — check `TODO.md` for a matching `🔄 In Progress` / `⬜ Open`
   item and read its task file.
3. No task file — create one via `/prd-workflow` first.

If one exists: use its **Problem Statement** as Phase 1 input rather than re-deriving, its
**Goals** as the Phase 2 starting point, and any partial **Design** section as a base. All output
goes back into the task file, not a separate document.

Run Phase 0 anyway if Design is empty, *or* the technology is unfamiliar, *or* the task file is
older than the code it touches. Any one of those is enough. A task file records what someone
concluded earlier, which is not the same as what is true now, and the cheap lookups are the ones
that catch a feature that already exists. Skip Phase 0 only when the Design section is populated
and the technology is familiar.

**Interview mode** — from the trigger phrase:

| Trigger | Mode |
|---|---|
| "grill me", "grill this", `/grill-me`, "stress-test this plan", "interview me about" | **Grill** — relentless, adversarial, every branch |
| All others | **Standard** — targeted, efficient, skip what's obvious |

### Standard Mode

Ask for a **brief** initial description; resolve details through exploration and follow-up.

1. **Explore first.** Codebase or cluster state, task files, tests, docs, ADRs, anything the
   description references. Platform: Helm charts, namespace manifests, runbooks, prior board
   decisions. Answer everything you can without the user.
2. **Ask only what you cannot determine** — preference and priority calls, trade-offs with no
   correct answer, conflicting signals. One thread at a time.
3. **Surface conflicts explicitly**, including when the user's own answer conflicts with their own
   earlier example. If an option you offer would refuse, invert, or exclude a case they have
   already described wanting, say so *before* writing it into the plan. **An answer that
   contradicts the asker's own worked example is a conflict to resolve, not a caveat to record.**
4. **Iterate until shared understanding** — until you can restate the full plan and the user
   confirms it. Do not proceed to Phase 1 before that.

Load `references/discovery-questions.md` and ask each in order, waiting for answers. Do not skip
it when a task file exists — the task file captures *what*, not *why*.

### Grill Mode

Interview relentlessly down every branch of the decision tree, resolving dependencies one at a
time. **One question at a time. Wait for the answer.**

**Before asking anything:** explore the codebase or cluster, read the task file and any design
doc, and map the decision tree — which decisions are load-bearing, and what depends on each. If
exploration can answer a question, answer it and confirm the finding instead of asking.

Tell the user the scope upfront: *"I'll work through [N areas]: [list]. Starting with the most
load-bearing decision."*

For each open question, in dependency order:
1. State the question — name the specific decision or assumption being tested.
2. Give your recommended answer and why, in one sentence. A real recommendation, not a hedge.
3. Wait.
4. Confirmed → lock it in, note it, move to the next dependent question.
5. Corrected → update your model, check whether it invalidates a locked decision, continue.
6. Unsure → offer a concrete trade-off (A vs B, one sentence each) and ask them to choose.

**Conflict rule:** when an answer contradicts a locked decision, stop and name it — *"That
conflicts with what we decided about X — [what was decided]. Which takes priority?"* Resolve
before continuing.

**Question quality:** one question = one decision, never bundled. Concrete over abstract
("Postgres or Redis for session state?" not "what's your persistence strategy?"). Load-bearing
decisions before their dependents. If a section has no open questions, say so and move on.

On completion, produce a locked-decisions summary:

```
## Grill summary
### Locked decisions
- [decision]: [what was decided]
### Revised from initial plan
- [what changed and why]
### Still open
- [anything explicitly deferred with reason]
```

Then ask whether to write it into the task file's Design section now or carry it as context.

---

## Phase 0 — Research

Runs in parallel with the pre-flight interview. Every lookup is a chance to answer a question
before asking the user.

Explore: relevant source and tests, existing similar features, library docs; platform — Helm
charts, namespace manifests, operator docs, upstream changelogs; prior ADRs and task files
touching this area; whether something already exists that meets the need.

Run `/research` or `/search-first` when the technology or pattern is unfamiliar, trade-offs
between competing approaches are unclear, or a security/compliance question must be resolved
before design. Save findings to `todo/research/<slug>/` and link from the Design section.

---

## Phase 1 — Problem framing

Answer: what problem does this solve (the underlying need, not "implement X")? What does success
look like, measurably? What is explicitly out of scope? What are the constraints (timeline,
existing tech/topology, compliance, team size)? Who are the stakeholders and what do they care
about?

```
Problem: [what is broken, missing, or at risk today]
Goal: [what we want to be true after this ships/applies]
Success metric: [how we'll know it worked]
Out of scope: [what we are NOT doing]
Constraints: [time, tech/topology, compliance, team]
```

---

## Phase 1.5 — User Stories [Codebase only]

A long, numbered list covering all actors and all aspects: `As a <actor>, I want <feature>, so
that <benefit>`. Be **extremely extensive** — happy paths, error paths, edge cases, admin flows,
every actor. Check the list with the user before proceeding.

---

## Phase 2 — Requirements [Codebase] / Feasibility & Capacity [Platform]

### [Codebase] Requirements

**Functional requirements** — what the system must do, and **where**:
```
FR-1: [requirement]
      Where: [function/module, and position relative to existing gates —
              "before the cold-store 503 check", not just "in _authorize"]
```

A requirement naming *what* but not *where* gets implemented in the wrong place or read three
ways by three reviewers. If the change **replaces** an existing function, enumerate every
behaviour of the old one and state whether the new one keeps it — a dropped behaviour nobody
listed is how a silent allow→deny regression ships (rule 3).

**Non-functional requirements** — how well: `NFR-1: [requirement]`

Any NFR defining a **set** (error reasons, states, labels, metric values) gets a `Produced by`
column naming the code path emitting each member. A set whose members come from different paths
is two sets wearing one name, and its count will be wrong.

**Acceptance criteria** — testable:
```
AC-1: Given [context], when [action], then [outcome]
      Verified by: [test name + fixture, or the exact command that checks it]
```

Every AC naming a test names its **fixture** and the guards that fixture must pass. Then run the
tests you claim will change and paste the real output — an executable fact, not a prediction
(rule 5).

**Measured facts block.** If the plan reasons over any measured quantity, put every one in a
single dated block with the exact command that produced it:

```
## Measured facts — measured YYYY-MM-DD, re-derive before implementing

| Fact | Value | How it was measured |
|---|---|---|
| <name> | <value> | <exact command / endpoint> |

Quantities that are easy to conflate get one row each, named distinctly.
No other section restates these values; they reference this block by name.
```

FR/NFR/AC examples: `references/prd-examples.md`.

### [Platform] Feasibility & Capacity

Answer: **can the cluster handle this?**

| Resource | Current utilisation | Change adds | Headroom after | Safe? |
|----------|-------------------|-------------|----------------|-------|
| CPU | X% | +N cores | Y% | ✅/⚠️/❌ |
| Memory | X% | +N GiB | Y% | ✅/⚠️/❌ |
| PVCs / storage | N in use | +N | N remaining | ✅/⚠️/❌ |
| LoadBalancer IPs | N | +N | N remaining | ✅/⚠️/❌ |
| Namespace count | N | +1 | — | ✅/⚠️/❌ |

**Thresholds:** flag any resource above 75% after the change; above 90% is blocking.

Beyond raw compute — does it also need new StorageClasses, Vault roles, OIDC config,
observability capacity, DNS records, TLS certificates?

---

## Phase 2.5 — Feasibility checks [mandatory, both modes]

Run before Phase 3. A dependency that doesn't resolve, a symbol that doesn't exist, a cluster
resource that isn't there, or a schema assumption that doesn't hold is cheap to check here and
costs a reviewer's Round 1 judgement otherwise.

Work `references/feasibility-checks.md` for the detected mode. Fix what fails, or record it
explicitly as an accepted unverified assumption — do not carry a silent ❌ into Phase 3.

Distinct from Phase 11: precision checks whether the plan agrees with **itself**; this checks
whether it agrees with **reality**. Run both.

Report in one line: *"Feasibility checks: N of M passed live (K dependency, J resource, …). L
unresolved, recorded as assumptions."* If everything passed, say so — that is a real signal.

---

## Phase 3 — Architecture Decision Records

For each significant decision, a short ADR using
`~/.claude/skills/codebase-arch-review/references/adr-template.md`.

**Every ADR records the rejected alternatives and, for each, the specific fact that kills it** —
the import cycle, the unreachable branch, the measurement. A decision recorded without them gets
re-litigated: reviewers independently propose options you already closed (rule 7).

**Do not allocate from a shared monotonic sequence while another branch or agent holds it** — ADR
numbers, migration numbers, task ids. Record *"next free is N, confirm against the merged tree"*
and state the derivation (`ls docs/adr/`), not the number. Do not assume concurrent work consumes
exactly one.

Examples: `references/prd-examples.md`.

---

## Phase 3.5 — Module Design [Codebase] / Migration Path [Platform]

### [Codebase] Module Design

Sketch the modules to build or modify. Look for deep modules — significant functionality behind a
simple, rarely-changing interface. Per module: name, responsibility, interface (in/out), new or
modification, testable in isolation? Format: `references/prd-examples.md`.

Check the list with the user, and ask which modules they want tests written for.

For data migration or schema changes, load `references/migration-checklist.md` and select the
pattern (expand-contract / strangler fig / hard cutover).

### [Platform] Migration & Transition Path

**Required only for:** topology changes, operator/CRD upgrades, storage class migration,
DNS/endpoint changes affecting live traffic, or a Kubernetes version upgrade. **If none apply:**
note "No migration required — additive change" and skip.

Load `references/migration-template.md` and fill in each applicable field.

---

## Phase 4 — System / Infrastructure Design

**[Codebase]** Diagram data flow and component interactions. Include data model changes (SQL),
API contract (endpoints, request/response shapes), and background processing paths.

**[Platform]** Diagram namespace topology and component relationships — Deployments, Services,
NetworkPolicies, ServiceAccounts, HPA settings, Ingress rules. Include Helm/manifest changes:
new charts, new values files, modified manifests.

Formats: `references/prd-examples.md`.

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

**Smoke, integration, and end-to-end tests.** "It deployed" is not "it works." Scripted tests are
mandatory — manual curl-and-eyeball is not a gate. Load `references/smoke-test-template.md` and
fill in each section. Every production change requires a pre-apply baseline entry.

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

For each significant choice, state what you are giving up. Format:
`references/prd-examples.md`.

---

## Phase 8 — Delivery Sequencing

Shippable slices — each independently deployable and useful on its own.

**State the placement invariant before listing any slice**, then check every row against it:

> **Placement invariant:** every artefact — requirement, acceptance criterion, doc edit, test —
> lands in the slice where its statement first becomes true. Not the slice that motivated it, and
> not the slice where it was noticed.

Write it into the plan, not just apply it silently: with the rule stated a misplaced row is
self-evident, and without it the same misplacement gets independently rediscovered by three
reviewers across two rounds.

**Then state build-order prerequisites explicitly.** "Everything else may ship in any order" is
almost always false — anything consuming a new module depends on the slice creating it. Name the
edges, or say there are none and be right.

Slice formats: `references/prd-examples.md`.

---

## Phase 9 — Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|

**For each risk, name the guard that already mitigates it, or state that none does — checked, not
assumed.** Grep for an existing refusal before inventing a mitigation. A risk whose mitigation is
an unbuilt design option is two unresolved things in one row, and it invites the reviewer to
debate the option instead of the risk.

**Label rows the way the repo labels them** — `RISK-1` is this skill's convention, not every
project's. See the plan-file guard check in `references/precision-rules.md`. Examples:
`references/prd-examples.md`.

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

Run before handing to `/board-review`. A defect fixed here costs one edit; the same defect fixed
via the board costs a reviewer's budget, a round of amendments, a re-review of the amended text,
and often a second defect introduced by the amendment.

Work the self-check at the bottom of `references/precision-rules.md` and **fix what it finds
now**. Every line is checkable without judgement:

- **Re-verify every `file:line` citation** against the file as it is now, and replace with a
  symbol reference wherever the exact line does not matter. Phase 0 citations have already drifted.
- **Grep for every number.** Each is either in `## Measured facts` with its command, or derived at
  implementation time. A number in two places is a defect even if both copies agree today.
- **Grep for each normative rule's keywords** to find restatements. Where prose and a table both
  state a rule, delete one or mark which is normative.
- **Run the tests the plan claims will change**, and correct the list from real output.
- **Grep for universal quantifiers** — "always", "never", "every", "only", "any order",
  "strictly", "monotonically" — and scope or delete each.
- **Grep for duplication.** Any value, rule, or code block appearing more than once is the defect.
  Collapse to one source of truth; cite the repo instead of re-quoting it.

Report in one line: *"Precision sweep: fixed N items (M stale citations, K duplicated values, J
unscoped claims, …). Plan is at L lines."* If it fixed nothing, say so explicitly.

---

## Completion

1. Set `**Status:**` in the task file to `⬜ Open`.
2. Update the matching `TODO.md` row to `⬜ Open`.
3. Do **not** set `🔍 Reviewed` — that is reserved for after `/board-review` passes.

Then prompt: *"Plan written and status set to ⬜ Open. Ready to run `/board-review` before
[implementation / applying to the cluster]?"*

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

**No line-count target.** Length alone is not a defect and is not scored; duplication is. A long
plan that says everything once is fine; a short plan restating a value in three places is not. If
a plan feels long, cut restatement, not content — never cut requirements, ADRs, or risk entries to
hit a page count. A great plan also has diagrams.
