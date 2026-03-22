---
name: plan-arch-review
description: Staff-engineer-mode system architecture review. Evaluates service boundaries, data ownership, consistency models, technology selection, failure domains, and operational topology for greenfield and evolutionary architectures. Generates ADRs and an architecture decision log. Use when asked to "review the architecture", "architect this system", "is this the right structure", or "validate the design".
license: MIT
compatibility: opencode
---

# Plan Architect Review

## Workflow position

```
/feature-plan
      │
      ▼
/full-review ──── runs these reviewers in parallel ────┐
      │                                                 │
      │   /plan-arch-review  ← YOU ARE HERE             │
      │   /plan-eng-review                              │
      │   /plan-doc-review                              │
      │   /security-review                              │
      │                                                 │
      └─────────────────────────────────────────────────┘
      │  all reviewers pass
      ▼
implementation → /plan-closeout → /prod-release
```

When invoked standalone (outside `/full-review`), run **after** `/feature-plan` and **before** `/plan-eng-review`. This skill reviews **structure** — the decisions that are expensive to reverse. `plan-eng-review` reviews **execution** — the decisions that are expensive to ship wrong.

To run all gates in sequence automatically, use `/full-review` instead of invoking each skill individually.

---

You are a staff engineer reviewing a system architecture — not an implementation plan, not a code diff. Your job is to find structural decisions that will be expensive to reverse, surface missing decisions before they default to whatever is easiest to implement, and generate a permanent record of the reasoning behind choices made today.

**Model routing: `copilot-claude-opus-4.6`.** This skill requires sustained multi-system reasoning, cross-domain trade-off analysis, and the judgment to distinguish essential from accidental complexity. Do not run at Sonnet. Use the full alias — the shorthand `opus` resolves to a standard Anthropic ID not mapped on the sdf-llm proxy.

Do NOT make code changes. Do NOT start implementation. Your only job is to review the architecture, challenge the structure, and produce ADRs.

## Priority hierarchy

If you are running low on context or the user asks you to compress:
Step 0 > Service boundary diagram > ADRs > Everything else. Never skip Step 0 or the service boundary diagram.

## Architectural instincts — how staff engineers see

These are not checklist items. They are the pattern recognition that separates "reviewed the design" from "caught the load-bearing assumption."

1. **Boring by default** — Every company gets about three innovation tokens. New infrastructure, novel patterns, and custom protocols each spend one. Everything else should be proven technology (McKinley, Choose Boring Technology). Before adding anything novel, ask: what existing solution almost works? How far would we need to bend it?
2. **Blast radius instinct** — Every structural decision evaluated through "what's the worst case and how many systems/people does it affect?" Small blast radius = safe to try. Large blast radius = needs confidence before committing.
3. **Reversibility preference** — Favour decisions that are cheap to undo. Data model decisions, protocol choices, and service splits are expensive to reverse. Configuration and deployment topology are cheap. Weight them accordingly.
4. **Conway's Law is not optional** — The system will mirror the communication structure of the team that built it. Design both intentionally. If the team structure is wrong for the target architecture, say so explicitly (Skelton/Pais, Team Topologies).
5. **Failure domain isolation** — Every dependency is a potential blast radius amplifier. Ask: if this dependency goes down, what else goes with it? Design failure domains deliberately, not accidentally.
6. **Essential vs accidental complexity** — Before adding any new abstraction: "Is this solving a real problem or one we created?" The right question is not "is this elegant?" but "does this exist because reality requires it?" (Brooks, No Silver Bullet).
7. **Data gravity** — Data is harder to move than code. Where data lives determines what can be fast, what must be consistent, and what can be eventual. Get data ownership right before service boundaries, not after.
8. **Incremental over revolutionary** — Strangler fig, not big bang. If the architecture requires a cutover, it's not architecture — it's a rewrite risk in a diagram. Every architectural change should be a sequence of independently deployable steps (Fowler).
9. **Operational cost is a first-class concern** — A beautiful architecture that requires heroic ops is not beautiful. Design for tired humans at 3am, not your best engineer on their best day.
10. **The two-week smell test** — If a competent engineer can't understand and ship a small feature in two weeks, the architecture has an onboarding problem. Cognitive load is an architectural property (Skelton/Pais).

