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

**During any conversation**, capture new topics to TOPICS.md immediately when they surface — gaps, dependencies, deferred decisions, technologies mentioned without a concept entry. One-line acknowledgement, don't interrupt the flow.

**Context window**: research sessions accumulate context quickly. Use `/compact` between major tasks (after a concept file is written and before starting the next topic) to keep the context window healthy. The `strategic-compact` skill can suggest good compaction points if active.

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
python3 .claude/skills/research-workflow/tools/blast-radius.py <keyword> [keyword2 ...]
```

**When a new output file is written** (Step 5), run `priority-audit.py` to detect
any existing TOPICS.md items whose blast radius has grown due to the new file, and
update their reference count, affected files list, and priority as needed:

```bash
python3 .claude/skills/research-workflow/tools/priority-audit.py --recount
```

When a task reveals a dependency or gap not yet in the file, add it immediately — don't wait
until the end of the session.

### Blast-radius scan procedure

**Always use `.claude/skills/research-workflow/tools/blast-radius.py`** to compute blast radius — never estimate by
memory. Run this whenever assigning or updating a priority: when adding a new topic,
after writing a new output file, or when reviewing whether stored priorities are current.

```bash
# Assign priority to a new topic — provide its most specific keywords
python3 .claude/skills/research-workflow/tools/blast-radius.py Keycloak realm "LDAP sync"

# Single RFC topic
python3 .claude/skills/research-workflow/tools/blast-radius.py "RFC 8693" "token exchange"

# snake_case identifier
python3 .claude/skills/research-workflow/tools/blast-radius.py amsc_project_context "project context"
```

Output includes: match count, priority tier, full affected file list, and a ready-to-paste
`notes` column snippet.

**Periodically audit all priorities** with `.claude/skills/research-workflow/tools/priority-audit.py`. Run after any session
where multiple new output files were written — new files change the blast radius of existing
topics without those topics' notes being updated.

```bash
# Fast check: counts backtick file references stored in notes column
python3 .claude/skills/research-workflow/tools/priority-audit.py

# Authoritative check: re-greps live files against stored notes file stems
python3 .claude/skills/research-workflow/tools/priority-audit.py --recount

# Fix mismatches automatically (writes .bak before touching TOPICS.md)
python3 .claude/skills/research-workflow/tools/priority-audit.py --fix
python3 .claude/skills/research-workflow/tools/priority-audit.py --recount --fix
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

```markdown
# Charge N: <verbatim question from CHARGE.md>

> **Status:** Answered | Partial | Open
> **Primary sources:** `reports/foo.md`, `reports/bar.md`, `concepts/baz.md`

## Answer

[2–5 sentence direct answer to the charge question. State a position. Cite reports inline
as [→ slug.md §section]. Do not hedge unless the evidence is genuinely ambiguous — in that
case, state why it is ambiguous and what would resolve it.]

## Evidence

### <Report or concept title> — `<filename>`

- **Key finding:** "[direct quote or tight paraphrase]" (§section-name)
- **Key finding:** "[direct quote or tight paraphrase]" (§section-name)
[…repeat for each primary source; omit sources that add no new evidence for this charge]

## Residual Open Questions

1. [Specific unresolved question — what decision or information would close it]
2. …
```

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
2. Read the existing `charges/charge-NN.md` if it exists — understand current status
3. **Read all reports and concepts cited as primary sources** for this charge (in parallel)
4. **Scan for newly relevant files** — `ls reports/` and `ls concepts/`, skim `README.md`
   for any output written since the charge was last updated that bears on the question
5. Write the answer: commit to a position, cite evidence with `§section` references,
   list residual open questions
6. Update `CHARGE.md` — add or refresh the link to the charge file

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

`_cache/` stores **cleaned web fetch output** — content retrieved from external URLs,
stripped of noise, and written to disk so it can be reused by the same or a different
subagent in a later session without re-fetching.

#### Filename convention

```
_cache/<slug>--<YYYY-MM-DD>.md
```

Where `<slug>` is derived from the URL: take the hostname + path, replace `/`, `.`, `?`, `=`
with `-`, collapse runs of `-`, truncate to 60 characters.

Examples:
```
_cache/datatracker-ietf-org-doc-html-rfc8693--2026-03-20.md
_cache/keycloak-org-docs-latest-server-admin--2026-03-20.md
_cache/nvd-nist-gov-vuln-detail-CVE-2024-1234--2026-03-20.md
```

The date in the filename is the **fetch date** — used to determine staleness.

#### Cache-first fetch protocol

