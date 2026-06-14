---
name: research-workflow
description: Manages all research output — cataloguing concepts, writing reports, and synthesising charge answers into source/, concepts/, reports/, and charges/ with bidirectional cross-linking and confidence tracking.
---

# research-workflow

Catalogue concepts and write recommendation reports for any research project.

---

## Session Start — Do This First, Every Time

At the start of every session, before anything else:

1. **Read `TOPICS.md`** — understand the outstanding work queue; note all `todo` items and **always call out every `blocked` item explicitly** (see format below)
2. **Read `source/`** — scan for any primary documents relevant to the session topic
3. **Check `README.md`** — orient to what has already been written

**Blocked item callout format** — use this every time, without exception:

> ⚠️ **Blocked: `<topic>`**
> *Reason:* <blocking reason from notes>
> *Needs:* <what would unblock it — a decision, a missing source, a dependency topic>

If there are no blocked items, say so explicitly: *"No blocked items."* Do not silently skip this step.

Then respond to the user's request in one of two ways:

| Situation | Action |
|-----------|--------|
| User points at a specific topic or asks a question | Work it, or capture it to TOPICS.md if it's new |
| User says "what's next" or similar | Pick the first `todo` item from TOPICS.md and propose it |

**Proactive topic suggestions** — at every session start, after orienting, scan `README.md`
and `TOPICS.md` and surface 2–4 candidate topics not currently in the queue. Apply these
lenses to the existing corpus:

| Lens | Question to ask |
|------|----------------|
| **Steelman** | Which `done` report's conclusion is most vulnerable? What would invalidate it? |
| **Failure mode** | If a key recommendation turns out to be wrong, what breaks and how badly? |
| **Regulatory / compliance** | Is there a compliance regime, audit requirement, or standards body not yet on the radar? |
| **Operator / user perspective** | Does the research reflect the people who will *use* the system, not just the people building it? |
| **Simplification** | What could be removed, consolidated, or replaced with something simpler? |
| **Outsider domain** | What would a fintech engineer, a security red-teamer, or a distributed systems researcher ask that the current agenda hasn't? |
| **Contrarian expert** | Who in the field disagrees with the dominant approach, and have we read their argument? |

Present suggestions as a compact checklist — user promotes to `TOPICS.md`, or dismisses.
One line per suggestion; don't interrupt session flow. Example format:

> **Suggested topics (not yet in queue):**
> - [ ] `steelman` report — challenge the Keycloak recommendation: what if token volume assumptions are wrong?
> - [ ] `concept` — CMMC compliance angle on token storage: not currently covered
> - [ ] `report` — operator runbook gaps: research assumes happy-path provisioning only

**During any conversation**, capture new topics to TOPICS.md immediately when they surface — gaps, dependencies, deferred decisions, technologies mentioned without a concept entry. One-line acknowledgement, don't interrupt the flow.

**Context window**: research sessions accumulate context quickly. Use `/compact` between major tasks (after a concept file is written and before starting the next topic) to keep the context window healthy. The `strategic-compact` skill can suggest good compaction points if active.

---

## Pre-Research: Scout

Before committing to a research topic, invoke `/research-scout` to challenge the framing
and surface blind spots. The scout is a complement, not a gate — skip it when the topic is
urgent or already well-defined.

| Situation | Invocation |
|-----------|-----------|
| Topic feels obvious or tightly bounded | `/research-scout framing <topic>` |
| Picking up a `todo` item from a long backlog | `/research-scout framing <topic>` |
| After a cluster of related reports is done | `/research-scout audit` |
| Starting research in a new domain | `/research-scout wildcard <domain>` |
| Completed report drives a major recommendation | `/research-scout steelman <report-slug>` |

Scout outputs are proposals only — the user approves which candidates to promote to
`TOPICS.md`. See the `research-scout` skill for full mode documentation.

### Typical sequence

```
1. /research-scout framing <next topic>     ← challenge the framing
2. User approves 0–N scout candidates → TOPICS.md
3. Work the topic via normal research-workflow steps below
```

---

## Purpose

This skill has three modes:

| Mode | Command trigger | Output directory |
|------|----------------|-----------------|
| **Catalogue** a technology / standard / tool / concept | `/research-workflow catalogue <topic>` | `concepts/` |
| **Report** on a topic | `/research-workflow report <topic>` | `reports/` |
| **Charge** — synthesise existing research to answer a charge question | `/research-workflow charge <N>` or `answer charge N` | `charges/` |

You can also omit the mode word and describe what you want in plain English — Claude will infer which mode applies.

`README.md` and `TOPICS.md` at the project root must always be kept up to date.

---

## Research Agenda — TOPICS.md

`TOPICS.md` and `README.md` have complementary, non-overlapping roles:

| File | Role | Contains |
|------|------|----------|
| `TOPICS.md` | **Agenda** — full topic history | 🔲 `todo`, 🔄 `in-progress`, 🚫 `blocked`, ⏸️ `deferred`, ✅ `done` items |
| `README.md` | **Index** — backward-looking | Every completed output file, ordered for navigation |

**When a topic is done, mark it `done` in TOPICS.md** and add the output file to README.md.
Do not remove completed rows — they provide a history of what was researched and when.

### Reading TOPICS.md

At the start of any research session:
1. Read `TOPICS.md` — this is the outstanding work queue
2. **Call out every `blocked` item** using the callout format defined in Session Start — unconditionally, not "if relevant"
3. Note all `todo` items
4. Check whether the user's request matches an existing topic or is net-new

Also call out blocked items whenever they become relevant mid-session — e.g. if the user asks about a topic and a dependency of it is blocked, surface the blocker immediately.

### Working a topic

When picking up a `todo` topic:
1. Update its status to `in-progress` in `TOPICS.md` immediately
2. Follow the normal research workflow (Steps 1–5 below)
3. On completion: **mark the row `done` in `TOPICS.md`** (add output filename to notes) and add the output file to `README.md`

### Adding new topics

When a user requests something not in `TOPICS.md`:
1. Add it as a new row before starting work — type, status `in-progress`, notes
2. If the request spawns related follow-on topics (gaps, dependencies), add those as `todo`
3. If a topic is too vague to start, add it to the Backlog section with a "why it matters" note
   and ask the user for more context before proceeding. **Never pick up a Backlog item
   autonomously** — it must be explicitly promoted to `todo` by the user first.

**Backlog row format** is the same as all other TOPICS.md rows, with an additional `affects`
column listing the output files that reference it:

`| priority | topic | affects | why it might matter |`

### Capturing topics during conversation

**Any conversation about this project is a source of new topics.** Do not wait for an explicit
research request. Capture to `TOPICS.md` immediately whenever:

| Trigger | Action |
|---------|--------|
| A gap or unknown is mentioned ("we don't know if X supports Y") | Add as `todo` with the open question in notes |
| A dependency surfaces ("this requires understanding Z first") | Add Z as `todo`, note the dependency |
| A decision is deferred ("we'll figure out X later") | Add as `todo` or `deferred` with context |
| A new technology or standard is named that has no concept entry | Add as `todo` concept |
| A recommendation is made that hasn't been written up | Add as `todo` report |
| The user says "we should look into…" or "I wonder if…" | Add as `todo` or Backlog depending on urgency |

Write the entry immediately — **do not finish the conversation and add it later**. A topic
mentioned but not captured is a topic lost.

When adding a topic mid-conversation, acknowledge it briefly:
> *"Added to TOPICS.md: `todo` concept — RFC 9700 OAuth 2.0 Security BCP."*

Do not interrupt the conversation flow — one line is enough.

### TOPICS.md format

Each topic row has: `priority | status | type | topic | researched | notes`

| Column | Values / format |
|--------|----------------|
| `priority` | 🔺 P1 · 🔸 P2 · 🔹 P3 (see priority rules below) |
| `status` | 🔲 `todo` · 🔄 `in-progress` · 🚫 `blocked` · ⏸️ `deferred` · ✅ `done` |
| `type` | `concept` · `report` |
| `topic` | Short descriptive name |
| `researched` | `—` when not yet started; `YYYY-MM-DD` when research was performed (set when work begins, not when output is written) |
| `notes` | Scope, open questions, dependencies — include which existing files reference this topic |

