---
name: research
description: Multi-source deep research using parallel subagents and native web fetch. Searches the web, synthesizes findings, and delivers cited reports with source attribution. Use when the user wants thorough research on any topic with evidence and citations.
origin: ECC
---

# Deep Research

Produce thorough, cited research reports from multiple web sources using parallel subagents and native fetch — no paid MCPs required.

---

## When to Activate

- User asks to research any topic in depth
- Competitive analysis, technology evaluation, or market sizing
- Due diligence on companies, investors, technologies, or trends
- Any question requiring synthesis from multiple sources
- Targeted fact-checking of specific claims in a document or plan
- User says "research", "deep dive", "investigate", "verify", or "what's the current state of"

---

## Tools Used

- **WebSearch** — native web search for discovering sources
- **WebFetch** — native HTTP fetch for reading full page content
- **Agent (subagents)** — parallel research workers, one per sub-question or claim

No paid MCPs or external services required.

---

## Modes

### Exploratory mode

Open-ended research on a topic. Goal: build a thorough, synthesised picture from multiple
sources, surface patterns and implications, and identify what remains unknown.

Use when: the user wants to understand a topic, evaluate options, or build a knowledge base.

### Verification mode

Targeted fact-checking of specific claims in a document, plan, or prior summary. Goal:
confirm, contradict, or flag as unverified each checkable claim — fast and narrow.

Use when: the user provides a document or plan and asks to "verify", "fact-check", or
"check the assumptions in".

**Before launching any subagents**, extract the checkable claims:

1. Read the document/plan.
2. List every concrete, verifiable assertion — technology choices, version numbers, library
   capabilities, scalability claims, compatibility statements, CVE status, API behaviours.
3. Discard anything that is: (a) obvious/uncontroversial, (b) not checkable via web search,
   or (c) already cited with a source.
4. **Cap at 4 claims.** Prioritise: claims that if wrong would require redesign > claims
   that would add a warning > cosmetic claims.

If fewer than 2 checkable claims are found, skip web research entirely and return:
> "No material unverified claims found. Assumptions appear reasonable. ✅ PASS"

**Subagent profile for Verification mode** (leaner than Exploratory):
- 1 subagent per claim — up to 4 subagents total
- Each subagent: 2–3 searches max, 1–2 full page fetches, stop as soon as the claim
  is confirmed or contradicted
- Output per subagent: verdict (confirmed / contradicted / unverified) + 1–3 bullet
  points of evidence + source URL. No prose paragraphs.
- Total output ceiling: 200 lines.

**Output format for Verification mode:**

```markdown
## Claim Verdicts

| Claim | Verdict | Evidence | Source |
|---|---|---|---|
| Redis Streams supports consumer groups since v5.0 | ✅ confirmed | Redis docs confirm | https://... |
| library X is actively maintained | ⚠️ unverified | Last commit 14 months ago | https://... |
| approach Y is deprecated in favour of Z | ❌ contradicted | Official guide recommends Y | https://... |

## Open Questions
1. [Claim that could not be verified — what source would close this gap]

## Summary
<2-3 bullets — only findings that would change a decision>

## Status
PASS | PASS WITH WARNINGS | FAIL
```

**Amendment trigger:** only amend the source document when a claim is **contradicted** or
**unverified AND load-bearing** (removing it would change the design). Confirmed claims
need no amendment.

---

## Workflow (Exploratory mode)

### Step 1 — Understand the Goal

Ask 1–2 quick clarifying questions if needed:
- "What's your goal — learning, designing something, making a decision, or evaluating options?"
- "Any specific angle, depth, or recency requirement?"

If the user says "just research it" — proceed with reasonable defaults.

### Step 2 — Plan the Research

Break the topic into 5–8 research sub-questions. Think broadly; group related ideas together.

Example for "Modern authentication and authorisation systems":
- What are authentication and authorisation, and where do definitions diverge?
- What historically have been the core challenges?
- What are the security implications of different designs?
- What are the gaps with modern solutions? Common patterns across industry?
- What makes a solution succeed or fail in practice?