**Before every WebFetch call**, check whether a fresh cache entry exists:

1. `ls _cache/ 2>/dev/null` — list existing entries
2. Look for a file matching `<slug>--*.md`
3. If found, check the date suffix:
   - **≤ 7 days old** for volatile sources (CVE databases, changelogs, blog posts) → **use cache**
   - **≤ 30 days old** for stable sources (RFCs, spec pages, official docs) → **use cache**
   - **Older** → re-fetch and overwrite the cache entry
4. If not found → fetch, clean, and write to cache before using

Announce cache hits briefly: `"Using cached _cache/rfc8693--2026-03-15.md (5 days old)"`

#### Data cleaning — strip before caching

Raw WebFetch output contains significant noise that wastes context tokens. **Before writing
to `_cache/`, apply this cleaning pass:**

Strip the following patterns:
- Navigation blocks: repeated link lists at the top/bottom, breadcrumb trails, sidebar menus
- Cookie banners, GDPR notices, "Accept cookies" boilerplate
- Headers/footers that repeat on every page (copyright lines, social links, "Back to top")
- Duplicate content: if a block of ≥5 lines appears more than once, keep only the first occurrence
- Empty sections: headings with no content beneath them before the next heading
- Inline ads and tracking pixel markup (common in WebFetch output from blog-style sites)
- RFC datatracker boilerplate: the standard header block (document status, IPR, copyright
  notice) is truncated to the first 5 lines — the rest is noise for most research tasks

**Preserve:**
- All substantive prose, code blocks, tables, and lists
- Section headings (they provide structure)
- The abstract / executive summary if present
- All URLs and references in the Sources or References section

**Record what was cleaned** — append a one-line metadata footer to every cache file:

```
<!-- cached: 2026-03-20 | original: ~18400 chars | cleaned: ~6200 chars | stripped: nav, footer, boilerplate -->
```

This makes token savings visible and lets a reader know the file is not verbatim.

#### Staleness and invalidation

- Cache files are **never deleted automatically** — they persist until manually cleared or overwritten by a re-fetch.
- A re-fetch overwrites the existing cache file (same slug, new date in filename — delete the old file, write the new one).
- **Never read a cache file without checking its date suffix.** A 6-month-old CVE cache entry is actively dangerous — it may be missing patches or updated severity scores.
- If a cache file is stale but you cannot re-fetch (e.g. network unavailable), use it and note the staleness explicitly in your scratch file and output.

#### Cache hygiene

Cache files are **not indexed in README.md** and not referenced in `TOPICS.md`. They are
an implementation detail of the fetch layer.

After a research project is fully complete and all output files are written, the cache
may be cleared:

```bash
rm -rf _cache/
```

But unlike `_scratch/`, do not delete `_cache/` automatically — it has cross-session value.
Only clear it when explicitly asked or when you are certain the project is complete.

---

## Output Conventions

### Concepts (`concepts/`)

Concept files capture **what a thing is** — its spec, architecture, known behaviour, quirks,
and fit with the project. They are reference material, not opinions.

**Filename**: `<kebab-slug>.md`

**Required structure**:

```markdown
# <Full Name>

> **Type:** Concept Reference
> **Applied in:** [Report Title](../reports/slug.md), …

*Generated: YYYY-MM-DD | Confidence: High/Medium/Low (<method>)*

---

## 1. What It Is
[1–3 sentence plain-English description]

## 2. How It Works
[Architecture, data flow, key mechanisms — use diagrams/code blocks as needed]

## 3. Key Facts

| Fact | Detail |
|------|--------|
| Spec / RFC | … |
| Current version | … |
| Maturity | … |
| Language / runtime | … |
| License | … |

## 4. Relevance to This Project
[How this connects to the project's core problems or goals — use sub-headings if needed]

## 5. Known Gaps / Limitations
[Sharp edges, things it does NOT do, open issues, CVEs if relevant]

## Sources
- [Name](URL) — fetched YYYY-MM-DD
```

**Survey documents** (multiple items side-by-side) may use a numbered section hierarchy
(`## 1.`, `### 2.1`) and comparison tables instead of the single-entry template. Still
required: frontmatter blockquote, confidence line, Relevance section, Sources section.

**Existing concept files that lack the `*Generated / Confidence*` line** should have it
added as part of any amendment — prepend it immediately after the frontmatter blockquote,
before the first `---` separator.

### Reports (`reports/`)

Report files capture **what you think / recommend** — synthesis, analysis, decision support.
Opinionated, cited, addressed to the project team.

