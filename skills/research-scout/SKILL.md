---
name: research-scout
description: Proactive research companion that challenges framing, surfaces blind spots, and injects outsider thinking — questions the questions before research begins.
---

# research-scout

Challenge how a problem is framed *before* investing in researching it. Generate unexpected
questions, surface hidden assumptions, and propose alternative framings the research plan cannot
yet see.

Use it before committing to a topic when: a `TOPICS.md` item feels obvious or tightly bounded ·
the plan has grown in one direction and may have a blind spot · a charge came down from
stakeholders and needs stress-testing · you want a second opinion on a framing · you have just
finished a cluster of related reports and want to know what was never asked.

**What it does not do:** write concept files or reports (that is `research-workflow`) · do the
research (it audits whether the *right* research is planned) · require citations (its outputs are
speculative provocations, not factual claims) · write to `TOPICS.md`.

## Modes

```
/research-scout framing <topic or charge>   # challenge a single topic's framing
/research-scout audit                        # sweep the full TOPICS.md backlog
/research-scout wildcard <domain>            # max-diversity question set for a domain
/research-scout steelman <report-slug>       # challenge a completed report's assumptions
```

Plain English works too — "Before we research the oidc-agent socket forwarding topic, challenge
how we've framed it" · "Do a scout audit — what are we not asking?" · "What would a payments
engineer ask about our token lifecycle that we haven't thought of?"

## Operating principles

- **Think like an outsider, write like an insider.** Ask what a project-immersed researcher has
  stopped asking, but stay project-literate — **always read the project files first**
  (`TOPICS.md`, `README.md`, named sources or reports), and announce in one line what context you
  have. Never generate questions in a vacuum.
- **Provocation over completeness.** One question that genuinely reframes the problem beats ten
  that refine it.
- **No corroboration required, no invention either.** Speculative questions and hypotheses,
  grounded in actual project context.
- **The user decides.** Recommendations are always a checklist; never write to `TOPICS.md`
  directly. On explicit approval, supply paste-ready rows in `research-workflow`'s format, and
  remind the user that the priority emoji is only a scout estimate:

  ```
  | 🔸 P2 | 🔲 todo | report | <topic> | — | <notes, dependencies, why this matters> |
  ```

  Confirm it with `python3 .claude/skills/research-workflow/scripts/blast-radius.py`.

---

## Framing mode

Five categories of challenge for a topic, charge, or open question:

1. **Hidden assumptions** — what must be true for this to be the right question? List the
   load-bearing ones. At least one should feel uncomfortable to name.
2. **The question behind the question** — what deeper problem or fear is this a proxy for? If the
   answer came back "no, it doesn't work", what would the team do — and is *that* the real
   decision being avoided?
3. **Scope inversions** — what does the research look like with the opposite polarity? ("Can we
   *remove* AmSC rather than adding it?" · "What if we issued *fewer* tokens?") The inverted
   question is sometimes more tractable, and often more honest.
4. **Outsider questions** — pick two from: payments/fintech engineer, distributed systems
   researcher, regulator, red-team analyst, UX researcher, operations-at-scale team. Their naive
   questions expose what the domain experts stopped questioning.
5. **Failure mode questions** — the three most likely ways the conclusion could be wrong. Not "we
   lacked data" — be specific. What would a well-informed sceptic attack first?

```markdown
## Scout Report: <topic>
*Scout run: YYYY-MM-DD*

### Hidden Assumptions
### The Question Behind the Question
### Scope Inversions

### Outsider Perspectives
| Domain | Outsider question |
|--------|------------------|
| Fintech/payments | … |
| Distributed systems | … |
| Regulator / auditor | … |
| Red-team / attacker | … |

### Failure Mode Questions
1. …

### Scout Recommendations
> Candidate topics — **user must approve before promoting**
- [ ] `todo` concept — <topic>: <one-line reason>
```

## Audit mode

Read `TOPICS.md` and `CHARGES.md` if present, and identify: **cluster concentration** (which
sub-domains are over-represented, and what is conspicuously absent) · **narrowing spirals**
(groups of topics that are each refinements of one shared assumption — name the assumption) ·
**missing contrarian topics** (research that could contradict an existing `done` report) ·
**external forcing functions** (standards bodies, regulatory shifts, vendor roadmaps that could
invalidate current conclusions but aren't on the radar) · **absence of the user/operator
perspective** (does the agenda reflect the people who will live with the system, not just build
it?).

```markdown
## Scout Audit: Research Agenda
*Scout run: YYYY-MM-DD*

### Cluster Map
| Domain cluster | Topics in backlog | Share |
|----------------|------------------|-------|

### Conspicuous Absences
### Narrowing Spirals (shared assumptions to stress-test)
- Topics: [A, B, C] — shared assumption: "…"

### Contrarian Candidates
- [ ] If <X> were false, `reports/<slug>.md` would need rewriting. Worth verifying?

### External Forcing Functions
### User/Operator Perspective Gaps
### Scout Recommendations
```

## Wildcard mode

For a domain ("HPC identity", "federated auth", "token lifecycle"), generate the most **diverse**
10–15 questions possible — variety over depth, stretching the question space rather than being
comprehensive on one thread. Each question differs along at least one axis:

| Axis | Example |
|------|---------|
| **Time horizon** | True today vs in 5 years when quantum breaks RSA? |
| **Stakeholder** | A SLAC sysadmin vs a DOE auditor vs an HPC user at a partner lab? |
| **Scale** | 100 users vs 100,000 vs 10 million tokens/day? |
| **Failure mode** | Blast radius if the IdP goes down / the token store is compromised / the RFC is revised? |
| **Regulatory** | Which regime is not yet on the radar — CMMC, FedRAMP High, ISO 27001, NIS2? |
| **Technology alternative** | What if the project chose a different primitive — no OAuth at all, just mTLS + SPIFFE? |
| **Human factors** | What behaviour does this incentivise that we didn't intend? |
| **Second-order effects** | What changes about how labs collaborate, data moves, or vendors compete? |
| **Edge cases** | Users with no internet, no MFA device, expired POSIX accounts, multiple affiliations? |
| **Simplification** | What could be removed entirely? What is complexity for its own sake? |

## Steelman mode

Given a completed `reports/` slug, read it and build the strongest case **against its
conclusions**. Not a critique of quality — it assumes the report is correct, then asks what would
have to change for it to be wrong.

1. **Premise inventory** — the 5–7 key premises the recommendations rest on
2. **Strongest counterargument** — one paragraph making the best case for the opposite conclusion
3. **Conditional reversals** — "If [condition X] holds, recommendation Y should be reversed
   because…"
4. **Missing experiments** — which empirical test would most shift confidence?
5. **Dissenting voice** — a one-paragraph dissent from a thoughtful critic who read the same
   sources and concluded differently

---

Run before `/research-workflow` picks up a new topic, or periodically via `/research-scout audit`.
See "Pre-research: scout" in `research-workflow` for the integration sequence.
