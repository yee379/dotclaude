---
name: research-workflow
description: Manages all research output — cataloguing concepts, writing reports, and synthesising charge answers into source/, concepts/, reports/, and charges/ with bidirectional cross-linking and confidence tracking.
---

# research-workflow

Catalogue concepts and write recommendation reports for any research project.

| Mode | Trigger | Output |
|------|---------|--------|
| **Catalogue** a technology / standard / tool / concept | `/research-workflow catalogue <topic>` | `concepts/` |
| **Report** on a topic | `/research-workflow report <topic>` | `reports/` |
| **Charge** — synthesise existing research to answer a charge question | `/research-workflow charge <N>` or `answer charge N` | `charges/` |

The mode word is optional — describe what you want in plain English and the mode is inferred.
`README.md` and `TOPICS.md` at the project root are always kept up to date.

---

## Session start — every time, before anything else

1. **Read `TOPICS.md`** — the outstanding work queue. Note all `todo` items and call out **every**
   `blocked` item using the callout format below, unconditionally. If there are none, say *"No
   blocked items."* Do not silently skip this.
2. **Read `source/`** — scan for primary documents relevant to the topic.
3. **Check `README.md`** — orient to what already exists.
4. **Flag stale concepts** — any whose `researched` date exceeds its `Status` re-verify interval.

```
⚠️ **Blocked: `<topic>`**
*Reason:* <blocking reason from notes>
*Needs:* <what would unblock it — a decision, a missing source, a dependency topic>

⚠️ **Stale: `<concept-slug>`**
*Status:* evolving · *Last researched:* YYYY-MM-DD · *Due for re-verify*
*Action:* add a `todo` amendment row to TOPICS.md, or re-verify now if the session depends on it
```

Also surface a blocker mid-session the moment it becomes relevant — e.g. the user asks about a
topic whose dependency is blocked.

Then either work the topic the user named (capturing it to `TOPICS.md` if new), or — if they asked
"what's next" — propose the first `todo` item.

Finally, apply the **suggestion lenses** below to the existing corpus and surface 2–4 candidates
not in the queue. Present as a compact checklist, one line each; the user promotes or dismisses.

> **Suggested topics (not yet in queue):**
> - [ ] `steelman` report — challenge the Keycloak recommendation: what if token volume assumptions are wrong?
> - [ ] `concept` — CMMC compliance angle on token storage: not currently covered

**Context window:** research sessions accumulate fast. `/compact` between major tasks — after a
concept file is written, before the next topic.

### Suggestion lenses

Used at session start (applied to the whole corpus) and after every new output file (applied to
the file just written — max 3 candidates there, highest signal first).

| Lens | Question |
|------|----------|
| **Steelman / adversarial** | Which conclusion is most vulnerable? What would invalidate it? Is there a report arguing the opposite? |
| **Failure mode** | If a key recommendation is wrong, what breaks and how badly? |
| **Dependency gap** | Which referenced concepts or standards have no `concepts/` entry yet? |
| **Regulatory** | Any compliance regime, audit requirement, or standards body not yet on the radar? |
| **Outside-in** | What would a regulator, an attacker, an operator, or an end-user ask that nothing answers? |
| **Simplification** | What could be removed, consolidated, or replaced with something simpler — or is implicitly ruled out without being evaluated? |
| **Outsider domain** | What would a fintech engineer, a security red-teamer, or a distributed-systems researcher ask? |
| **Contrarian** | Who in the field disagrees with the dominant approach, and have we read their argument? |
| **Temporal** | If a file's `Status` is `evolving`, add a `deferred` re-verify entry dated 6 months out. |

---

## Pre-research: scout

Before committing to a topic, `/research-scout` challenges the framing and surfaces blind spots.
A complement, not a gate — skip it when the topic is urgent or already well-defined. Outputs are
proposals; the user approves what gets promoted to `TOPICS.md`.

| Situation | Invocation |
|-----------|-----------|
| Topic feels obvious or tightly bounded | `/research-scout framing <topic>` |
| Picking up a `todo` from a long backlog | `/research-scout framing <topic>` |
| After a cluster of related reports is done | `/research-scout audit` |
| Starting research in a new domain | `/research-scout wildcard <domain>` |
| Completed report drives a major recommendation | `/research-scout steelman <report-slug>` |

---

## TOPICS.md — the agenda

`TOPICS.md` is the **agenda** (full topic history, forward-looking); `README.md` is the **index**
(every completed output file, ordered for navigation). Non-overlapping roles.

Row format: `priority | status | type | topic | researched | notes`

