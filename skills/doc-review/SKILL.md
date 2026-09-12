---
name: doc-review
description: Pre-implementation documentation coverage review. Checks that every doc needing an update is explicitly called out in the plan — README, ARCHITECTURE, API docs, runbooks, CHANGELOG, ADRs, capacity baselines — before any code or cluster change is made. Works in codebase mode (application features) and platform mode (Kubernetes/infrastructure). Pairs with /closeout-prd which executes updates post-ship. Use when asked to "check the docs plan", "documentation review", or as part of /board-review.
---

# Documentation Review

Runs on the **plan** — before any code or cluster change — and asks one question: *does this plan
account for every piece of documentation this change touches?*

Documentation debt is created at implementation time, not ship time. When a plan doesn't name the
docs needing updates, one of three things happens: engineers forget them; `/closeout-prd`
reverse-engineers partial updates from the diff and loses the "why"; or docs get updated
inconsistently so README and ARCHITECTURE disagree.

**Do NOT** make code, cluster, or doc changes. Find gaps in the plan's coverage and get the plan
to name them.

A board member of `/board-review` in both modes; `/closeout-prd` executes what this skill plans.
**Model routing:** Step 0 and impact-table classification are **`haiku`-eligible**; gap analysis
and breaking-change assessment need **`sonnet`**.

## Mode detection

**Platform mode** when the plan contains any of: `namespace`, `Helm`, `cluster`, `vcluster`,
`NetworkPolicy`, `StorageClass`, `PVC`, `node pool`, `Ingress`, `HelmRelease`, `kustomize`,
`GitOps`, or is sourced from `platform/` or a platform-prefixed `todo/`. **Codebase mode**
otherwise. State it: `> Mode: Platform` or `> Mode: Codebase`.

## Lane boundaries

This skill judges **coverage** — does the doc update exist as named work in the plan. Three
adjacent questions belong elsewhere; flag and defer, don't decide them:

| Question | Owner |
|---|---|
| Is the documentation *good* — readable, right examples, user-journey structure, troubleshooting? | `/codebase-ux-review` (dimension 3) |
| Is the *terminology* right against the domain model? Should this become an ADR? | `/draft-prd` (Grill Mode), then `/codebase-arch-review` |
| Is the capacity *sizing* in the baseline doc correct? | `/platform-capacity-review` |

You still check the ADR, glossary entry, and baseline update are **named as work** — you just
don't adjudicate their content.

## Subagent mode

When run inside `/board-review`, the orchestrator provides `Plan file:` and `Output file:`
(e.g. `todo/review/<slug>/round-N-dc.md`). If given an output path, load
`references/subagent-protocol.md` (in the `board-review` skill directory) and follow it.

Checkpoints: Step 0, impact table, each review section. Bias the safe default toward **adding**
the doc gap to the plan. Terminology issues surface as Issues, not questions.

**Priority hierarchy.** Codebase: impact table > breaking changes > gaps > everything else.
Platform: impact table > runbook gaps > onboarding guide gaps > breaking changes > everything else.

---

## Context gathering

Read, if they exist: `CONTEXT.md` (domain glossary — the canonical terminology) · `CONTEXT-MAP.md`
(multiple bounded contexts; find the relevant one) · `docs/adr/` (note any relevant) ·
`ARCHITECTURE.md` (to avoid contradicting existing decisions) · `CLAUDE.md` (conventions).

Read-only. Creating `CONTEXT.md` and writing ADRs belongs to `/draft-prd` and
`/codebase-arch-review` — if either is missing, that absence is a gap for the plan to name.

## Step 0: Documentation scope assessment

**Codebase mode:** Is there user-facing surface (new endpoints, commands, changed behaviour, new
config options, removed features)? Internal surface (new services, changed architecture, new ADRs,
changed deployment topology)? A breaking change (API changes, config renames, migrations,
deprecated paths — these need upgrade guides, not just doc updates)?

