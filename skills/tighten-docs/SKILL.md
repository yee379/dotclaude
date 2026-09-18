---
name: tighten-docs
description: Tighten prose in natural-language files on disk (.md, .txt, .tex, .typ) without touching code, structure, or meaning. Backs up each file before overwriting. Use for "tighten this doc", "shorten this README", "condense these notes".
---

# Tighten Docs

Rewrites prose in a file to be shorter, in place, keeping structure and every literal intact.

This is a file operation, not a response style. The `Terse` output style governs how you talk;
this skill governs what you write into an existing document on disk when asked.

Tightening removes slack at the word level. It is not summarising: every point in the original
survives. If a point has to go to hit a length, that is a different job and needs the user's
agreement first.

## Before editing anything

1. Check the extension against the boundaries below. If it is not on the allowed list, stop and
   say so.
2. Back up the original to the out-of-tree data directory, never beside the source:
   `~/.claude/data/tighten-docs/<path-with-slashes-as-dashes>.original.<ext>`, so
   `skills/troubleshoot/SKILL.md` backs up as `skills-troubleshoot-SKILL.original.md`.
   Deriving the name from the whole path, not the basename, keeps 35 files called `SKILL.md`
   from colliding.
   Create the directory if absent. Never overwrite an existing backup — suffix with a timestamp.
3. Never tighten a `*.original.*` file. Skip it.
4. In a git repository with a clean tree, the commit is already a backup. Say so and skip step 2
   if the user prefers; do not skip it silently.

## Skip a file that is already tight

Read the file before editing it. If it has no measurable slack, leave it untouched and report it
as already tight. Editing a lean file spends risk for no gain — every rewrite can drop a
qualifier, and a file with nothing to remove has only qualifiers left to lose.

Slack looks like: filler words, "you should" and "make sure to", passive constructions, two
bullets making one point, several examples of one pattern, a sentence restating its own heading.

No slack means stop. Do not manufacture savings by cutting a qualifier, an example that carries
distinct information, or a negation.

On a batch, report the skipped files by name. A run where nothing was skipped is a warning sign,
not a success: it usually means the bar drifted down to justify editing everything.

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
- Dates, version numbers, numeric values, units.
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

## Example

Original:

> You should always make sure to run the test suite before pushing any changes to the main branch.
> This is important because it helps catch bugs early and prevents broken builds from being
> deployed to production.

Tightened:

> Run tests before push to main. Catches bugs early, prevents broken prod deploys.

## After

Report one line per file: path, before and after line counts, backup location.

If tightening would lose a distinction you cannot preserve in fewer words, keep the longer
wording and say which passage you left alone. Meaning outranks length.

Read the tightened file back before reporting. A file that no longer parses as the same
instructions is a failure, however much shorter it is.

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
  Do not run both on the same document without deciding which you want.
- `agentic-standards/references/technical-prose.md` — generative voice for a document written from
  scratch. Tighten an existing file; that guide governs a new one.