Set `researched` to today's date when you begin working a topic (Step 2 of the workflow),
even if writing is deferred to a later session. This records when the information was
gathered, so staleness is visible at a glance.

### Priority rules

Every topic in TOPICS.md (including the Backlog) must carry a priority based on its blast
radius — how many existing `concepts/` and `reports/` files reference or depend on it:

| Priority | Emoji | Criteria |
|----------|-------|---------|
| P1 | 🔺 | Referenced by ≥5 existing outputs, OR blocks a deployment path, OR is a direct output of completed research with no file yet |
| P2 | 🔸 | Referenced by 2–4 existing outputs, OR unblocks a known gap in an existing report |
| P3 | 🔹 | Referenced by 0–1 existing outputs; low urgency |

**When adding any new topic**, run `blast-radius.py` before writing the row — the
reference count must be accurate. Include the affected filenames in `notes`:

```bash
python3 .claude/skills/research-workflow/scripts/blast-radius.py <keyword> [keyword2 ...]
```

**When a new output file is written** (Step 5), run `priority-audit.py` to detect
any existing TOPICS.md items whose blast radius has grown due to the new file, and
update their reference count, affected files list, and priority as needed:

```bash
python3 .claude/skills/research-workflow/scripts/priority-audit.py --recount
```

When a task reveals a dependency or gap not yet in the file, add it immediately — don't wait
until the end of the session.

### Blast-radius scan procedure

**Always use `.claude/skills/research-workflow/scripts/blast-radius.py`** to compute blast radius — never estimate by
memory. Run this whenever assigning or updating a priority: when adding a new topic,
after writing a new output file, or when reviewing whether stored priorities are current.

```bash
# Assign priority to a new topic — provide its most specific keywords
python3 .claude/skills/research-workflow/scripts/blast-radius.py Keycloak realm "LDAP sync"

# Single RFC topic
python3 .claude/skills/research-workflow/scripts/blast-radius.py "RFC 8693" "token exchange"

# snake_case identifier
python3 .claude/skills/research-workflow/scripts/blast-radius.py amsc_project_context "project context"
```

Output includes: match count, priority tier, full affected file list, and a ready-to-paste
`notes` column snippet.

**Periodically audit all priorities** with `.claude/skills/research-workflow/scripts/priority-audit.py`. Run after any session
where multiple new output files were written — new files change the blast radius of existing
topics without those topics' notes being updated.

```bash
# Fast check: counts backtick file references stored in notes column
python3 .claude/skills/research-workflow/scripts/priority-audit.py

# Authoritative check: re-greps live files against stored notes file stems
python3 .claude/skills/research-workflow/scripts/priority-audit.py --recount

# Fix mismatches automatically (writes .bak before touching TOPICS.md)
python3 .claude/skills/research-workflow/scripts/priority-audit.py --fix
python3 .claude/skills/research-workflow/scripts/priority-audit.py --recount --fix
```

When the audit flags mismatches:
- **Computed > Stored** — new output files have raised the blast radius; update the priority
  and add the new files to the notes column
- **Computed < Stored** — the notes may be stale, or the topic was assigned P1 due to
  "blocking a deployment path" (a non-count criterion); verify before downgrading

The `--fix` flag handles count-based corrections automatically. Manual review is still
needed for topics whose priority was justified by deployment-path blocking rather than
pure reference count.

---

## Repository Layout

| Directory / File | Purpose | Written by |
|-----------|---------|------------|
| `source/` | Verbatim primary documents — specs, upstream materials, ground-truth inputs placed here by the user | **User only — never Claude** |
| `concepts/` | Distilled, neutral descriptions of technologies, tools, protocols, and standards | Claude (catalogue mode) |
| `reports/` | Opinionated analysis and recommendations applied to the project's context | Claude (report mode) |
| `charges/` | Synthesis answer documents — one per charge question; collate findings from `concepts/` and `reports/` to answer the question directly | Claude (charge mode) |
| `CHARGE.md` | The research brief — the set of questions this project is intended to answer, each linked to its answer document in `charges/` | **User-defined (Claude maintains links)** |
| `_scratch/` | Temporary research checkpoints; deleted after output files are written | Claude (transient) |
| `_cache/` | Cleaned, persisted web fetch content — reused across sessions and subagents to avoid re-fetching | Claude (persistent until stale) |