**Filename**: `<topic-slug>.md`

**Required structure**:

```markdown
# <Title>

> **Type:** Report
> **Concept References:** [Concept Name](../concepts/slug.md), …
> **See also:** [Report Title](../reports/slug.md), …

*Generated: YYYY-MM-DD | Confidence: High/Medium/Low (<method>)*

---

## Executive Summary
[2–4 sentences: problem, finding, recommendation]

---

## Part 1: <Background Section Title>
[Context — what triggered this, which problem it addresses]

## Part 2: <Analysis Section Title>
[Detailed findings with tables, code blocks, comparisons]

## Part 3: <Recommendations Section Title>
1. **<Action>** — <rationale>

## Open Questions
- …

## Sources
- [Name](URL) — fetched YYYY-MM-DD
```

Section titles are flexible — use whatever fits the content. Required fixed anchors:
**Executive Summary**, **Recommendations** (or equivalent), **Open Questions**, **Sources**.

---

## Parallelism — Default Mode of Operation

**Always parallelise by default.** Research tasks are embarrassingly parallel — most fetches,
reads, and sub-topic investigations have no dependency on each other. Serialising them wastes
time and burns context on waiting.

### Use subagents for independent research branches

Spawn parallel subagents whenever a task has multiple independent sub-topics:

```
User: "catalogue OAuth 2.0 token exchange and device flow"
→ Launch two subagents simultaneously:
    • subagent A: researches RFC 8693 (token exchange)
    • subagent B: researches RFC 8628 (device flow)
→ Each subagent writes its own scratch file, returns a brief summary
→ Parent reads scratch files, writes both concept files, updates README
```

Subagents keep their findings isolated — each gets its own context window, so neither
pollutes the other's research or risks overflowing the parent context.

### Agent tree depth limit — max 2 levels

Subagents may spawn their own sub-subagents if their assigned scope is too large to
research in a single context. The tree is capped at **2 levels deep**:

```
parent (level 0)
└── subagent (level 1)
    └── sub-subagent (level 2) — leaf only, no further spawning
```

**Level 2 agents are leaves.** They fetch, read, and write a scratch file — they never
spawn further agents. If a level-2 agent finds its scope is still too large, it should
narrow its focus and note the gap in its scratch file rather than spawning deeper.

**Scratch file naming by depth:**

```
_scratch/<topic>-<subtopic>.md          # level-1 subagent
_scratch/<topic>-<subtopic>-<detail>.md # level-2 sub-subagent
```

**Decision rule for subagents** — spawn a sub-subagent only when ALL of these are true:
1. The assigned scope covers ≥3 independent items that each require multiple fetches
2. You are at level 1 (not already a subagent of a subagent)
3. The items are genuinely independent (no data dependency between them)

If scope is large but items are sequential or interdependent, chunk them serially within
your own context rather than spawning.

### Parallelise within a single topic too

Even for a single concept or report, parallelize the fetch phase:

```
→ WebFetch spec page         ┐
→ WebFetch RFC datatracker   ├─ all fired simultaneously
→ WebSearch recent CVEs      │
→ Read relevant source/files ┘
→ synthesise once all return
```

Never fetch URL 2 after URL 1 returns if they are independent. Fire them all at once.

### What to serialise

Only serialise when there is a true data dependency:

| Serialise | Because |
|-----------|---------|
| Write `_scratch/` → write `concepts/` | formatted file depends on raw notes |
| Write `concepts/` → update `README.md` | index entry depends on file existing |
| Read `source/` → fetch external docs | external research should fill gaps source leaves, not overlap |

Everything else: **parallel**.

### Splitting large surveys into subagent batches

For a survey of N items (e.g. 8 IAM platforms), batch them:

```
Batch 1 (subagent): Keycloak, Authentik, Authelia  ┐ simultaneous
Batch 2 (subagent): Kanidm, Zitadel, Ory Stack     ┘
    each subagent writes _scratch/<topic>-<batch>.md before returning
→ parent reads both scratch files, writes concepts/<slug>.md
```

Rule of thumb: **≤3–4 items per subagent** to keep each subagent's context manageable.

### Live status reporting while subagents run

After launching background subagents, **poll continuously and emit a live status table**
after every polling pass so the user can see progress in real time.

1. Launch all subagents with `run_in_background: true`. Record each agent's task ID.

2. Enter a polling loop — call `TaskOutput(task_id, block: false)` for each agent that
   has not yet completed. After each pass, emit a status table:

```
⏳ Research in progress  (elapsed: Xs)
──────────────────────────────────────────────────────────────
Subagent             Status            Elapsed   Early signal
──────────────────────────────────────────────────────────────
token-exchange       ✅ complete       1m 12s    wrote _scratch/token-exchange.md
device-flow          ⏳ running        1m 12s    fetching RFC 8628…
mtls-binding         🔵 queued         —         —
──────────────────────────────────────────────────────────────
```

   Status values:
   - `🔵 queued`   — launched, no output yet
   - `⏳ running`  — partial output received (scratch file exists or partial TaskOutput)
   - `✅ complete` — TaskOutput returned final result

   Early signal: if the subagent's scratch file (`_scratch/<topic>.md`) already exists,
   read its last few lines to surface a signal — e.g. "wrote 42 lines", "fetching RFC…",
   "no CVEs found". Show this in the table.

3. Repeat immediately after rendering the table — no fixed sleep. Stop when all agents
   are `complete`.

4. Once all agents are complete, announce the summary before reading scratch files:

```
✅ All subagents complete — synthesising results
──────────────────────────────────────────────────────────────
token-exchange       ✅ complete   _scratch/token-exchange.md (38 lines)
device-flow          ✅ complete   _scratch/device-flow.md (51 lines)
mtls-binding         ✅ complete   _scratch/mtls-binding.md (29 lines)
──────────────────────────────────────────────────────────────
```

Then proceed to read all scratch files and write the final output.

---

### Subagent output → scratch file handoff

Each subagent **writes its own scratch file** before returning:

```
_scratch/<topic>-<subtopic-or-batch>.md
```

The subagent dumps all raw findings (bullet points, tables, URLs, notes) into that file,
then returns a brief summary to the parent confirming what was written and where.

The parent reads the scratch files to synthesise — it never holds raw research in its own
context. This means a context reset at any point loses at most one batch, not the whole
survey, and the parent context stays lean regardless of how much the subagents found.

### ⚠️ Subagent context budget warning

**Subagents have a limited context window.** Reading many existing `concepts/` and `reports/`
files for cross-references is the most common way subagents overflow before writing output.

**Hard rule:** A subagent that has been given source material in its prompt MUST NOT read
additional existing report files unless the prompt explicitly instructs it to. Cross-reference
links are written from memory / prompt context, not from re-reading files.

**Subagent task structure — always follow this order:**
1. Check `_cache/` for each URL you intend to fetch — use cached content if fresh (see Cache-first fetch protocol)
2. Execute only the reads and fetches that are in scope for this subagent's assigned topic;
   write each fetch result to `_cache/` (cleaned) before using it
3. **Write `_scratch/<topic>.md` immediately** — before any formatting, before any additional reads
4. Verify the scratch file exists (`wc -l _scratch/<topic>.md`)
5. Write the final `concepts/` or `reports/` file from the scratch file contents
6. Return a one-line summary: `"Wrote _scratch/<topic>.md (N lines) and reports/<slug>.md (M lines); cached N URLs"`

**If context is running low after step 2:** stop after writing the scratch file and return.
The parent will write the final file from the scratch. A scratch file on disk is never wasted.
**Never return "Now I'll write the report" without having written anything to disk.**

When the parent launches subagents for multi-topic batches, the prompt must include:
> "Write your findings to `_scratch/<topic>.md` BEFORE formatting the final report. This is
> mandatory — not optional. If you run out of context, the scratch file is the deliverable."

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

Use **copilot-claude-opus-4.6** for:
- Any task requiring synthesis across many sources
- Security analysis, CVE assessment, or compliance gap analysis
- Reports where recommendations will inform architectural decisions
- Any situation where a previous attempt produced a confidence level of Medium or below

Use **copilot-claude-sonnet-4.6** for:
- Straightforward single-source concept entries (e.g. cataloguing a well-documented RFC)
- Index and README updates
- Scratch file checkpoints

When launching subagents, **assign model explicitly** — research subagents doing multi-source
synthesis should use copilot-claude-opus-4.6; subagents doing mechanical tasks (writing a file from notes already
gathered) can use copilot-claude-sonnet-4.6.

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
- **WebFetch** primary sources first (RFCs, spec pages, official docs) — these are tier-1 and tier-2 sources;
  write each result to `_cache/` (cleaned) immediately after fetching
- **Corroborate** every non-trivial claim with a second source before writing it down (see Epistemic Standards)
- **WebSearch** for version history, CVEs, and recent changes — use to validate or challenge what primary sources say
- **Read** prior `concepts/` and `reports/` files for context already established
- Invoke **`deep-research`** for broad multi-source investigations; assign it copilot-claude-opus-4.6 for synthesis tasks

