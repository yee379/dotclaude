---
name: research-scout
description: Proactive research companion that challenges framing, surfaces blind spots, and injects outsider thinking — questions the questions before research begins.
---

# research-scout

Challenge how a problem is framed before investing in researching it. Generate unexpected questions, surface hidden assumptions, and propose alternative framings that the research plan might not yet see.

---

## When to Use This Skill

Use `research-scout` **before** committing to a research topic or workplan when:

- A topic in `TOPICS.md` feels obvious or tightly bounded
- The research plan has been growing in one direction for a while and might have a blind spot
- A charge or question is handed down from stakeholders (and needs stress-testing before work begins)
- You want a second opinion on the framing of an open question
- You've just completed a cluster of related reports and want to check what wasn't asked

You can also run it on the whole `TOPICS.md` backlog to audit the collective framing of the research agenda at once.

---

## What This Skill Does NOT Do

- It does **not** write concept files or reports — that is `research-workflow`'s job
- It does **not** do the research — it audits whether the right research is being planned
- It does **not** add items to `TOPICS.md` on its own — it proposes candidates; the user decides what to promote
- It does **not** require corroboration or citations — its outputs are speculative provocations, not factual claims

---

## Scout Modes

```
/research-scout framing <topic or charge>     # challenge a single topic's framing
/research-scout audit                          # sweep the full TOPICS.md backlog
/research-scout wildcard <domain>             # generate max-diversity question set for a domain
/research-scout steelman <report-slug>        # challenge assumptions in a completed report
```

Plain English also works — describe what you want and the scout will infer the mode.

---

## Framing Mode — Challenge a Single Topic

Given a topic title, charge, or open question, the scout generates **five categories of challenge**:

### 1. Hidden Assumptions
What must be true for this question to be the right question? List the load-bearing assumptions buried in the framing. At least one should feel uncomfortable to name.

### 2. The Question Behind the Question
What deeper problem or fear is this research question actually a proxy for? If the answer came back "no" or "it doesn't work", what would the team do — and is that the real decision being avoided?

### 3. Scope Inversions
What would the research look like if the problem were stated with the opposite polarity? (e.g. "Can we remove AmSC rather than adding it?" / "What if we issued fewer tokens rather than more?") Sometimes the inverted question is more tractable or more honest.

### 4. Outsider Questions
What would someone from a completely different domain ask? Pick two: a payments/fintech engineer, a distributed systems researcher, a regulator, a red-team security analyst, a UX researcher, an operations-at-scale team. Their naive questions often expose assumptions the domain experts have stopped questioning.

### 5. Failure Mode Questions
What are the three most likely ways the research conclusion could be wrong? Not "we didn't have enough data" — be specific. What would a well-informed sceptic attack first?

**Output format** — a compact markdown section, not a full report:

```markdown
## Scout Report: <topic>

*Scout run: YYYY-MM-DD*

### Hidden Assumptions
- …

### The Question Behind the Question
…

### Scope Inversions
- …
- …

### Outsider Perspectives
| Domain | Outsider question |
|--------|------------------|
| Fintech/payments | … |
| Distributed systems | … |
| Regulator / auditor | … |
| Red-team / attacker | … |

### Failure Mode Questions
1. …
2. …
3. …

### Scout Recommendations
> Candidate topics to add to TOPICS.md — **user must approve before promoting**
- [ ] `todo` concept — <topic>: <one-line reason>
- [ ] `todo` report — <topic>: <one-line reason>
```

---

## Audit Mode — Sweep the Full Backlog

Read `TOPICS.md` and `CHARGES.md` (if present). Identify:

1. **Cluster concentration** — which sub-domains are over-represented? What is conspicuously absent?
2. **Narrowing spirals** — groups of related topics that are each refinements of the same assumption; flag the assumption they share
3. **Missing contrarian topics** — topics that, if researched, could contradict or invalidate existing `done` reports
4. **External forcing functions** — standards bodies, regulatory shifts, vendor roadmap events that could invalidate current conclusions but aren't on the radar
5. **Absence of user/operator perspective** — does the research agenda reflect the perspective of the people who will live with the system, not just the people building it?

**Output format:**

```markdown
## Scout Audit: Research Agenda

*Scout run: YYYY-MM-DD*

### Cluster Map
| Domain cluster | Topics in backlog | Share |
|----------------|------------------|-------|
| …              | N                | X%    |

### Conspicuous Absences
- …

### Narrowing Spirals (shared assumptions to stress-test)
- Topics: [A, B, C] — shared assumption: "…"

### Contrarian Candidates
- [ ] If <X> were false, report `reports/<slug>.md` would need to be rewritten. Worth verifying?

### External Forcing Functions
- …

### User/Operator Perspective Gaps
- …

### Scout Recommendations
> Candidate topics — user must approve before adding to TOPICS.md
- [ ] …
```