---

## Charges — Synthesis Layer

`CHARGE.md` and `charges/` form a fourth tier above `reports/` and `concepts/`. They exist
to answer the question: *given everything we now know, what is the answer to the original
research question?*

### The four-tier reading path

```
CHARGE.md        ← the questions  (what are we trying to answer?)
charges/         ← synthesised answers  (what did we find, in plain terms?)
reports/         ← detailed analysis  (why, with evidence and citations)
concepts/        ← factual reference  (what is this thing?)
```

Charge files are **the entry point for decision-makers** who do not want to read every report.
A reader who only reads `charges/` should understand the state of the research, the
recommendation, and the key residual open questions — with links into `reports/` for depth.

### `CHARGE.md` — the research brief

`CHARGE.md` is user-defined. It contains the broad questions the research is expected to
answer, grouped by theme, each linking to its answer document in `charges/`. Questions are
intentionally broad — each one may be answered by synthesising multiple reports and concepts.

Claude maintains the links in `CHARGE.md` (adding `(charges/charge-NN.md)` when a new
charge file is created) but **never rewrites or reorders the questions themselves** — that
is the user's prerogative.

### `charges/` — answer documents

Each charge file answers one question from `CHARGE.md`. It is a **synthesis document**, not
new research. It:

1. **Reads across `concepts/` and `reports/`** to collate the relevant findings
2. **States a direct answer** to the charge question — not "it depends" without follow-up
3. **Cites evidence** with inline `[→ report-slug.md §section-name]` references
4. **Identifies residual open questions** — what is still unknown or unresolved

Charge files are the *most opinionated* output in the repository. Where reports hedge or
present options, charge files commit to an answer based on the weight of evidence.

### Charge file structure

Load `references/templates/charge.md` as the file template.

**Status values:**

| Status | Meaning |
|--------|---------|
| `Answered` | A clear, defensible answer exists based on research to date |
| `Partial` | An answer exists for the main thrust but one or more sub-questions remain open |
| `Open` | Insufficient research to answer; records what is known and what is needed |

### When to write or update a charge file

Write or update a charge file when:

- A new report is written that directly answers or changes the answer to a charge question
- A charge is explicitly requested: *"answer charge 3"* or *"update charge 7 given the new report"*
- A charge status needs to change (e.g. from `Partial` to `Answered` after a gap is resolved)

Do **not** automatically update all charge files every time a new report is written — only
update the charges materially affected by the new finding.

### Charge mode — how to work a charge

**Trigger:** User says *"answer charge N"*, *"update charge N"*, *"write up charge N"*, or
*"what does the research say about [question]?"* where the question maps to a charge.

**Workflow:**

1. Read `CHARGE.md` — identify the charge question and its number
2. Read the existing `charges/charge-NN.md` if it exists — understand current status and its `Generated` date
3. **Freshness check** — for every report or concept cited as a primary source in the existing charge file:
   - Check its `Generated` / `Amended` date against the charge's `Generated` date
   - If any source was **amended after the charge was last written**, flag it:
     > ⚠️ **Charge drift: `charge-NN.md`**
     > *Source amended after charge was written:* `reports/<slug>.md` (amended YYYY-MM-DD, charge written YYYY-MM-DD)
     > *Action:* re-read the amended section and determine whether the charge answer or confidence needs updating
   - If no sources have been amended since the charge was written, note "Sources current — no drift detected"
4. **Read all reports and concepts cited as primary sources** for this charge (in parallel)
5. **Scan for newly relevant files** — `ls reports/` and `ls concepts/`, skim `README.md`
   for any output written since the charge was last updated that bears on the question
6. Write the answer: commit to a position, cite evidence with `§section` references,
   list residual open questions
7. Update `CHARGE.md` — add or refresh the link to the charge file