Explicitly identify the **temporal scope** for each sub-question:
- **Established** — settled knowledge, unlikely to have changed in 2+ years
- **Current** — active state of the art, worth checking for recent updates
- **Emerging** — fast-moving, sources from last 6–12 months only

Label each sub-question with its temporal scope — this drives subagent search strategy.

### Step 3 — Launch Parallel Subagents

Spawn one `general-purpose` subagent per sub-question (or group 2 sub-questions per agent for narrow topics).

Each agent receives:

```
You are a research agent. Your job:

1. **Lateral read first.** Before deep-reading any source, quickly scan *about* it:
   - Who wrote it? What is their affiliation or incentive?
   - Who cites it? Is it endorsed or criticised by authoritative sources?
   - Is it primary (spec, official docs, peer-reviewed) or secondary (blog, forum)?
   Spend 1 search on source credibility before committing to a full fetch.
   Skip or downweight sources that fail this check.

2. Use WebSearch to find 4–6 relevant sources for: "<sub-question>"
   Temporal scope: <established | current | emerging>
   - For "established": prefer specs, RFCs, official docs
   - For "current": prefer official docs + recent release notes (last 12 months)
   - For "emerging": prefer last 6 months only; flag anything older as potentially stale

3. Use WebFetch to read the 2–3 most credible URLs in full.

4. Persist findings incrementally to: research/<slug>/<agent-N>.md
   Write after each source — so progress is not lost if context grows large.
   Use a running markdown file with a ## Sources section at the bottom.

5. Return a structured findings block:
   - Key facts with source URLs and temporal label (established / current / emerging)
   - Per-claim confidence: High (primary source), Medium (secondary corroborated),
     Low (single secondary or inferred)
   - Conflicting information noted explicitly
   - Gaps where data was unavailable — and what source would close each gap
   - Recency of sources

6. Add a short analysis layer (3–5 bullets max):
   - **Implications**: what do these facts suggest that sources don't state explicitly?
   - **Tensions**: where do sources contradict or pull in different directions?
   - **Absences**: what would you expect to find but didn't? (signal in the silence)
   - **Patterns**: recurring themes across sources
   One precise sentence per bullet. Omit any that yield nothing useful.

Search strategy:
- Try 2–3 keyword variations (broad → specific → news-focused)
- Prioritize: official docs, academic, reputable news > blogs > forums
- If a page fails to fetch (bot-blocked, JS-heavy), try r.jina.ai/<url> or note and move on
```

Launch all agents **in parallel** in a single message for maximum speed.

### Step 4 — Adversarial Pass

After all subagents complete, spawn **one dedicated adversarial subagent**. Its sole job
is to challenge the emerging synthesis — not to add more supporting evidence.

Adversarial subagent prompt:

```
You are a skeptical reviewer. You have been given a set of research findings.
Your job is NOT to summarise or extend them — it is to find their weaknesses.

For each major claim or recommendation in the findings:
1. What is the strongest counter-argument or counter-evidence?
2. Are there failure cases, known critics, or cautionary tales not mentioned?
3. Are any sources low-credibility, outdated, or single-sourced?
4. What assumptions are baked in that might not hold in a different context?
5. Is the conclusion stronger than the evidence actually supports?

Search specifically for: criticism, failure post-mortems, dissenting expert opinion,
known limitations, and edge cases the initial research may have missed.

Return: a list of challenges, each with a severity (material / minor) and the
source or reasoning behind it. Do not pad — if a finding is solid, say so briefly.
```

Incorporate adversarial findings into the synthesis: either strengthen the claim with
additional corroboration, lower its confidence level, or add it to Open Questions.

### Step 5 — Consolidate and Synthesize

Read each `research/<slug>/agent-N.md` file and the adversarial subagent's output.
Merge findings, deduplicate sources, resolve conflicts (prefer primary over secondary;
surface irreconcilable conflicts explicitly).

Run a cross-cutting synthesis pass before drafting:
- **Cross-question patterns** — what themes surface across multiple sub-questions?
- **Temporal arc** — does the established picture differ from the current state? Is
  something that was settled now being challenged?
