# Charges — the Synthesis Layer

Load this file when working with `CHARGE.md` or `charges/` — creating a charge answer, updating
one after a new report lands, or running Charge mode.

`CHARGE.md` and `charges/` form a fourth tier above `reports/` and `concepts/`. They exist
to answer the question: *given everything we now know, what is the answer to the original
research question?*

## The four-tier reading path

```
CHARGE.md        ← the questions  (what are we trying to answer?)
charges/         ← synthesised answers  (what did we find, in plain terms?)
reports/         ← detailed analysis  (why, with evidence and citations)
concepts/        ← factual reference  (what is this thing?)
```

Charge files are **the entry point for decision-makers** who do not want to read every report.
A reader who only reads `charges/` should understand the state of the research, the
recommendation, and the key residual open questions — with links into `reports/` for depth.

## `CHARGE.md` — the research brief

`CHARGE.md` is user-defined. It contains the broad questions the research is expected to
answer, grouped by theme, each linking to its answer document in `charges/`. Questions are
intentionally broad — each one may be answered by synthesising multiple reports and concepts.

Claude maintains the links in `CHARGE.md` (adding `(charges/charge-NN.md)` when a new
charge file is created) but **never rewrites or reorders the questions themselves** — that
is the user's prerogative.

## `charges/` — answer documents

Each charge file answers one question from `CHARGE.md`. It is a **synthesis document**, not
new research. It:

1. **Reads across `concepts/` and `reports/`** to collate the relevant findings
2. **States a direct answer** to the charge question — not "it depends" without follow-up
3. **Cites evidence** with inline `[→ report-slug.md §section-name]` references
4. **Identifies residual open questions** — what is still unknown or unresolved

Charge files are the *most opinionated* output in the repository. Where reports hedge or
present options, charge files commit to an answer based on the weight of evidence.

## Charge file structure

Load `references/templates/charge.md` as the file template.

**Status values:**

| Status | Meaning |
|--------|---------|
| `Answered` | A clear, defensible answer exists based on research to date |
| `Partial` | An answer exists for the main thrust but one or more sub-questions remain open |
| `Open` | Insufficient research to answer; records what is known and what is needed |

## When to write or update a charge file

Write or update a charge file when:

- A new report is written that directly answers or changes the answer to a charge question
- A charge is explicitly requested: *"answer charge 3"* or *"update charge 7 given the new report"*
- A charge status needs to change (e.g. from `Partial` to `Answered` after a gap is resolved)

Do **not** automatically update all charge files every time a new report is written — only
update the charges materially affected by the new finding.

## Charge mode — how to work a charge

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

## Evidence citation format

```
[→ report-slug.md §Section Title]
```

Direct quotes use standard Markdown blockquotes:

```markdown
> "The connector doesn't support refresh tokens since the SAML 2.0 protocol doesn't provide
> a way to requery a provider without interaction." [→ dex-integration.md §1.3]
```

## Charge files and README.md

Charge files are **not listed in README.md's reports table**. `README.md` indexes `concepts/`
and `reports/`. Charge files are navigated via `CHARGE.md`.

The README should include a reading-path entry pointing at `CHARGE.md` as the
management-level entry point:

```markdown
**"I need a management-level summary of what the research concluded"**
→ `CHARGE.md` — browse the questions; each links to its synthesis answer
→ follow `Primary sources` links in each charge for detailed evidence
```