**No external research in charge mode.** Charge files synthesise existing `concepts/` and
`reports/` — they do not originate new research. If the charge cannot be answered from
existing output, record it as `Open` and add the missing research as a `todo` in `TOPICS.md`.

### Evidence citation format

```
[→ report-slug.md §Section Title]
```

Direct quotes use standard Markdown blockquotes:

```markdown
> "The connector doesn't support refresh tokens since the SAML 2.0 protocol doesn't provide
> a way to requery a provider without interaction." [→ dex-integration.md §1.3]
```

### Charge files and README.md

Charge files are **not listed in README.md's reports table**. `README.md` indexes `concepts/`
and `reports/`. Charge files are navigated via `CHARGE.md`.

The README should include a reading-path entry pointing at `CHARGE.md` as the
management-level entry point:

```markdown
**"I need a management-level summary of what the research concluded"**
→ `CHARGE.md` — browse the questions; each links to its synthesis answer
→ follow `Primary sources` links in each charge for detailed evidence
```

---

### `source/` — Primary Source Documents

`source/` contains **verbatim originals** — documents that arrived from outside this research
process and are treated as ground truth.

**Rules for `source/`:**
- **Never write to, edit, or delete files in `source/`** — it is user-managed.
- When researching, **always read relevant source files first** before fetching external material.
  They are the highest-authority input; external web research fills gaps they leave open.
- When a concept entry or report contradicts a source file, **flag the discrepancy explicitly**
  rather than silently resolving it.
- Cite source files inline as: `source/<filename>.md §<section>` — not as a URL.

---

### `_cache/` — Persisted Web Fetch Content

`_cache/` stores cleaned web fetch output — content retrieved from external URLs, stripped of noise, and written to disk for reuse across sessions and subagents. See [`SUBAGENT-GUIDE.md`](./SUBAGENT-GUIDE.md) for the cache-first fetch protocol, data cleaning rules, staleness policy, and hygiene guidance.

---

## Output Conventions

### Concepts (`concepts/`)

Concept files capture **what a thing is** — its spec, architecture, known behaviour, quirks,
and fit with the project. They are reference material, not opinions.

**Filename**: `<kebab-slug>.md`

**Required structure**:

Load `references/templates/concept.md` as the file template.

**Survey documents** (multiple items side-by-side) may use a numbered section hierarchy
(`## 1.`, `### 2.1`) and comparison tables instead of the single-entry template. Still
required: frontmatter blockquote, confidence line, Relevance section, Sources section.

**Existing concept files that lack the `*Generated / Confidence*` line** should have it
added as part of any amendment — prepend it immediately after the frontmatter blockquote,
before the first `---` separator.

**Keywords field** — every concept file must include `**Keywords:**` in its frontmatter
blockquote. Populate it with acronyms, synonyms, abbreviations, and adjacent terms that
someone might search for when looking for this concept (e.g. `OIDC, OpenID Connect, OAuth2
identity layer` for a Keycloak concept). This is the primary index used by `blast-radius.py`
to discover cross-file relationships — richer keywords = better blast-radius coverage.

**Status field** — every concept file must include `**Status:**` in its frontmatter blockquote:

| Value | Meaning | Re-verify interval |
|-------|---------|-------------------|
| `stable` | Settled spec or standard; unlikely to change (e.g. an RFC) | 24 months |
| `evolving` | Active product, library, or practice; releases change behaviour | 6 months |
| `deprecated` | Superseded or end-of-life; kept for historical reference | No re-verify needed |

At session start, flag any concept whose `researched` date exceeds its re-verify interval:

> ⚠️ **Stale: `<concept-slug>`**
> *Status:* evolving · *Last researched:* YYYY-MM-DD · *Due for re-verify*
> *Action:* add `todo` amendment row to TOPICS.md, or re-verify now if session topic depends on it

**Existing concept files that lack the `**Status:**` field** should have it added as part of
any amendment — infer from context (most RFCs → `stable`; most vendor tools → `evolving`).

### Reports (`reports/`)

Report files capture **what you think / recommend** — synthesis, analysis, decision support.
Opinionated, cited, addressed to the project team.