---

## Wildcard Mode — Maximum Diversity Question Set

For a domain (e.g. "HPC identity", "federated auth", "token lifecycle"), generate the most **diverse** possible set of 10–15 research questions — prioritising variety over depth. The goal is to stretch the question space as wide as possible, not to be comprehensive on any single thread.

Heuristics for diversity — each question should be different along at least one of these axes:

| Axis | Examples |
|------|---------|
| **Time horizon** | What's true today vs. what changes in 5 years when quantum breaks RSA? |
| **Stakeholder** | What matters to a SLAC sysadmin vs. a DOE auditor vs. an HPC user at a partner lab? |
| **Scale** | What works at 100 users vs. 100,000 users vs. 10 million tokens/day? |
| **Failure mode** | What's the blast radius if the IdP goes down / the token store is compromised / the RFC is revised? |
| **Regulatory** | What compliance regime is not yet on the radar — CMMC, FedRAMP High, ISO 27001, NIS2? |
| **Technology alternative** | What if the project chose a completely different primitive — no OAuth at all, just mTLS + SPIFFE everywhere? |
| **Human factors** | What behaviour does this system incentivise that we didn't intend? |
| **Second-order effects** | What does this change about the way labs collaborate, data moves, or vendors compete? |
| **Edge cases** | What happens for users with no internet, no MFA device, expired POSIX accounts, or multiple affiliations? |
| **Simplification** | What could be removed entirely? What is complexity for its own sake? |

---

## Steelman Mode — Challenge a Completed Report

Given a completed `reports/` file slug, read the report and construct the strongest possible case **against its conclusions**. This is not a critique of the report's quality — it assumes the report is correct and then asks what would have to change for it to be wrong.

Structure:
1. **Premise inventory** — list the 5–7 key premises the recommendations rest on
2. **Strongest counterargument** — one paragraph making the best case for the opposite conclusion
3. **Conditional reversals** — "If [condition X] is true, recommendation Y should be reversed because…"
4. **Missing experiments** — what empirical test, if run, would most shift confidence in the conclusion?
5. **Dissenting voice** — write a one-paragraph dissent from the perspective of a thoughtful critic who read the same sources and reached a different conclusion

---

## Operating Principles

- **Think like an outsider, write like an insider** — ask the questions a project-immersed researcher has stopped asking, but stay project-literate; read source files before generating questions.
- **Provocation over completeness** — one question that genuinely reframes the problem is worth more than ten that refine it.
- **No corroboration required, no invention either** — outputs are speculative questions and hypotheses, not factual claims; they must be grounded in actual project context.
- **The user decides** — recommendations appear in checklist format; the scout never writes to `TOPICS.md` directly. On approval, provide properly-formatted rows ready to paste (noting that `.claude/skills/research-workflow/scripts/blast-radius.py` should confirm priority).

---

## Integration with research-workflow

Run before `/research-workflow` picks up a new topic, or periodically via `/research-scout audit` to sweep the full backlog. See the Pre-Research: Scout section in `research-workflow` for the integration sequence.

---

## Session Behaviour

When invoked, the scout:

1. **Reads the project files first** — `TOPICS.md`, `README.md`, and any specified source files or reports. Do not generate questions in a vacuum.
2. **Announces what it read** — one-line summary of what context it has.
3. **Generates the scout report** using the appropriate mode.
4. **Presents candidate `TOPICS.md` rows** at the end — user approves before any are written.
5. **Does not update any project files** unless the user explicitly approves specific candidates and asks the scout to write the rows.

When writing `TOPICS.md` rows on user approval, follow the exact format from `research-workflow`:

```
| 🔸 P2 | 🔲 todo | report | <topic> | — | <notes, dependencies, why this matters> |
```

Priority emoji is a scout estimate — remind the user to run `python3 .claude/skills/research-workflow/scripts/blast-radius.py` to confirm.

---

## Example Invocations

```
# Challenge the framing before researching RFC 9700
/research-scout framing "RFC 9700 — OAuth 2.0 Security Best Current Practice"

# Audit the whole backlog for blind spots
/research-scout audit

# Wildcard questions for HPC identity
/research-scout wildcard "HPC batch job identity"

# Steelman the Keycloak vs Dex recommendation
/research-scout steelman keycloak-vs-dex
```

Or in plain English:

> "Before we research the oidc-agent socket forwarding topic, challenge how we've framed it."

> "Do a scout audit of our research agenda — what are we not asking?"

> "What would a payments engineer ask about our token lifecycle that we haven't thought of?"
