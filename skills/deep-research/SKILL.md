---
name: deep-research
description: Multi-source deep research using parallel subagents and native web fetch. Searches the web, synthesizes findings, and delivers cited reports with source attribution. Use when the user wants thorough research on any topic with evidence and citations.
origin: ECC
---

# Deep Research

Produce thorough, cited research reports from multiple web sources using parallel subagents and native fetch — no paid MCPs required.

## When to Activate

- User asks to research any topic in depth
- Competitive analysis, technology evaluation, or market sizing
- Due diligence on companies, investors, or technologies, or trends
- Any question requiring synthesis from multiple sources
- User says "research", "deep dive", "investigate", or "what's the current state of"

## Tools Used

- **WebSearch** — native web search for discovering sources
- **WebFetch** — native HTTP fetch for reading full page content
- **Agent (subagents)** — parallel research workers, one per sub-question

No paid MCPs or external services required.

## Workflow

### Step 1: Understand the Goal

Ask 1-2 quick clarifying questions:
- "What's your goal — learning, designing something new, implementing something unknown, making a decision, or writing something?"
- "Any specific angle or depth you want?"

If the user says "just research it" — skip ahead with reasonable defaults.

### Step 2: Plan the Research

Try to think broadly about the subject; categorize ideas together for further investigation:

Break the topic into 5-8 research sub-questions. Example:
- Topic: "Impact of AI on healthcare"
  - What are the main AI applications in healthcare today?
  - What clinical outcomes have been measured?
  - What are the regulatory challenges?
  - What companies are leading this space?
  - What's the market size and growth trajectory?
- Topic: "How are modern authentication and authorisation systems implemented"
  - How do we define what authentication and authorisation are?
  - What historically have been the challenges?
  - What are the security implications of different designs/implementations?
  - What are the gaps with modern solutions? Are there common practices or technologies being implemented across industry?
  - What are the key tenants that make a solution successful or fail miserably?

### Step 3: Launch Parallel Subagents

Spawn one `general-purpose` subagent per sub-question (or group 2 sub-questions per agent for narrow topics). Each agent receives:

```
You are a research agent. Your job:
1. Use WebSearch to find 4-6 relevant sources for: "<sub-question>"
2. Use WebFetch to read the 2-3 most promising URLs in full
3. Persist your findings incrementally to: research/<slug>/<agent-N>.md
   - Write partial findings as you go — after each source — so progress
     is not lost if your context grows too large or you are interrupted
   - Use a running markdown file with a ## Sources section at the bottom
4. Return a structured findings block:
   - Key facts with source URLs
   - Any conflicting information noted
   - Gaps where data was unavailable
   - Recency of sources (prefer last 12 months)
   - Potentially interesting/useful facets that warrant further research

Search strategy:
- Try 2-3 keyword variations (e.g. broad → specific → news-focused)
- Prioritize: official docs, academic, reputable news > blogs > forums
- If a page fails to fetch (bot-blocked, JS-heavy), note it and try an alternate source
```

Launch all agents **in parallel** in a single message for maximum speed.

### Step 4: Fallback for Blocked Pages

If `WebFetch` returns an error or thin content (bot detection, SPA, paywalled):
- Try a **cached version**: `https://webcache.googleusercontent.com/search?q=cache:<url>`
- Try a **reader-mode proxy**: `https://r.jina.ai/<url>` (free, no auth)
- Search for the same information from an alternate source
- Note the failed URL and move on — don't stall

### Step 5: Consolidate and Synthesize

Once all subagents complete, consolidate their persisted files:
- Read each `research/<slug>/agent-N.md` file
- Merge findings, deduplicate sources, and resolve any conflicts
- If a subagent was interrupted, its partial file still contains whatever it managed to persist — include it and note the gap

Then synthesize into a single report:

```markdown
# [Topic]: Research Report
*Generated: [date] | Sources: [N] | Confidence: [High/Medium/Low]*

## Executive Summary
[3-5 sentence overview of key findings]

## 1. [First Major Theme]
[Findings with inline citations]
- Key point ([Source Name](url))
- Supporting data ([Source Name](url))

## 2. [Second Major Theme]
...

## 3. [Third Major Theme]
...

## Key Takeaways
- [Actionable insight 1]
- [Actionable insight 2]
- [Actionable insight 3]

## Sources
1. [Title](url) — [one-line summary]
2. ...

## Methodology
Searched [N] queries. Analyzed [M] sources across [K] subagents.
Sub-questions investigated: [list]
Fetch failures / gaps: [note any blocked or unavailable sources]
```

### Step 6: Deliver

- **Short topics**: Post the full report in chat
- **Long reports**: Post the executive summary + key takeaways, save full report to a file

## Subagent Architecture

```
Main session
├── Subagent 1: Sub-question 1 (WebSearch + WebFetch → persists research/<slug>/agent-1.md)
├── Subagent 2: Sub-question 2 (WebSearch + WebFetch → persists research/<slug>/agent-2.md)
├── Subagent 3: Sub-questions 3-4 (WebSearch + WebFetch → persists research/<slug>/agent-3.md)
└── Subagent 4: Sub-question 5 (WebSearch + WebFetch → persists research/<slug>/agent-4.md)
         ↓ all run in parallel ↓
Main session: read agent-*.md files → consolidate → synthesize → write report
```

Each subagent is self-contained: it searches, fetches, extracts key facts, **writes findings incrementally to disk**, and returns a structured summary. The main session reads the persisted files to consolidate — so even partial runs from interrupted agents are not lost.

## Quality Rules

1. **Every claim needs a source.** No unsourced assertions.
2. **Cross-reference.** If only one source says it, flag it as unverified.
3. **Recency matters.** Prefer sources from the last 12 months.
4. **Acknowledge gaps.** If you couldn't find good info on a sub-question, say so.
5. **No hallucination.** If you don't know, say "insufficient data found."
6. **Separate fact from inference.** Label estimates, projections, and opinions clearly.
7. **Note fetch failures.** If pages were blocked or unavailable, list them in Methodology.

## Examples

```
"Research the current state of nuclear fusion energy"
"Deep dive into Rust vs Go for backend services in 2026"
"Research the best strategies for bootstrapping a SaaS business"
"What's happening with the US housing market right now?"
"Investigate the competitive landscape for AI code editors"
```
