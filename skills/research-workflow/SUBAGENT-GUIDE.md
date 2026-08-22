# Research Workflow — Subagent & Context Guide

Reference guide for parallelism patterns, subagent coordination, scratch file protocol,
context management, and web cache. Used by `research-workflow` and any skill that spawns
research subagents.

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

Even for a single concept or report, parallelise the fetch phase:

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

---

## Live Status Reporting While Subagents Run

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

## Subagent Output → Scratch File Handoff

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
1. Check `_cache/` for each URL you intend to fetch — use cached content if fresh (see Cache-first fetch protocol below)
2. Execute only the reads and fetches that are in scope for this subagent's assigned topic;
   write each fetch result to `_cache/` (cleaned) immediately after fetching
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

## `_cache/` — Persisted Web Fetch Content

`_cache/` stores **cleaned web fetch output** — content retrieved from external URLs,
stripped of noise, and written to disk so it can be reused by the same or a different
subagent in a later session without re-fetching.

### Filename convention

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

### Cache-first fetch protocol

**Before every WebFetch call**, check whether a fresh cache entry exists:

1. `ls _cache/ 2>/dev/null` — list existing entries
2. Look for a file matching `<slug>--*.md`
3. If found, check the date suffix:
   - **≤ 7 days old** for volatile sources (CVE databases, changelogs, blog posts) → **use cache**
   - **≤ 30 days old** for stable sources (RFCs, spec pages, official docs) → **use cache**
   - **Older** → re-fetch and overwrite the cache entry
4. If not found → fetch, clean, and write to cache before using

Announce cache hits briefly: `"Using cached _cache/rfc8693--2026-03-15.md (5 days old)"`

### Data cleaning — strip before caching

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

### Staleness and invalidation

- Cache files are **never deleted automatically** — they persist until manually cleared or overwritten by a re-fetch.
- A re-fetch overwrites the existing cache file (same slug, new date in filename — delete the old file, write the new one).
- **Never read a cache file without checking its date suffix.** A 6-month-old CVE cache entry is actively dangerous — it may be missing patches or updated severity scores.
- If a cache file is stale but you cannot re-fetch (e.g. network unavailable), use it and note the staleness explicitly in your scratch file and output.

### Cache hygiene

Cache files are **not indexed in README.md** and not referenced in `TOPICS.md`. They are
an implementation detail of the fetch layer.

After a research project is fully complete and all output files are written, the cache
may be cleared:

```bash
rm -rf _cache/
```

But unlike `_scratch/`, do not delete `_cache/` automatically — it has cross-session value.
Only clear it when explicitly asked or when you are certain the project is complete.