**Filename**: `<topic-slug>.md`

**Required structure**:

Load `references/templates/report.md` as the file template.

Section titles are flexible — use whatever fits the content. Required fixed anchors:
**Executive Summary**, **Recommendations** (or equivalent), **Open Questions**, **Sources**.

**Keywords field** — every report file must include `**Keywords:**` in its frontmatter
blockquote. Include the main topic terms, any tools/protocols/standards discussed, and
alternative names or abbreviations used in the body. This widens `blast-radius.py`'s net
when searching for downstream impact.

---

## Parallelism & Subagent Coordination

**Always parallelise by default.** Research tasks are embarrassingly parallel — most fetches, reads, and sub-topic investigations have no dependency on each other. Serialising them wastes time and burns context on waiting.

Spawn subagents whenever tasks have multiple independent sub-topics. Tree depth is capped at 2 levels. Each subagent writes its own `_scratch/<topic>.md` before returning — never a bare return. Live-poll running subagents and emit a status table after each pass.

See [`SUBAGENT-GUIDE.md`](./SUBAGENT-GUIDE.md) for the complete reference: parallelism patterns, agent tree depth limits, batching strategy (≤3–4 items per subagent), live status reporting format, scratch file handoff protocol, subagent context budget rules, and cache-first fetch protocol.


---

## Confidence Tracking

State a confidence level on every document:
- **High** — primary sources (spec pages, RFCs, official docs)
- **Medium** — mixed (primary + secondary)
- **Low** — mostly inferred or indirect

Include the method in parentheses, e.g. `High (RFCs + official docs)`, `Medium (docs + WebSearch)`.

---

## Epistemic Standards — Tone, Accuracy, and Corroboration

This skill deals in **facts, not stories**. Every output should read like a precise technical
reference, not a narrative summary. The following standards are non-negotiable.

### Tone

- **Flat and precise.** No filler phrases ("it is worth noting", "importantly", "in conclusion").
  State the fact, cite it, move on.
- **No hedging without cause.** If a claim is well-sourced, assert it directly. Reserve
  qualifiers ("appears to", "may", "reportedly") for genuinely uncertain claims — and pair
  them with a confidence note explaining why.
- **No editorialising.** Concept files are purely descriptive. Opinions and recommendations
  belong only in reports, clearly labelled as such.
- **Audience is a domain expert.** Do not over-explain fundamentals. Be terse.

### Corroboration before assertion

A claim is not ready to write until it is corroborated:

| Claim type | Minimum corroboration |
|---|---|
| Protocol behaviour / RFC requirement | Primary spec or RFC text (direct quote or section cite) |
| Version / release fact | Official changelog, release notes, or project page |
| Vendor capability claim | Vendor docs + at least one independent source (issue tracker, blog, test report) |
| Security property or CVE | CVE record + advisory + vendor patch confirmation |
| "Not supported" / "missing" claim | Verified by checking docs AND issue tracker — absence of docs alone is not proof |

If a second source cannot be found, **lower the confidence level** and say so explicitly.
Do not assert as fact what is only claimed by one source.

### Source hierarchy

Prefer sources in this order — never cite a lower tier if a higher one is available:

1. **Primary spec** — RFC text, W3C spec, official schema, source code
2. **Official docs** — vendor documentation, project README, release notes
3. **Authoritative secondary** — IETF working group notes, CVE database, peer-reviewed paper
4. **Community secondary** — GitHub issues, mailing lists, Stack Overflow (cite with caution)

### Model selection

> Configure your preferred model names in settings — these are environment-specific.

Use a **high-capability model (e.g. opus tier)** for:
- Any task requiring synthesis across many sources
- Security analysis, CVE assessment, or compliance gap analysis
- Reports where recommendations will inform architectural decisions
- Any situation where a previous attempt produced a confidence level of Medium or below

Use a **fast model (e.g. sonnet tier)** for:
- Straightforward single-source concept entries (e.g. cataloguing a well-documented RFC)
- Index and README updates
- Scratch file checkpoints

