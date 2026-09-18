---
name: tighten-docs
description: Tighten prose in natural-language files on disk (.md, .txt, .tex, .typ) without touching code, structure, or meaning. Requires a clean git tree, or asks before overwriting. Use for "tighten this doc", "shorten this README", "condense these notes".
---

# Tighten Docs

Rewrites prose in a file to be shorter, in place, keeping structure and every literal intact.

This is a file operation, not a response style. The `Terse` output style governs how you talk;
this skill governs what you write into an existing document on disk when asked.

Tightening removes slack at the word, sentence, and paragraph level. It is not summarising: every
point in the original survives. If a point has to go to hit a length, that is a different job and
needs the user's agreement first.

## Before editing anything

1. Check the extension against the boundaries below. If it is not on the allowed list, stop and
   say so.
2. Establish a way back before overwriting anything. In a git repository the tree is the backup:
   confirm the files you are about to edit are committed, then say so. `git diff` shows exactly
   what changed and `git checkout -- <path>` restores any file byte for byte.
3. No git, or uncommitted changes in a file you are about to edit? **Stop and ask.** Do not write
   a copy anywhere by default — a scattered backup directory is its own maintenance problem, and
   copies made automatically are never cleaned up. If the user wants one, they choose the
   location.
4. Never tighten a `*.original.*` file. Skip it — earlier runs of this skill may have left some.

## Skip a file that is already tight

Read the file before editing it. If it has no measurable slack, leave it untouched and report it
as already tight. Editing a lean file spends risk for no gain — every rewrite can drop a
qualifier, and a file with nothing to remove has only qualifiers left to lose.

Slack looks like: filler words, "you should" and "make sure to", passive constructions, two
bullets making one point, several examples of one pattern, a sentence restating its own heading,
a paragraph announcing what the next paragraphs will say, and a closing paragraph recapping the
section.

No slack means stop. Do not manufacture savings by cutting a qualifier, an example that carries
distinct information, or a negation.

On a batch, report the skipped files by name. A run where nothing was skipped is a warning sign,
not a success: it usually means the bar drifted down to justify editing everything.

Do not triage by average sentence length without checking the splitter. A naive split on
sentence-ending punctuation merges a markdown heading into the paragraph below it and joins
bullets that lack terminal punctuation, which inflates the average and invents long "sentences"
that are really lists. Split on blank lines first, drop lines starting with `#`, `|`, `>`, or
`<!--`, strip bullet markers, then split. Correcting this moved one file from 26.2 to 22.9 words
per sentence before any editing, and turned four files that looked like they needed work into one.

## Boundaries

**Tighten only:** `.md`, `.txt`, `.typ`, `.typst`, `.tex`, and extensionless text files.

**Never modify:** `.py`, `.js`, `.ts`, `.tsx`, `.json`, `.yaml`, `.yml`, `.toml`, `.env`, `.lock`,
`.css`, `.html`, `.xml`, `.sql`, `.sh`.

Mixed file (prose plus code)? Tighten the prose sections only.

Unsure whether something is code or prose? Leave it unchanged.

## Preserve exactly

Copy these byte for byte. Do not reflow, reorder, reindent, or "tidy" them:

- Fenced and indented code blocks. Treat them as read-only regions: no removing comments, no
  changing spacing, no reordering lines, no shortening commands.
- Inline code in backticks.
- URLs and markdown links.
- File paths (`/src/components/...`, `./config.yaml`).
- Commands (`npm install`, `git commit`, `docker build`).
- Technical terms: library names, API names, protocols, algorithms.
- Proper nouns: project names, people, companies.
- Dates, version strings, and units. Numbers in code blocks, tables, commands, and paths are
  untouchable too. A numeric value in *prose* is the one exception — see § A number is content or
  it is decoration.
- Environment variables (`$HOME`, `NODE_ENV`).
- Error strings.
- Negations: not, never, no, only, except. Dropping one inverts the meaning.

Do not merge sections across a code block.