| Column | Values |
|--------|--------|
| `priority` | 🔺 P1 · 🔸 P2 · 🔹 P3 (see below) |
| `status` | 🔲 `todo` · 🔄 `in-progress` · 🚫 `blocked` · ⏸️ `deferred` · ✅ `done` |
| `type` | `concept` · `report` |
| `topic` | Short descriptive name |
| `researched` | `—` until started; then `YYYY-MM-DD`, set when work **begins**, so staleness is visible at a glance |
| `notes` | Scope, open questions, dependencies, and which existing files reference this topic |

**Completed topics are marked `✅ done`, never deleted** — the rows are the history of what was
researched and when. Add the output file to `README.md` at the same time.

Backlog rows take an extra `affects` column listing the output files that reference them:
`| priority | topic | affects | why it might matter |`. **Never pick up a Backlog item
autonomously** — the user must promote it to `todo` first.

### Lifecycle

- **Picking up a `todo`:** set `in-progress` immediately, work Steps 1–5, then mark `✅ done`
  with the output filename in notes and add the file to `README.md`.
- **New request not in the file:** add the row *before* starting work (`in-progress`), plus any
  follow-on topics it spawns as `todo`. Too vague to start → Backlog with a "why it matters" note,
  and ask the user for context.
- **Mid-conversation capture:** any conversation is a source of topics. Write the entry
  **immediately** — a topic mentioned but not captured is lost. Acknowledge in one line
  (*"Added to TOPICS.md: `todo` concept — RFC 9700 OAuth 2.0 Security BCP."*) without interrupting
  the flow. Triggers: a gap or unknown ("we don't know if X supports Y"), a surfaced dependency, a
  deferred decision, a named technology with no concept entry, an unwritten recommendation, "we
  should look into…", "I wonder if…".

### Priority

Priority is **blast radius** — how many existing `concepts/` and `reports/` files reference the
topic.

| Priority | Criteria |
|----------|---------|
| 🔺 P1 | Referenced by ≥5 outputs, OR blocks a deployment path, OR is a direct output of completed research with no file yet |
| 🔸 P2 | Referenced by 2–4 outputs, OR unblocks a known gap in an existing report |
| 🔹 P3 | Referenced by 0–1 outputs; low urgency |

**Never estimate blast radius from memory.** Both scripts live in
`.claude/skills/research-workflow/scripts/` and run under `python3`:

| When | Command |
|---|---|
| Adding a topic — before writing the row | `blast-radius.py <most specific keywords>` |
| After writing any new output file | `priority-audit.py --recount` |
| Fast sanity check (uses counts stored in `notes`) | `priority-audit.py` |
| Apply count-based corrections (writes `.bak` first) | `priority-audit.py --recount --fix` |

Quote multi-word keywords: `blast-radius.py Keycloak realm "LDAP sync"`. Output gives the match
count, tier, affected files, and a paste-ready `notes` snippet — always include the filenames.

On a mismatch: **computed > stored** means new outputs raised the radius — raise the priority and
add the files to `notes`. **Computed < stored** means `notes` may be stale, *or* the topic is P1 on
a non-count criterion; verify before downgrading, as `--fix` only handles count-based corrections.

---

## Repository layout

| Directory / File | Purpose | Written by |
|-----------|---------|------------|
| `source/` | Verbatim primary documents — specs, upstream materials, ground truth | **User only — never Claude** |
| `concepts/` | Distilled, neutral descriptions of technologies, tools, protocols, standards | Claude (catalogue) |
| `reports/` | Opinionated analysis and recommendations in the project's context | Claude (report) |
| `charges/` | Synthesis answers — one per charge question, collating `concepts/` and `reports/` | Claude (charge) |
| `CHARGE.md` | The research brief — the questions this project answers, each linked to its answer | **User-defined; Claude maintains links only** |
| `_scratch/` | Temporary checkpoints; deleted once output files are written | Claude (transient) |
| `_cache/` | Cleaned, persisted web fetch content, reused across sessions and subagents | Claude (persistent until stale) |

**`source/` rules:** never write, edit, or delete anything in it. Always read relevant source files
**before** fetching external material — they are the highest-authority input and external research
only fills the gaps they leave. Where a concept or report contradicts a source file, **flag the
discrepancy explicitly** rather than resolving it silently. Cite as `source/<filename>.md
§<section>`, never as a URL.

**Charges** form a fourth tier above reports and concepts, answering *given everything we now
know, what is the answer to the original question?* — the entry point for decision-makers who will
not read every report.

```
CHARGE.md        ← the questions  (what are we trying to answer?)
charges/         ← synthesised answers  (what did we find, in plain terms?)
reports/         ← detailed analysis  (why, with evidence and citations)
concepts/        ← factual reference  (what is this thing?)
```

