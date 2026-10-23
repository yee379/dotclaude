---
name: research
description: Multi-source deep research using parallel subagents and native web fetch. Searches the web, synthesizes findings, and delivers cited reports with source attribution. Use when the user wants thorough research on any topic with evidence and citations.
origin: ECC
---

# Deep Research

Thorough, cited research reports from multiple web sources using parallel subagents and native
`WebSearch` / `WebFetch`. No paid MCPs required.

Activate for: in-depth research on any topic · competitive analysis, technology evaluation, market
sizing · due diligence · any question needing synthesis from multiple sources · targeted
fact-checking of claims in a document or plan · "research", "deep dive", "investigate", "verify",
"what's the current state of".

## Modes

**Exploratory** — open-ended research on a topic: build a synthesised picture from multiple
sources, surface patterns and implications, identify what remains unknown. Use when the user wants
to understand a topic, evaluate options, or build a knowledge base.

**Verification** — targeted fact-checking of claims in a document, plan, or prior summary:
confirm, contradict, or flag each checkable claim. Fast and narrow. Use when the user supplies a
document and asks to "verify", "fact-check", or "check the assumptions in".

---

## Verification mode

**Before launching any subagents**, extract the checkable claims:

1. Read the document.
2. List every concrete, verifiable assertion — technology choices, version numbers, library
   capabilities, scalability claims, compatibility statements, CVE status, API behaviours.
3. Discard anything obvious/uncontroversial, not checkable via web search, or already cited.
4. **Cap at 4 claims.** Prioritise: claims that if wrong would require redesign > claims that
   would add a warning > cosmetic claims.

Fewer than 2 checkable claims → skip web research entirely and return:
> "No material unverified claims found. Assumptions appear reasonable. ✅ PASS"

**Subagent profile** (leaner than Exploratory): one per claim, up to 4 total. Each does 2–3
searches and 1–2 full fetches, stopping as soon as the claim is confirmed or contradicted. Output
per subagent: verdict (confirmed / contradicted / unverified), 1–3 evidence bullets, source URL.
No prose. Total output ceiling 200 lines.

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

**Amendment trigger:** amend the source document only when a claim is **contradicted**, or
**unverified AND load-bearing** (removing it would change the design). Confirmed claims need no
amendment.

---

## Exploratory mode

### Step 1 — Understand the goal

One or two clarifying questions if needed: "What's your goal — learning, designing something,
making a decision, evaluating options?" · "Any specific angle, depth, or recency requirement?"
If the user says "just research it", proceed with reasonable defaults.

### Step 2 — Plan

Break the topic into 5–8 sub-questions, grouping related ideas. For "modern authentication and
authorisation systems": what are authn and authz, and where do definitions diverge? · what have
historically been the core challenges? · what are the security implications of different designs?
· what are the gaps in modern solutions, and the common industry patterns? · what makes a solution
succeed or fail in practice?

**Label each sub-question with its temporal scope** — this drives the subagent's search strategy:

- **Established** — settled knowledge, unlikely to have changed in 2+ years
- **Current** — active state of the art, worth checking for recent updates
- **Emerging** — fast-moving; sources from the last 6–12 months only

If the topic matches a **domain rubric** below, replace these generic sub-questions with the
rubric's dimension clusters — one cluster per subagent.

### Step 3 — Launch parallel subagents

One `general-purpose` subagent per sub-question (or two per agent for narrow topics), all launched
**in a single message**. Each is self-contained: it vets sources, searches, fetches, extracts facts
with per-claim confidence, **writes to disk incrementally**, and returns a structured summary — so
even an interrupted agent's work survives.

```
You are a research agent. Your job:

1. **Lateral read first.** Before deep-reading any source, scan *about* it:
   - Who wrote it? What is their affiliation or incentive?
   - Who cites it? Is it endorsed or criticised by authoritative sources?
   - Is it primary (spec, official docs, peer-reviewed) or secondary (blog, forum)?
   Spend 1 search on credibility before committing to a full fetch. Skip or
   downweight sources that fail this check.

2. Use WebSearch to find 4–6 sources for: "<sub-question>"
   Temporal scope: <established | current | emerging>
   - established: prefer specs, RFCs, official docs
   - current: prefer official docs + release notes from the last 12 months
   - emerging: last 6 months only; flag anything older as potentially stale

3. Use WebFetch to read the 2–3 most credible URLs in full.

4. Persist findings incrementally to: research/<slug>/<agent-N>.md
   Write after each source, with a ## Sources section at the bottom.

5. Return a structured findings block:
   - Key facts with source URLs and temporal label
   - Per-claim confidence: High (primary), Medium (secondary corroborated),
     Low (single secondary or inferred)
   - Conflicting information, stated explicitly
   - Gaps where data was unavailable — and what source would close each
   - Recency of sources

6. Add a short analysis layer (3–5 bullets max, one precise sentence each; omit
   any that yield nothing):
   - **Implications**: what the facts suggest that sources don't state explicitly
   - **Tensions**: where sources contradict or pull in different directions
   - **Absences**: what you expected to find but didn't — signal in the silence
   - **Patterns**: recurring themes across sources

Search strategy: 2–3 keyword variations (broad → specific → news-focused).
Prioritise official docs, academic, reputable news > blogs > forums. If a page
fails to fetch (bot-blocked, JS-heavy), try r.jina.ai/<url> or note it and move on.
```