## Preserve structure

- All headings, with their exact text. Tighten the body beneath, never the heading.
- Bullet hierarchy and nesting depth.
- List numbering.
- Tables: tighten cell text, keep every row, column, and the header.
- YAML frontmatter: untouched.

## Tighten

- Short synonyms: "big" not "extensive", "fix" not "implement a solution for", "use" not "utilize".
- Fragments are fine: "Run tests before commit", not "You should always run tests before
  committing".
- Drop "you should", "make sure to", "remember to". State the action.
- Cut filler (just, really, basically, actually, simply) and connective fluff (however,
  furthermore, additionally).
- Merge bullets that say the same thing twice.
- Where several examples demonstrate one pattern, keep the clearest and cut the rest.
- One idea per sentence, target 20 words. Active voice. Imperative for instructions.

Never add a word to sound tighter. If the shorter phrasing is not actually shorter, keep the
original.

Keep the word a reader already knows. Swapping a familiar word for a rarer, shorter one costs a
lookup and saves nothing.

### Two of these rules depend on what the file is

**Fragments are fine** and **imperative for instructions** hold for instruction files: a SKILL.md,
a README usage section, a runbook step, a CLI help text. They are wrong for an explanatory
artifact — an ADR, PRD, todo task file, research report, or incident write-up. There, dropping the
conjunction drops the mechanism, and a Consequences section in fragments becomes a list of
assertions nobody can check. On those files the two rules are suspended and
`agentic-standards/references/technical-prose.md` wins, which requires articles, conjunctions, and
complete sentences.

Every other rule in this section applies to both.

The rest of this skill is a file operation: back up, check the extension, skip what is already
tight. Those steps have no meaning for a document being written for the first time. What does
carry to authoring is § Tighten the unit, not only the word, § A number is content or it is
decoration, § State the finding, not the trail to it, and the two paragraphs above — cited from
`CLAUDE.md` § Response Style as standards that apply on the first pass.

## Tighten the unit, not only the word

Word-level edits reach a fraction of the slack. A sentence can be built from good words and still
carry nothing, and a paragraph can be built from good sentences and still repeat the one above it.
Work the largest unit first: paragraph, then sentence, then word. Tightening a sentence you are
about to delete wastes the effort and biases you toward keeping it.

### What licenses a deletion

The rule at the top of this skill preserves every *point*. A unit that carries no point is not a
point, so removing it is tightening rather than summarising. Three tests decide, and a unit has to
fail all three before it goes:

- **Would the reader do anything differently if it were absent?** The same test as the one for
  numbers. If nothing changes, the unit shows that the work was done instead of telling the reader
  something.
- **Portability.** Could this sentence move unchanged into another project's document or another
  team's runbook? Then it is about documents in general, not about this one.
- **Altitude.** Does it restate its neighbour at a different level of abstraction, as the general
  version of the specific sentence below it or the specific version of the general one above? Keep
  whichever one the reader acts on, which is usually the specific.

A unit that fails two tests and passes one gets tightened, not deleted.

### A defect is not slack

Those three tests detect absent content. Duplication, contradiction, and confusion are defects in
content that is present, and they fail the tests for the wrong reason: a duplicated rule passes
portability, and a contradicting rule is one the reader acts on, which is a pass. Do not route
them through the deletion licence.

Each one comes out of the edit, goes back verbatim, and is reported with a named warning. The
document you hand back carries the original wording, and the warning is the deliverable.

- **Duplicative.** The unit states a point already made in the same file. Cut the later copy only
  when the surviving one sits above it under a heading the reader passes through on the way.
  Otherwise put it back and warn, naming both locations. Across files it is not yours to cut at
  all: § Redundancy pass owns that, and it stops at a proposal list.
- **Contradictory.** Two units state rules that cannot both hold. Deleting either picks the
  winner, which is a content decision this skill has no authority to make, and the shorter
  document then silently loses a rule somebody relies on. Put both back, quote both with line
  numbers, say which one you believe is current and why, and stop editing that section.