**Platform mode:** Operator-facing surface (new services to manage, new failure modes, new config
options, changed procedures)? Developer-facing surface (new self-service capabilities, new
onboarding steps)? A breaking change (namespace renames, StorageClass changes, ingress path
changes, config key renames)?

Exit only if **nothing** in the impact table applies: "This change has no documentation surface.
Skipping doc-review." This is a narrow gate — a backend refactor with no user surface still
usually touches ARCHITECTURE.md, an ADR, CLAUDE.md, or a runbook.

## Documentation impact table

**Mandatory.** Load `references/impact-tables.md` and fill in the table for the detected mode.
Any row that is **AFFECTED: yes** and **IN PLAN?: no** is a gap. Surface each individually.

---

## Review sections — codebase mode

> **Platform mode:** load `references/platform-mode.md` and follow P1–P5 instead of these four.

**Global stop rule: one gap, one AskUserQuestion. Never batch.** If a section has no gaps, say so
and move on.

### 1. User-facing documentation
Does the plan update README for new features, changed behaviour, removed options? Does it add a
user-forward CHANGELOG entry ("You can now X", not "Refactored Y")? For API changes — are
new/changed/removed endpoints documented, and request/response schemas updated? For CLI or config
changes — are all new flags, options, and environment variables documented? For breaking changes —
is there an upgrade guide or migration section?

### 2. Internal / architectural documentation
Does the plan update ARCHITECTURE.md for new services, changed boundaries, or new data flows? Does
it name the ADRs that need writing — checking against those `/codebase-arch-review` already
generated, so gaps are found without duplicating? For new workloads or infrastructure, is CLAUDE.md
updated with new commands or setup steps? For dev-setup or contributor-workflow changes, is
CONTRIBUTING.md? For new failure modes or alert conditions, is the runbook?

### 3. Inline documentation and diagrams
Does the plan identify which files need new or updated inline comments? For complex new logic, are
ASCII diagram comments called out as implementation work? For files with existing ASCII diagrams
that this change touches, does the plan note those diagrams must be reviewed for accuracy?

Stale inline diagrams are worse than none — they actively mislead. Reviewing them must be explicit
work, not an afterthought.

### 4. Breaking changes and migrations
A dedicated upgrade guide is required — a CHANGELOG entry alone is **not** sufficient — if any of
these holds: a public endpoint removed or its signature changed · a config key renamed or removed ·
a database migration required · a CLI flag renamed or removed · a behaviour change that silently
affects existing users · the auth or permission model changed.

Per breaking change: is the upgrade guide in the plan, does it specify **what breaks, how to detect
it, how to migrate, and the rollback path**, and is it flagged in CHANGELOG under
`### Breaking changes`?

---

## Asking questions

Describe each gap concretely: which doc, what is missing, what a user or engineer would be without
it. Options: **A)** add to plan now **B)** defer to `/closeout-prd` / post-apply close-out
**C)** not needed, with the reason. State your recommendation and **bias toward A** — deferred
documentation often never happens. **Platform runbook gaps are always A.**

## Required outputs

| Output | Content |
|---|---|
| Documentation impact table | Mandatory. Every affected doc has a concrete "what changes" entry. |
| Plan amendments | Per accepted gap, exactly what to add and where, in imperative form: "Update ARCHITECTURE.md: add the ingestion service to the component diagram and describe its data ownership." |
| Deferred to close-out | Items deferred rather than added, so `/closeout-prd` knows to look. |
| NOT in scope | Documentation considered and explicitly ruled out, one line each. |

```
Documentation Review complete — Mode: Codebase | Platform
─────────────────────────────────────────────────────
Step 0:           surface area assessed — user/operator-facing: Y/N,
                  internal: Y/N, breaking: Y/N
Docs reviewed:    N rows in impact table
Gaps found:       N
  → Added to plan:            N
  → Deferred to close-out:    N
  → Confirmed not needed:     N
Breaking changes: N (upgrade/migration guides required: N)
Deferred to other reviewers: N (doc quality → ux, terminology/ADRs → arch)
─────────────────────────────────────────────────────
Status: clean | gaps_open
```