### Step 4 — Write the file

- Every factual claim gets a source link or inline citation
- State a confidence level with method on every file
- Fenced code blocks for JSON/YAML/config with inline `//` comments
- Tables for comparisons and compatibility matrices
- Tone: technical, precise, direct — audience is a domain expert on this project
- Cross-link bidirectionally: concept files list `Applied in` reports; reports list `Concept References`

### Step 5 — Update the index

Open `README.md` and:

- **New report**: add a row to the reports table (`New YYYY-MM-DD`)
- **New concept entry**: add/update the concepts table row with filename, subject, and date
- **Amendment**: update the existing row's status to `Amended YYYY-MM-DD (reason)`

Then update `TOPICS.md`:

- **Remove** the completed topic row entirely
- Add any follow-on topics or newly discovered gaps as `todo` rows — run `blast-radius.py` on each new topic before assigning its priority
- If a blocker was encountered, update status to `blocked` with a reason
- **Run `priority-audit.py --recount` after writing any new output file** — it detects TOPICS.md items whose blast radius has grown, so their priority and notes can be updated in one pass:

```bash
python3 .claude/skills/research-workflow/tools/priority-audit.py --recount
# apply fixes automatically:
python3 .claude/skills/research-workflow/tools/priority-audit.py --recount --fix
```

---

## Context Management — Avoiding Context-Window Failures

The primary defence against context overflow is **parallelism** (see above) — subagents
each get their own context window, so the parent never accumulates their research. The
scratch file protocol below is the secondary defence for when a single task is genuinely large.

### Step 0 — Persist raw findings BEFORE formatting

**This step is mandatory and non-negotiable.** No final output file may be written until
a scratch file exists on disk. A subagent that returns without writing anything to disk
has failed, regardless of how much context it consumed.

Before writing any final formatted document, dump all research findings to a scratch file.

**If you are a subagent** — write your findings immediately after research, before returning
to the parent:

```
_scratch/<topic>-<subtopic-or-batch>.md
```

**If you are the parent** working a single-context task (no subagents), write:

```
_scratch/<topic>-raw.md
```

In both cases: write everything — bullet points, tables, URLs, notes — in a single Write
tool call. This acts as a durable checkpoint. The parent reads scratch files rather than
holding raw findings in its own context.

**Failure mode to avoid:** reading all source material, then returning "Now I'll write the
report" — and then running out of context before the Write tool call. The scratch file
is the escape hatch. Write it before you run out of tokens, not after.

### Chunked execution rule

**One file per context segment.** The safe order is:

1. Write `_scratch/<topic>-raw.md` (raw notes — always first)
2. Write `concepts/<slug>.md` (formatted catalogue entry)
3. Write `reports/<slug>.md` (formatted report)
4. Edit `README.md` (index update)

Between each step, verify the previous file was written (`wc -l` or `ls`) before proceeding.
If context runs low after any step, stop — the work is safe on disk.

### Scratch file hygiene

Scratch files live in `_scratch/` — never in `concepts/` or `reports/`, never indexed in `README.md`.

After all derived files are written and verified, clean up:

```bash
rm _scratch/<topic>-raw.md
rmdir _scratch   # only if empty
```

Confirm the scratch contains nothing not already captured before deleting. If in doubt, keep it and ask.

### When to reach for subagents vs. scratch-file chunking

| Signal | Response |
|--------|----------|
| More than ~3 independent items to research | Subagent batches (parallel) |
| Research + two output files in one request | Subagents for research, scratch file before writing |
| Previous session ran out of context mid-write | Scratch file checkpoint + smaller subagent batches |
| Single topic but many sources to fetch | Parallel fetches within one context (no subagent needed) |
| Research output exceeds ~10,000 characters | Scratch file before formatting |

When reaching for subagents, tell the user: *"This is a large task — I'll split the research
across parallel subagents and checkpoint findings to `_scratch/` before writing output files."*

---

## Tips

- When cataloguing an RFC: always include Published date, Authors, Status, and a wire format
  section with a JSON/YAML example.
- When a report references a catalogued concept, link to it:
  `See [concept entry](../concepts/slug.md)`.
- If deep research is needed across many sources, invoke `deep-research` first, then layer in
  project-specific framing.
- Never create a file without first checking both output directories for duplicates.
- Draft RFC/spec citations: pin the version number, not just a generic name.
- Add `— fetched YYYY-MM-DD` to each Sources entry so staleness is trackable.