- **Confusing.** You cannot recover what the unit means. Then you cannot tighten it either,
  because you cannot preserve a meaning you never had. Deleting it is the worst outcome available:
  it looks like a saving and is an information loss. Put it back verbatim and warn, naming the
  readings you could not choose between.

Never write the warning into the document. An inline `TODO`, `FIXME`, or `<!-- unclear -->` is the
template residue `agentic-standards/references/technical-prose.md` § Do not write the template
back forbids, and a tighten that adds markers grows the file it was called to shorten.

### Paragraph patterns

- **The announcement.** A paragraph whose job is to say what the following paragraphs will say.
  The headings are already visible.
- **The recap.** A closing paragraph restating the section the reader has just finished.
- **Motivation longer than the rule it motivates.** Keep the mechanism, meaning the specific thing
  that breaks, and cut the argument for caring about it.
- **An example that restates the rule in other words.** An example earns its place by covering a
  case the rule does not obviously reach.
- **A paragraph that is a table.** Three or more items compared on the same axes belong in a
  table. Converting one is a structural change, so propose it rather than doing it silently.

### Sentence patterns

- **A general truth the reader already accepts.** "Documentation is important for
  maintainability." True, unarguable, and it changes nothing.
- **A hedged instruction.** "You may want to consider validating the input." A hedged instruction
  is not an instruction: either state it, or state the condition under which it applies.
- **Metadiscourse.** A sentence telling the reader how to read the next one, how important it is,
  or what to notice. Show it in the content or drop it.
- **The scaffolding sentence.** "This section covers X", under a heading that says X.

Never cut a sentence because it is long, because it is the only one in its paragraph, or because a
section would look tidier without it.

### Patterns imported from no-ai-slop

`agentic-standards/references/no-ai-slop.md` § Patterns to cut is written for a human draft, but
most of its entries are voice-neutral and apply here unchanged: binary contrasts, throat-clearing
openers, faux-insight setups, colon reveals, superficial `-ing` analysis, importance puffery,
interpretive metadiscourse, weasel attribution, fake-strong verbs, synonym cycling, negative
listing, robotic rhythm, rhetorical setups, fake-profound kickers, and summary-recap endings. Its
§ Words to cut applies in full, including the technical exception that keeps a banned word when it
names the thing precisely.

Three entries do not transfer. **Dramatic fragmentation** contradicts this skill's fragments rule,
and § Two of these rules depend on what the file is decides which one wins. **Em dashes** and
**formatting slop** are house style, so leave the document's existing convention alone rather than
converting it during a tighten.

The editing principles in that file do not transfer at all. "Preserve the writer's real voice",
"minimum effective edit", and keeping humour, profanity, and "I think" all protect an author this
document does not have.

### Report every deletion

A reworded sentence shows up in `git diff` and is easy to judge. A deleted one is not, because
whoever reads the report cannot see what is gone. List each deleted sentence and paragraph
verbatim under the file it came from, so the user can restore one without reading the diff. Report
the warnings from § A defect is not slack the same way, each with its class named, and say plainly
that those passages were left in place.

If every paragraph under a heading fails all three tests, stop and ask. An empty section is a
structural change, and § Preserve structure keeps headings.

## A number is content or it is decoration

A number is content when a reader applies it, and decoration when it only shows that the work was
done. The test is one question: would the instruction change if the number were absent? If not,
cut it and keep the claim.

Keep:

- A threshold the reader applies — "worth following when its records come from more than three
  distinct openers".
- A comparison that carries the argument — "resolved 8 of 86 tickets in a broad family" against
  "30 of 200 in this category", where the contrast is the point and the sentence collapses
  without it.
- A cost that drives a choice — "~67s against ~5s", which is why the expensive call is made once
  per sitting.
- A safety measurement — "emails the requester, measured 6 of 6".
- Calibration for what to expect — "about 14% of values do not resolve".

Cut:

- Population counts behind a qualitative claim. "better populated than `category`: 47 of 72 open
  tickets and 3,234 of 4,484 resolved" becomes "better populated than `category`".
- A percentage restating the word beside it. "supplies about 70% of the result, so most of what
  comes back" becomes "dominates the result".
- The working behind a threshold already stated: "cuts the same-opener share from 53% to 10% while
  keeping 52% of the pairs".
- A count where a fraction is what the reader uses. "32 of 71 open tickets are email injection"
  becomes "roughly half this queue".
- "set on 72 of 72 open tickets" becomes "set on every open ticket".

This overrides § Preserve exactly for numeric values in prose. It does not touch numbers in code
blocks, tables, commands, version strings, or paths.

Cutting decoration and tabulating content are the same discipline from opposite ends:
`agentic-standards/references/technical-prose.md` § Measured values in prose requires a table once
a sentence carries more than one measured value. A number that survives this test and has
siblings belongs in that table, not back in the paragraph.

## State the finding, not the trail to it

A chain of internal identifiers is not prose. This passage:

> That a non-broadcast shared watcher means two records are *related* was never tested —
> [#053](../../../todo/053-...md) closed unrun, because judging relatedness needs human labels and
> [#017](../../../todo/017-...md) ruled that harness out.

becomes:

> That a shared watcher means two records are related has never been tested, and testing it would
> need human labels nobody has produced.

Same finding, no tour through the issue tracker. A single trailing citation such as "(ADR-0038)"
is cheap and stays. What goes is a sentence built out of references, where the reader must follow
two of them to learn one fact.

## Example

Original:

> You should always make sure to run the test suite before pushing any changes to the main branch.
> This is important because it helps catch bugs early and prevents broken builds from being
> deployed to production.

Tightened:

> Run tests before push to main. Catches bugs early, prevents broken prod deploys.

## After

Report one line per file: path, before and after line counts, and how it is recoverable — the
commit it is clean against, or the location the user chose.

If tightening would lose a distinction you cannot preserve in fewer words, keep the longer
wording and say which passage you left alone. Meaning outranks length.

Read the tightened file back before reporting. A file that no longer parses as the same
instructions is a failure, however much shorter it is.

In a repository whose tests assert prose content, removing a number or a citation can blind a
guard: a registry of retired claims matches on wording, and a citation rule can require the record
to be named. Run the test suite after this pass, and treat a newly-blind registry entry as part of
the edit rather than a surprise.

## Redundancy pass

Opt-in, separate, and never part of a normal tighten. Ask for it by name.

Rewording buys a fraction of a file. Deleting a passage that already exists elsewhere buys all of
it. This pass finds those passages; the tighten rules above cannot, because they preserve every
heading and row by construction.

It needs the other files open, so it works across a set, not one file.

1. Across the target set, find passages stating the same rule in more than one place.
2. Pick one home for each rule — the most specific file that every other mention can reach.
3. Propose replacing the other copies with a pointer to that home. One line naming the file and
   the rule, enough that a reader knows whether to follow it.
4. Stop. List each proposed deletion with its file, its line range, and the home you chose.
5. Delete nothing until the user approves that list.

Keep a restatement when the reader cannot reach the home in time to act on it — a security
boundary, a destructive-action gate, or a rule a subagent needs but will not load the home file to
get. Say which ones you kept and why.

A pointer that is longer than the passage it replaces is not a saving. Leave the passage.

## Related

- `Terse` output style — conversation compression, not files.
- `agentic-standards/references/no-ai-slop.md` — removing AI patterns while preserving an author's
  voice. Different goal: that guide protects voice and cadence, this one strips them for brevity.
  § Patterns imported from no-ai-slop names the subset that carries over and the entries that do
  not. Do not run the full guide over a document you are tightening without deciding which you
  want.
- `agentic-standards/references/technical-prose.md` — generative voice for a document written from
  scratch. Tighten an existing file; that guide governs a new one.