- **Hidden implications** — what does the combined evidence suggest that no single source states?
- **Tension resolution** — where sub-questions pointed in different directions, name the tension

These become the backbone of `## Patterns & Implications` — not restatements of facts.

### Step 6 — Deliver

Synthesize into a single report using this structure:

```markdown
# [Topic]: Research Report
*Generated: [date] | Sources: [N] | Overall Confidence: [High/Medium/Low]*

## Executive Summary
[3–5 sentences. State findings and their implications directly — not "it depends"
without a follow-up. A reader who reads only this section should know the main
conclusion and the primary reason for it.]

## 1. [First Major Theme]
[Findings with inline citations and per-claim confidence labels]
- **[Claim]** — [source]([url]) · *High confidence (primary spec)*
- **[Claim]** — [source]([url]) · *Medium confidence (two secondary sources)*
- **[Claim]** — inferred from [source]([url]) · *Low confidence (single source)*

## 2. [Second Major Theme]
...

## 3. [Third Major Theme]
...

## Temporal Landscape
| Finding | Status | Last verified |
|---------|--------|---------------|
| [Established claim] | Established — stable | [year] |
| [Current practice] | Current — verify annually | [date] |
| [Emerging pattern] | Emerging — may shift in 6–12 months | [date] |

## Patterns & Implications
- [Cross-cutting pattern not visible in any single theme]
- [What the combined evidence implies that no source states directly]
- [Meaningful tension or absence — if the silence says something, name it]

## Adversarial Findings
[Material challenges surfaced by the adversarial pass]
- **[Challenge]** (material) — [reasoning/source]
- **[Challenge]** (minor) — [reasoning/source]
[If no material challenges: "No material counter-evidence found."]

## Open Questions
1. **[Question]** — what source or experiment would close this gap
2. **[Question]** — [same format]
[Include gaps surfaced by the adversarial pass and the initial subagents]

## Key Takeaways
- [Actionable insight — not a restatement of a finding above]
- [Actionable insight]
- [Actionable insight]

## Sources
1. [Title](url) — [one-line summary] · [tier: primary / authoritative secondary / community]
2. ...

## Methodology
Searched [N] queries across [K] subagents + 1 adversarial pass.
Sub-questions investigated: [list with temporal scope labels]
Fetch failures / gaps: [note any blocked or unavailable sources]
```

**Delivery:**
- **Short topics**: post the full report in chat
- **Long reports**: post Executive Summary + Key Takeaways; save full report to a file

### Fallback for Blocked Pages