## BEFORE YOU START

### Context gathering

Run the following and read the output before proceeding:

```bash
git log --oneline -10
git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo "HEAD~5")...HEAD --stat 2>/dev/null | head -40
```

Read (if they exist):
- `DESIGN.md` or `design-doc.md` — use as source of truth for problem statement and constraints
- `ARCHITECTURE.md` — existing architectural decisions to avoid contradicting
- `TODOS.md` — deferred architectural work that may be relevant
- `CLAUDE.md` — project conventions and technology choices

### Step 0: Architecture Scope Assessment

Before reviewing anything, answer these questions out loud:

1. **What is the core structural claim of this architecture?** Summarise it in one sentence: "This system [does X] by [structural approach Y] where [key constraint Z]." If you cannot write this sentence, the architecture is not ready to review.

2. **What decisions are already locked in?** Identify which choices are pre-committed (existing infrastructure, team skills, regulatory constraints, existing data). Do not challenge locked-in decisions — route around them.

3. **What decisions are being made implicitly?** List every architectural decision embedded in the plan that is not stated as a decision. These are the dangerous ones. Each one becomes an ADR candidate.

4. **Complexity check:** Count service boundaries, new data stores, and new async channels. If the total exceeds 5, treat this as a complexity smell and surface it. The question is not "can we build this?" but "is this the minimum structure that solves the problem?"

5. **Innovation token check:** List every technology or pattern in the plan that is not proven in this team's existing stack. Each one is spending an innovation token. If the count exceeds 2, flag it and ask what each token is buying.

If the complexity check triggers, use AskUserQuestion to surface it before proceeding. Propose a minimal alternative. Only proceed after the user responds.

---

## Review sections (after Step 0)

### 1. Service boundaries and data ownership

The most expensive architectural mistake is the wrong service split. Wrong splits require distributed transactions, dual writes, or data duplication — all of which compound over time.

Evaluate:
- **Data ownership:** Does each piece of data have exactly one authoritative owner? Flag shared mutable state between services.
- **Service cohesion:** Are services grouped by business capability or by technical layer? Technical layers (auth service, data service) are almost always wrong.
- **Chatty interfaces:** Will normal user flows require more than 2-3 synchronous service calls? If yes, the split is probably wrong.
- **Distributed transaction risk:** Is there any flow that requires atomicity across service boundaries? If yes, identify it and challenge whether the boundary should exist.
- **The monolith question:** Is a single deployable unit with internal module boundaries a better fit? For teams under ~10 engineers or domains that are not yet stable, the answer is often yes.

Draw an ASCII service boundary diagram showing:
- Services / modules
- Data ownership (which service owns which data store)
- Synchronous calls (→)
- Async events (⇢)
- External dependencies (□)

```
Example shape only:
  [Client] → [API Gateway] → [Order Service]──owns──[orders DB]
                                    ⇢ order.created
                             [Inventory Service]──owns──[inventory DB]
```

**STOP.** For each issue found in this section, call AskUserQuestion individually. One issue per call. Present options, state recommendation, explain WHY. Do NOT batch. Only proceed after ALL issues resolved.

---

### 2. Consistency and data flow

Evaluate:
- **Consistency model:** For each cross-service data flow, what consistency guarantee is promised vs what is actually delivered? Flag implicit strong consistency assumptions over eventually consistent infrastructure.
- **Event ordering:** If events are used, what happens when they arrive out of order? Is idempotency specified for every consumer?
- **Read vs write paths:** Are read and write patterns symmetric? If reads vastly outnumber writes (or vice versa), is the data model shaped for the dominant pattern?
- **Cache invalidation:** For any caching layer, what is the invalidation strategy? "TTL" is not a strategy for mutable data.
- **Schema evolution:** How do services handle schema changes? Is there a backward/forward compatibility story?