### Step 4 — Adversarial pass (mandatory)

After all subagents complete, spawn **one dedicated adversarial subagent** whose only job is to
challenge the emerging synthesis — not to add supporting evidence.

```
You are a skeptical reviewer. You have been given a set of research findings.
Your job is NOT to summarise or extend them — it is to find their weaknesses.

For each major claim or recommendation:
1. What is the strongest counter-argument or counter-evidence?
2. Are there failure cases, known critics, or cautionary tales not mentioned?
3. Are any sources low-credibility, outdated, or single-sourced?
4. What assumptions are baked in that might not hold in a different context?
5. Is the conclusion stronger than the evidence actually supports?
6. Where sources conflict or overlap (RFC vs. draft vs. vendor doc vs. blog post), does the
   synthesis state which one takes precedence and why? An unresolved conflict with no stated
   precedence is a material finding, not a detail to smooth over.
7. For each claimed "standard" or "best practice", is there a real implementation example — not
   just the spec text — showing the concrete fields or values in use (e.g., an actual `act.iss` /
   `act.sub` pair in a token-exchange implementation, not just RFC 8693's description of them)? A
   practice with no cited implementation is unverified in practice, whatever the spec says.
8. How prevalent is the practice actually — ubiquitous, common among major implementers, a single
   vendor's convention, or seen only in a draft/proposal with no adoption? State this explicitly;
   "best practice" asserted without an adoption estimate is a claim stronger than its evidence.

Search specifically for: criticism, failure post-mortems, dissenting expert opinion, known
limitations, edge cases the initial research may have missed, real production implementations
(open-source code, vendor docs with worked examples) of each claimed standard, and any data on
how many implementers actually follow it.

Return a list of challenges, each with a severity (material / minor) and the source or reasoning
behind it. Tag each challenge by kind — counter-evidence, unresolved precedence, or
missing/unverified real-world implementation — so the synthesis step can route it correctly. Do
not pad — if a finding is solid and already backed by a real implementation, say so briefly.
```

Incorporate the results: strengthen the claim with corroboration, lower its confidence, or move it
to Open Questions. For an unresolved-precedence challenge, state the precedence explicitly in the
report (which source wins and why) rather than presenting the conflicting sources side by side. For
a missing-implementation challenge, either add the real example found or relabel the claim as
spec-only / low adoption — do not keep calling it a "best practice" without one.

### Step 5 — Consolidate and synthesise

Read each `research/<slug>/agent-N.md` plus `adversarial.md`. Merge, deduplicate sources, resolve
conflicts (primary over secondary; surface irreconcilable conflicts explicitly).

Then run a cross-cutting pass, which becomes the backbone of `## Patterns & Implications` — not a
restatement of facts:

- **Cross-question patterns** — themes surfacing across multiple sub-questions
- **Temporal arc** — does the established picture differ from the current state? Is something
  once settled now being challenged?
- **Hidden implications** — what the combined evidence suggests that no single source states
- **Tension resolution** — where sub-questions pointed different ways, name the tension

### Step 6 — Deliver

```markdown
# [Topic]: Research Report
*Generated: [date] | Sources: [N] | Overall Confidence: [High/Medium/Low]*

## Executive Summary
[3–5 sentences. State findings and implications directly — not "it depends" without a
follow-up. A reader who reads only this should know the main conclusion and why.]

## 1. [First Major Theme]
- **[Claim]** — [source]([url]) · *High confidence (primary spec)*
- **[Claim]** — [source]([url]) · *Medium confidence (two secondary sources)*
- **[Claim]** — inferred from [source]([url]) · *Low confidence (single source)*

## 2. [Second Major Theme]
## 3. [Third Major Theme]

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
- **[Challenge]** (material) — [reasoning/source]
- **[Challenge]** (minor) — [reasoning/source]
[If none: "No material counter-evidence found."]

## Open Questions
1. **[Question]** — what source or experiment would close this gap

## Key Takeaways
- [Actionable insight — not a restatement of a finding above]

## Sources
1. [Title](url) — [one-line summary] · [tier: primary / authoritative secondary / community]

## Methodology
Searched [N] queries across [K] subagents + 1 adversarial pass.
Sub-questions investigated: [list with temporal scope labels]
Fetch failures / gaps: [note any blocked or unavailable sources]
```