If `WebFetch` returns an error or thin content:
- Try reader-mode proxy: `https://r.jina.ai/<url>` (free, no auth)
- Try an archive snapshot: `https://web.archive.org/web/<url>` (Google's `webcache` endpoint was retired in 2024 — do not use it)
- Search for the same information from an alternate source
- Note the failed URL in Methodology and move on

---

## Subagent Architecture

```
Main session
├── Subagent 1: Sub-question 1 (lateral read → WebSearch + WebFetch → agent-1.md)
├── Subagent 2: Sub-question 2 (lateral read → WebSearch + WebFetch → agent-2.md)
├── Subagent 3: Sub-questions 3–4 (lateral read → WebSearch + WebFetch → agent-3.md)
└── Subagent 4: Sub-question 5 (lateral read → WebSearch + WebFetch → agent-4.md)
         ↓ all run in parallel ↓
Adversarial subagent (challenges emerging synthesis → adversarial.md)
         ↓
Main session: read agent-*.md + adversarial.md → consolidate → synthesize → report
```

Each subagent is self-contained: it laterally vets sources, searches, fetches, extracts
facts with per-claim confidence, **writes findings incrementally to disk**, and returns a
structured summary. Even partial runs from interrupted agents are not lost.

---

## Programmatic Tool Calling

When used within a `research-workflow` project, load `references/ptc-patterns.md` (in the `research-workflow` skill directory) for the full three-technique PTC reference. Technique 2 is the most important: write Python to batch multiple workspace queries and keep intermediate results off-context.

---

## Quality Rules

1. **Every claim needs a source.** No unsourced assertions.
2. **Per-claim confidence.** Label each key claim High/Medium/Low with method.
3. **Lateral read before deep read.** Vet source credibility before investing context in it.
4. **Adversarial pass is mandatory** for Exploratory mode. It is not optional or a stretch goal.
5. **Cross-reference.** If only one source says it, flag it as Low confidence.
6. **Recency matters.** Prefer sources from the last 12 months for "current" claims.
7. **Acknowledge gaps.** If you couldn't find good info on a sub-question, say so — and name what source would close the gap.
8. **No hallucination.** If you don't know, say "insufficient data found."
9. **Separate fact from inference.** Label estimates, projections, and opinions clearly.
10. **Insight density over completeness.** 3 precise insights beat 10 surface summaries.
11. **Implication ≠ restatement.** "X is growing" is a fact. "X growing while Y is flat suggests consolidation" is an insight.
12. **Name temporal shifts explicitly.** If the established picture and the current state diverge, surface that in Temporal Landscape — don't blend them.

---

## Domain Rubrics

When the topic matches a known domain, replace the generic Step 2 sub-questions with the
domain rubric below. Rubrics define the mandatory dimensions to investigate — assign one
dimension cluster per subagent.

---

### AI Agent Framework

Use when researching a framework, SDK, library, or platform that runs AI agents
(e.g. LangChain, LangGraph, CrewAI, AutoGen, Google ADK, OpenHands, kagent, Hatchet).

**Dimension clusters:**

**1. Core architecture & primitives**
- Execution model (loop, graph, chain, event-driven, stateful/stateless)
- Primary building blocks (chains, graphs, agents, tasks, tools, memory, retrievers) — stable vs experimental
- Framework layer vs orchestration layer — what's in-scope vs requires extension
- Version history: breaking changes in last 12 months? Version churn?

**2. MCP & external tool integration**
- MCP support? Which transports (stdio / SSE / HTTP)? Which spec version?
- Tool filtering, multi-server support, authentication model
- If no MCP: how are external tools connected? MCP on roadmap?

**3. Multi-agent coordination & streaming**
- Supported patterns: supervisor/worker, handoff, tool-as-agent, fan-out, hierarchical subagents
- Streaming model: async iterator, SSE, WebSocket, callback — first-class or bolted on?
- Event types emitted; intermediate tool result streaming
- Observability: built-in tracing, cost attribution, OpenTelemetry support

**4. K8s deployment & multi-tenancy**
- Official Helm chart / operator / manifests? Self-hosted platform option?
- Multi-tenancy: per-user session isolation, namespace support, group-scoped access control
- Session/state persistence: in-memory, PostgreSQL, Redis? Resume and fork semantics
- Budget & resource controls: built-in USD/token caps per session/user/group?

**5. Ecosystem position & fit**
- Adoption and maintenance health (GitHub stars, release cadence, contributor count)
- Known criticisms: abstraction leaks, debugging difficulty, performance, version churn
- Relationship to other frameworks in the stack
- Integration with agentgateway, Claude Code / Codex CLI, A2A protocol support

---

### Auth & Identity Stack

Use when researching an authentication, authorisation, or identity system
(e.g. Dex, Keycloak, SPIRE, Vault, OAuth 2.x flows, MCP auth profiles).

**Dimension clusters:**

1. Protocol & spec compliance (RFCs, grant types, OIDC vs SAML, PKCE, PAR)
2. Group / claim model (how groups are stored, resolved, propagated through token chain)
3. Token lifecycle (issuance, rotation, revocation, TTL, refresh semantics)
4. K8s integration (ServiceAccount, RBAC, Gateway API, ForwardAuth)
5. Multi-tenant gaps and federation limits

---

## Examples

```
"Research the current state of nuclear fusion energy"
"Deep dive into Rust vs Go for backend services in 2026"
"What's the competitive landscape for AI code editors?"
"Research LangChain"               → uses AI Agent Framework rubric
"Research Dex OIDC"                → uses Auth & Identity Stack rubric
"Verify the assumptions in this plan: <paste>"  → Verification mode
"Fact-check this document"         → Verification mode
```