When launching subagents, **assign model explicitly** — research subagents doing multi-source
synthesis should use a high-capability model (e.g. opus tier); subagents doing mechanical tasks (writing a file from notes already
gathered) can use a fast model (e.g. sonnet tier).

### What to do when sources or information conflict

If two sources of information contradict each other:
1. Prefer the primary spec over any secondary source
2. If both are secondary, note the conflict explicitly in the output:
   > ⚠️ **Conflicting sources:** [Source A] states X; [Source B] states Y. Unable to resolve
   > from available evidence — marked Low confidence pending primary source verification.
3. Never silently pick one — always surface the conflict to the reader.

---

## Workflow

### Step 1 — Determine mode

**Catalogue mode** when the topic is a specific technology, RFC, tool, standard, or protocol,
or the user says "catalogue / document / what is / how does X work".

**Report mode** when the topic is a question, recommendation, decision, or comparison, or the
user says "report / should we / viability / compare / roadmap".

**Charge mode** when the user says "answer charge N", "update charge N", "write charge N",
or asks a question that maps directly to a numbered charge in `CHARGE.md`. Charge mode reads
existing `concepts/` and `reports/` only — it does not fetch external sources.

When in doubt, ask: *"Should I catalogue this as a reference entry, write a recommendation report, or synthesise an answer to a charge question?"*

### Step 2 — Check for existing files

Before creating anything:
1. Read `TOPICS.md` — is this topic already tracked? update its status to `in-progress`
2. `ls source/` — read any relevant source documents first (ground truth)
3. `ls concepts/` — existing catalogue entry?
4. `ls reports/` — existing relevant report?
5. Read `README.md` — understand what is already covered

If a relevant file exists, **amend it** rather than creating a duplicate:
- Append an `## Amendment YYYY-MM-DD — <reason>` section at the end of the file
- Update the README row status to `Amended YYYY-MM-DD (<reason>)`

### Step 3 — Research

- **Read `source/`** first — highest-authority inputs; understand what they say before going external
- **Check `_cache/`** before any WebFetch — use a fresh cached entry rather than re-fetching (see Cache-first fetch protocol)
- **Lateral read before deep read** — before investing a full WebFetch on any external source, spend one search vetting it: who wrote it, what is their affiliation or incentive, is it primary spec or secondary commentary? Downweight or skip sources that fail this check. This prevents low-credibility sources from shaping the output.
- **WebFetch** primary sources first (RFCs, spec pages, official docs) — these are tier-1 and tier-2 sources;
  write each result to `_cache/` (cleaned) immediately after fetching
- **Corroborate** every non-trivial claim with a second source before writing it down (see Epistemic Standards)
- **WebSearch** for version history, CVEs, and recent changes — use to validate or challenge what primary sources say
- **Read** prior `concepts/` and `reports/` files for context already established
- Invoke **`/research`** for broad multi-source investigations — it handles parallel subagents, lateral source vetting, adversarial pass, and synthesis; assign it a high-capability model (e.g. opus tier)

### Step 4 — Write the file

- Every factual claim gets a source link or inline citation
- **Per-claim confidence** — for key claims, label confidence inline rather than relying solely on the document-level confidence line:
  - `*High — RFC text*`, `*Medium — two secondary sources*`, `*Low — single blog post, unverified*`
  - Reserve Low-confidence claims for cases where no better source was found; pair with a note on what would raise it
- State a document-level confidence level with method on every file (High/Medium/Low + sources used)
- Fenced code blocks for JSON/YAML/config with inline `//` comments
- Tables for comparisons and compatibility matrices
- Tone: technical, precise, direct — audience is a domain expert on this project
- Cross-link bidirectionally: concept files list `Applied in` reports; reports list `Concept References`
- **Populate `**Keywords:**`** in the frontmatter blockquote — acronyms, synonyms, alternative names,
  and adjacent terms that someone might search for. This is the index `blast-radius.py` uses to
  find cross-file relationships; omitting it means the file is invisible to future blast-radius scans.

**For reports: adversarial challenge before writing Recommendations**

Before committing recommendations to disk, run a self-adversarial pass:

1. List the 3–5 key premises the recommendations rest on
2. For each premise: what is the strongest counter-argument or failure mode?
3. Are there known practitioners, posts, or issues that contradict the conclusion?
4. Would the recommendation change under different constraints (scale, team size, compliance regime)?

If any challenge is material, either: (a) strengthen the claim with corroborating evidence, (b) lower its confidence label, or (c) add it to **Open Questions**. Never leave a material challenge unaddressed.

**Open Questions must be escalated to TOPICS.md**

Every item in a report's Open Questions section that is not resolved in the same session must be captured as a `todo` row in `TOPICS.md` immediately after the file is written — before moving to Step 5. Use the report filename in the notes column as the dependency:

> `| 🔹 P3 | 🔲 todo | concept | <topic> | — | Open question from reports/<slug>.md: <question text> |`

Run `blast-radius.py` on the new topic before assigning its priority. Do not leave Open Questions as dead-ends in the report without a corresponding queue entry.

### Step 5 — Update the index

Open `README.md` and:

- **New report**: add a row to the reports table (`New YYYY-MM-DD`)
- **New concept entry**: add/update the concepts table row with filename, subject, and date
- **Amendment**: update the existing row's status to `Amended YYYY-MM-DD (reason)`

Then update `TOPICS.md`:

- **Remove** the completed topic row entirely
- Add any follow-on topics or newly discovered gaps as `todo` rows — run `blast-radius.py` on each new topic before assigning its priority
- If a blocker was encountered, update status to `blocked` with a reason

**Post-output suggestion pass** — after every new concept or report, before running
`priority-audit.py`, apply the lenses below to the file just written and surface any
candidates not already in `TOPICS.md`. Present as a checklist; user promotes or dismisses.

| Lens | What to generate |
|------|-----------------|
| **Adversarial** | A `steelman` report that argues the opposite conclusion, or a report on the most likely failure mode of this recommendation |
| **Dependency gap** | Concepts or standards referenced in this file that have no entry in `concepts/` yet |
| **Outside-in** | What a regulator, an attacker, or an end-user would ask after reading this that the file doesn't answer |
| **Contrarian** | A known dissenting view or alternative approach not covered — worth a concept or report of its own? |
| **Simplification** | Is there a simpler alternative the file implicitly rules out without explicitly evaluating? |
| **Temporal** | If the file's `Status` is `evolving`, flag a re-verify reminder as a `deferred` TOPICS.md entry dated 6 months out |

Keep the checklist to 3 items maximum — prioritise the highest-signal suggestions.

- **Run `priority-audit.py --recount` after writing any new output file** — it detects TOPICS.md items whose blast radius has grown, so their priority and notes can be updated in one pass:

```bash
python3 .claude/skills/research-workflow/scripts/priority-audit.py --recount
# apply fixes automatically:
python3 .claude/skills/research-workflow/scripts/priority-audit.py --recount --fix
```

---

## Context Management

The primary defence against context overflow is **parallelism** — subagents each get their own context window so the parent never accumulates their research. Write raw findings to `_scratch/<topic>-raw.md` BEFORE formatting any final document. Never return from a subagent without having written to disk.

See [`SUBAGENT-GUIDE.md`](./SUBAGENT-GUIDE.md) for: Step 0 scratch file protocol, chunked execution rules, and the subagents-vs-scratch decision table.


---

## Tips

- When cataloguing an RFC: always include Published date, Authors, Status, and a wire format
  section with a JSON/YAML example.
- When a report references a catalogued concept, link to it:
  `See [concept entry](../concepts/slug.md)`.
- If deep research is needed across many sources, invoke `/research` first, then layer in
  project-specific framing.
- Never create a file without first checking both output directories for duplicates.
- Draft RFC/spec citations: pin the version number, not just a generic name.
- Add `— fetched YYYY-MM-DD` to each Sources entry so staleness is trackable.

---

## Programmatic Tool Calling

Load `references/ptc-patterns.md` for the full three-technique PTC reference (tool search, batched Python queries, examples array usage). Technique 2 is the most important: write Python to batch multiple tool calls and keep intermediate results off-context.