Short topics: post the full report in chat. Long reports: post Executive Summary + Key Takeaways,
and save the full report to a file.

**Blocked pages:** try the reader proxy `https://r.jina.ai/<url>`, then an archive snapshot
`https://web.archive.org/web/<url>` (Google's `webcache` endpoint was retired in 2024 — do not
use it), then an alternate source. Note the failed URL in Methodology and move on.

---

## Quality rules

1. **Every claim needs a source**, labelled **High / Medium / Low** with the method. If only one
   source says it, it is Low.
2. **Lateral read before deep read** — vet credibility before spending context on a source.
3. **The adversarial pass is mandatory** in Exploratory mode. Not optional, not a stretch goal.
4. **Recency matters** — prefer the last 12 months for "current" claims, and **name temporal
   shifts explicitly** in Temporal Landscape rather than blending eras.
5. **Acknowledge gaps.** If a sub-question yielded nothing, say so and name what would close it.
   "Insufficient data found" beats a guess.
6. **Separate fact from inference.** Label estimates, projections, and opinions.
7. **Insight density over completeness.** Three precise insights beat ten surface summaries.
8. **Implication ≠ restatement.** "X is growing" is a fact; "X growing while Y is flat suggests
   consolidation" is an insight.

## Programmatic tool calling

Inside a `research-workflow` project, load `references/ptc-patterns.md` (in the
`research-workflow` skill directory). Technique 2 matters most: batch workspace queries in Python
and keep intermediate results off-context.

---

## Domain rubrics

### AI Agent Framework

For a framework, SDK, library, or platform that runs AI agents (LangChain, LangGraph, CrewAI,
AutoGen, Google ADK, OpenHands, kagent, Hatchet).

1. **Core architecture & primitives** — execution model (loop, graph, chain, event-driven,
   stateful/stateless) · building blocks (chains, graphs, agents, tasks, tools, memory,
   retrievers), stable vs experimental · framework vs orchestration layer: what is in scope and
   what needs extension · version history and breaking changes in the last 12 months.
2. **MCP & external tool integration** — MCP support, transports (stdio/SSE/HTTP), spec version ·
   tool filtering, multi-server support, auth model · if no MCP, how tools connect and whether
   MCP is on the roadmap.
3. **Multi-agent coordination & streaming** — supervisor/worker, handoff, tool-as-agent, fan-out,
   hierarchical subagents · streaming model (async iterator, SSE, WebSocket, callback) and whether
   it is first-class or bolted on · event types, intermediate tool result streaming ·
   observability: built-in tracing, cost attribution, OpenTelemetry.
4. **K8s deployment & multi-tenancy** — official Helm chart, operator, or manifests; self-hosted
   option · per-user session isolation, namespace support, group-scoped access · session/state
   persistence (in-memory, PostgreSQL, Redis) with resume and fork semantics · built-in USD/token
   caps per session, user, or group.
5. **Ecosystem position & fit** — adoption and maintenance health (stars, release cadence,
   contributors) · known criticisms (abstraction leaks, debugging difficulty, performance, version
   churn) · relationship to other frameworks in the stack · integration with agentgateway,
   Claude Code / Codex CLI, A2A protocol.

### Auth & Identity Stack

For an authentication, authorisation, or identity system (Dex, Keycloak, SPIRE, Vault, OAuth 2.x
flows, MCP auth profiles).

1. Protocol and spec compliance — RFCs, grant types, OIDC vs SAML, PKCE, PAR
2. Group/claim model — how groups are stored, resolved, and propagated through the token chain
3. Token lifecycle — issuance, rotation, revocation, TTL, refresh semantics
4. K8s integration — ServiceAccount, RBAC, Gateway API, ForwardAuth
5. Multi-tenant gaps and federation limits

## Examples

```
"Research the current state of nuclear fusion energy"
"Deep dive into Rust vs Go for backend services in 2026"
"Research LangChain"                            → AI Agent Framework rubric
"Research Dex OIDC"                             → Auth & Identity Stack rubric
"Verify the assumptions in this plan: <paste>"  → Verification mode
```