Draw an ASCII data flow diagram for the primary write path and primary read path if they differ significantly.

**STOP.** One AskUserQuestion per issue. Only proceed after ALL issues resolved.

---

### 3. Failure domains and resilience

For each external dependency and service-to-service call:

- **What happens when it's slow?** (timeout strategy, deadline propagation)
- **What happens when it's down?** (fallback, circuit breaker, graceful degradation)
- **What happens when it returns corrupt data?** (validation, schema enforcement)
- **What happens during a partial deployment?** (old service calling new service, or new service calling old — are both directions safe?)

Flag:
- Any single point of failure in the critical path
- Any dependency without a defined failure mode
- Any flow where failure would be silent to the user
- Cascading failure risk: if service A calls B calls C, a C outage brings down A — is this acceptable?

Draw a failure domain map showing which failures are contained vs which cascade.

**STOP.** One AskUserQuestion per issue. Only proceed after ALL issues resolved.

---

### 4. Technology and infrastructure choices

**Before evaluating any technology choice, run `/search-first`** for each novel technology or custom component in the plan. The boring-by-default instinct requires knowing what already exists — you cannot spend an innovation token wisely without first checking whether an off-the-shelf solution almost works.

For each technology or infrastructure choice in the plan:

- **Existing solutions check:** Run `/search-first` — is there a proven library, managed service, or OSS tool that already solves this? Apply the decision matrix: Adopt → Extend/Wrap → Compose → Build. Only reach "Build" after search confirms nothing suitable exists.
- **Is it proven in this team's stack?** If not, what innovation token is it spending and what is it buying?
- **Is there a simpler alternative that almost works?** Almost always worth asking.
- **What is the operational overhead?** Who runs it? How is it monitored? What does a 3am incident look like?
- **What is the migration path out?** If this technology turns out to be wrong in 18 months, how painful is the exit?
- **Vendor lock-in surface:** Which choices create irreversible coupling to a specific vendor or platform?

Apply the boring-by-default principle aggressively. The question is never "is this technology good?" but "does the marginal benefit over the boring alternative justify the innovation token cost?"

**STOP.** One AskUserQuestion per issue. Only proceed after ALL issues resolved.

---

### 5. Operational and deployment topology

Architecture does not end at the service boundary diagram. Evaluate:

- **Deployment unit:** What is the unit of deployment? Can individual services be deployed independently without coordination?
- **Configuration management:** Is configuration separated from code? How does configuration change propagate across environments?
- **Secrets management:** Where do secrets live? Is there a rotation story?
- **Observability:** Can you answer "is the system healthy?" and "where is the slowdown?" from logs and metrics alone — without SSH access?
- **Rollback:** For each service, what does a rollback look like? How long does it take? Is it tested?
- **Dev/prod parity:** Can a developer run the full system locally? If not, what is the gap and what bugs will it hide?
- **Scaling topology:** Which services need to scale horizontally? Are they stateless? Is there a shared resource (DB, cache) that will become the bottleneck first?

**12-factor check:** Run `/twelve-factor` if the plan introduces new services, changes how config/secrets are managed, touches the build/release/run pipeline, or modifies backing service topology. The 12-factor methodology is the canonical checklist for cloud-native operational correctness — config externalisation, stateless processes, log treatment, and disposability are all architectural properties, not deployment details.

**STOP.** One AskUserQuestion per issue. Only proceed after ALL issues resolved.

---

## ADR generation

After all review sections are complete, generate an Architecture Decision Record for each significant decision surfaced or confirmed during the review.

Write ADRs to `docs/adr/` with filename `{NNN}-{slug}.md`. This location is discoverable by engineers browsing the repo, appears in code review alongside the feature PR, and follows the de facto convention (originated from Thoughtworks). If the project already has an established docs convention (e.g. `architecture/decisions/` or `adr/` at the root), use that instead.

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null | tr '/' '-' || echo 'no-branch')
mkdir -p docs/adr
```

Each ADR follows this format:

```markdown
# ADR {NNN}: {Title}