**Load `references/charges.md`** whenever you touch this tier — it carries `CHARGE.md` ownership
rules, the `Answered`/`Partial`/`Open` status values, the 7-step charge workflow including the
source-drift freshness check, the `[→ report-slug.md §Section]` citation format, and why charge
files stay out of `README.md`'s reports table.

**Parallelism, subagents, and context** — see [`SUBAGENT-GUIDE.md`](./SUBAGENT-GUIDE.md) for the
complete reference: parallelism patterns, tree depth cap (2 levels), batching (≤3–4 items per
subagent), live status format, scratch handoff protocol, subagent context budgets, and the
cache-first fetch protocol. **Always parallelise by default** — research is embarrassingly
parallel, and serialising burns context on waiting. Every subagent writes `_scratch/<topic>.md`
before returning; never a bare return. Write raw findings to `_scratch/<topic>-raw.md` *before*
formatting any final document.

---

## Output conventions

**Concepts** capture **what a thing is** — spec, architecture, known behaviour, quirks, fit.
Reference material, not opinion. Filename `<kebab-slug>.md`; template
`references/templates/concept.md`.

- **AI agent frameworks** (LangChain, LangGraph, CrewAI, ADK, kagent, …) use
  `references/templates/agent-framework.md` instead — it adds the 14 sections the AI Agent
  Framework rubric in the `research` skill requires (MCP integration, multi-agent patterns,
  streaming, session/state, budget controls, K8s deployment, multi-tenancy).
- **Survey documents** (several items side by side) may use a numbered hierarchy (`## 1.`,
  `### 2.1`) and comparison tables instead of the single-entry template. Still required:
  frontmatter blockquote, confidence line, Relevance, Sources.

**Reports** capture **what you think and recommend** — synthesis, analysis, decision support.
Opinionated, cited, addressed to the project team. Filename `<topic-slug>.md`; template
`references/templates/report.md`. Section titles are flexible; required anchors are **Executive
Summary**, **Recommendations** (or equivalent), **Open Questions**, **Sources**.

**Every file's frontmatter blockquote carries these three fields.** Add any that are missing to an
existing file as part of any amendment.

- **`Keywords:`** — acronyms, synonyms, abbreviations, alternative names, and adjacent search
  terms (e.g. `OIDC, OpenID Connect, OAuth2 identity layer` for Keycloak). This is the index
  `blast-radius.py` uses; a file without it is invisible to future blast-radius scans.
- **`Status:`** — `stable` (settled spec, re-verify 24 months) · `evolving` (active product or
  practice, 6 months) · `deprecated` (superseded, no re-verify). Infer when adding to an old
  file: most RFCs `stable`, most vendor tools `evolving`.
- **`Generated / Confidence:`** — **High** (primary sources: specs, RFCs, official docs) ·
  **Medium** (primary + secondary) · **Low** (mostly inferred or indirect), with the method in
  parentheses: `High (RFCs + official docs)`, `Medium (docs + WebSearch)`.

---

## Epistemic standards

Facts, not stories. Every output reads like a precise technical reference. Non-negotiable.

**Tone.** Flat and precise — no filler ("it is worth noting", "importantly", "in conclusion").
State the fact, cite it, move on. No hedging without cause: assert well-sourced claims directly,
and reserve "appears to" / "may" / "reportedly" for genuine uncertainty paired with a confidence
note. No editorialising — `concepts/` is purely descriptive; opinion belongs in `reports/`.
Audience is a domain expert: do not explain fundamentals, be terse.

**Corroboration before assertion.** A claim is not ready to write until corroborated:

| Claim type | Minimum |
|---|---|
| Protocol behaviour / RFC requirement | Primary spec text (direct quote or section cite) |
| Version / release fact | Official changelog, release notes, or project page |
| Vendor capability claim | Vendor docs **plus** one independent source (issue tracker, blog, test report) |
| Security property or CVE | CVE record + advisory + vendor patch confirmation |
| "Not supported" / "missing" | Verified against docs **and** issue tracker — absent docs is not proof |

If a second source cannot be found, **lower the confidence level and say so.** Never assert as
fact what one source claims.

**Source hierarchy** — never cite a lower tier when a higher is available: primary spec (RFC, W3C,
official schema, source code) → official docs (vendor docs, README, release notes) → authoritative
secondary (IETF WG notes, CVE database, peer-reviewed) → community secondary (GitHub issues,
mailing lists, Stack Overflow — cite with caution).

**Lateral read before deep read.** Before spending a full WebFetch on an external source, spend
one search vetting it: who wrote it, what is their affiliation or incentive, is it primary spec or
secondary commentary? Downweight or skip sources that fail. This keeps low-credibility sources
from shaping the output.

**On conflict:** primary spec wins over any secondary. Two secondaries conflicting — surface it,
never resolve silently:

> ⚠️ **Conflicting sources:** [Source A] states X; [Source B] states Y. Unable to resolve from
> available evidence — marked Low confidence pending primary source verification.

**Model selection.** Model names are environment-specific; configure them in settings. Multi-source
synthesis, security/CVE/compliance analysis, reports informing architectural decisions, and any
retry after a Medium-or-below result get a **high-capability model (opus tier)**. Single-source
concept entries, index updates, and scratch checkpoints get a **fast model (sonnet tier)**. Assign
explicitly when launching subagents — a mechanical subagent writing a file from gathered notes
does not need the expensive tier.

---

## Workflow

### Step 1 — Determine mode

**Catalogue** when the topic is a specific technology, RFC, tool, standard, or protocol, or the
user says "catalogue / document / what is / how does X work".

**Report** when it is a question, recommendation, decision, or comparison, or the user says
"report / should we / viability / compare / roadmap".

**Charge** when the user says "answer/update/write charge N", or asks a question mapping directly
to a numbered charge. Charge mode reads existing `concepts/` and `reports/` only — no external
fetching. Load `references/charges.md` and follow its workflow instead of Steps 2–5.

In doubt, ask: *"Catalogue this as a reference entry, write a recommendation report, or synthesise
an answer to a charge question?"*

### Step 2 — Check for existing files

`ls concepts/` and `ls reports/` before creating anything. If a relevant file exists, **amend it**
rather than duplicating: append an `## Amendment YYYY-MM-DD — <reason>` section and update the
README row status to `Amended YYYY-MM-DD (<reason>)`. Set the TOPICS.md row to `in-progress`.

### Step 3 — Research

- **Check `_cache/`** before any WebFetch — use a fresh cached entry rather than re-fetching.
- **WebFetch primary sources first** (RFCs, specs, official docs), writing each cleaned result to
  `_cache/` immediately.
- **WebSearch** for version history, CVEs, and recent changes — to validate or challenge what the
  primary sources say.
- **Read** prior `concepts/` and `reports/` for context already established.
- Invoke **`/research`** for broad multi-source investigation (parallel subagents, lateral
  vetting, adversarial pass, synthesis) at opus tier.

Corroboration, source hierarchy, and lateral reading are governed by Epistemic Standards above.

### Step 4 — Write the file

- Every factual claim gets a source link or inline citation, with `— fetched YYYY-MM-DD` on each
  Sources entry so staleness is trackable. Pin version numbers on draft RFC/spec citations.
- **Per-claim confidence** on key claims, not just the document-level line: `*High — RFC text*`,
  `*Medium — two secondary sources*`, `*Low — single blog post, unverified*`. Pair any Low with a
  note on what would raise it.
- Fenced code blocks for JSON/YAML/config with inline `//` comments; tables for comparisons and
  compatibility matrices.
- **Cross-link bidirectionally:** concept files list `Applied in` reports; reports list `Concept
  References`. Link as `See [concept entry](../concepts/slug.md)`.
- Cataloguing an RFC: always include Published date, Authors, Status, and a wire-format section
  with a JSON/YAML example.

**For reports — adversarial challenge before writing Recommendations.** Before committing them to
disk: list the 3–5 premises the recommendations rest on; for each, the strongest counter-argument
or failure mode; any practitioners, posts, or issues contradicting the conclusion; whether the
recommendation would change under different scale, team size, or compliance regime. If a challenge
is material, either strengthen the claim with corroborating evidence, lower its confidence label,
or add it to **Open Questions**. Never leave a material challenge unaddressed.

**Open Questions escalate to TOPICS.md.** Every unresolved item becomes a `todo` row immediately —
before Step 5 — with the report as the dependency. Run `blast-radius.py` before assigning priority.

> `| 🔹 P3 | 🔲 todo | concept | <topic> | — | Open question from reports/<slug>.md: <question text> |`

### Step 5 — Update the index

`README.md`: new report → a row in the reports table (`New YYYY-MM-DD`); new concept → a concepts
table row with filename, subject, date; amendment → update the row to `Amended YYYY-MM-DD
(reason)`.

`TOPICS.md`: mark the topic `✅ done` with its output filename; add follow-on topics and newly
discovered gaps as `todo` (running `blast-radius.py` on each first); if blocked, set `blocked`
with a reason.

Then apply the **suggestion lenses** to the file just written (max 3 candidates), and run:

```bash
python3 .claude/skills/research-workflow/scripts/priority-audit.py --recount
# apply count-based fixes automatically:
python3 .claude/skills/research-workflow/scripts/priority-audit.py --recount --fix
```

---

## Programmatic tool calling

Load `references/ptc-patterns.md` for the three-technique reference (tool search, batched Python
queries, examples array). Technique 2 matters most: write Python to batch multiple tool calls and
keep intermediate results off-context.