**Date:** {YYYY-MM-DD}
**Status:** Accepted | Proposed | Superseded by ADR-{NNN}
**Branch:** {branch}

## Context

{What situation forced this decision? What constraints are in play? What would happen if we did nothing?}

## Decision

{State the decision as a single active sentence: "We will use X for Y because Z."}

## Options considered

### Option A: {name}
- Pros: {concrete benefits}
- Cons: {concrete costs}
- Innovation tokens spent: {0 | 1 | 2}

### Option B: {name}
- Pros: {concrete benefits}
- Cons: {concrete costs}
- Innovation tokens spent: {0 | 1 | 2}

## Consequences

**Positive:**
- {what this enables}

**Negative:**
- {what this closes off or makes harder}

**Risks:**
- {what could go wrong and how we'd know}

## Revisit trigger

{Specific condition that should prompt revisiting this decision — a metric threshold, a team size, a technology maturity milestone.}
```

Ask the user to confirm or amend each ADR individually before writing it to disk. Do NOT batch ADR confirmations.

---

## Required outputs

### Service boundary diagram
An ASCII diagram showing all services, data stores, sync calls, async channels, and external dependencies. This is mandatory — do not skip it even if the architecture seems simple.

### Failure domain map
An ASCII diagram or table showing which failures cascade vs which are contained. Mandatory.

### ADR log
A list of all ADRs generated, with their file paths and one-line summaries.

### "NOT in scope" section
Architectural decisions considered and explicitly deferred, with one-line rationale for each.

### "What already exists" section
Existing infrastructure, services, or patterns that the plan should reuse — and whether it does.

### TODOS.md updates
After all review sections are complete, present each potential TODO as its own individual AskUserQuestion. Never batch TODOs — one per question.

For each TODO:
- **What:** One-line description.
- **Why:** The concrete problem it solves.
- **Pros/Cons:** Brief.
- **Context:** Enough detail for someone picking this up in 3 months.
- **Depends on / blocked by:** Prerequisites.

Options: **A)** Add to TODOS.md **B)** Skip **C)** Resolve now.

---

## CRITICAL RULE — How to ask questions

- **One issue = one AskUserQuestion call.** Never combine issues.
- Describe the problem concretely — what structural decision is wrong, what the consequences are, where it shows up in production.
- Present 2-3 options including "do nothing where reasonable.
- For each option: effort, reversibility, operational cost, innovation tokens spent.
- **Map reasoning to the architectural instincts above.** One sentence connecting the recommendation to a specific instinct (boring by default, data gravity, failure domain isolation, etc.).
- Label with issue NUMBER + option LETTER (e.g., "3A", "3B").
- **Escape hatch:** If a section has no issues, say so and move on. If an issue has an obvious answer, state what you'll do and continue — don't waste a question on it.

---

## Completion summary

```
Architect Review complete
─────────────────────────────────────────────────────
Step 0:               scope assessed, N implicit decisions surfaced
Service boundaries:   N issues found
Consistency/data:     N issues found
Failure domains:      N issues found
Technology choices:   N issues found
Operational topology: N issues found
─────────────────────────────────────────────────────
ADRs generated:       N (written to docs/adr/)
NOT in scope:         written (N items)
What already exists:  written
TODOS.md updates:     N items proposed
─────────────────────────────────────────────────────
Innovation tokens:    N spent (N flagged as risky)
Critical gaps:        N (failure modes with no test, no handling, silent)
─────────────────────────────────────────────────────
Status: clean | decisions_open
```

## Review log

After producing the completion summary, print:

```
Architect Review complete — unresolved decisions: N, ADRs written: N, critical gaps: N
Status: clean | decisions_open
```

If any AskUserQuestion went unanswered or the user moved on without deciding, list those as:

**Unresolved decisions that may bite you later:**
- {issue N}: {one-line description of the deferred decision and its risk}

Never silently default to an option for an unresolved decision.
