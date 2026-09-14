---
name: compress-docs
description: Compress prose in natural-language files on disk (.md, .txt, .tex, .typ) without touching code, structure, or meaning. Backs up each file before overwriting. Use for "compress this doc", "shorten this README", "tighten these notes".
---

# Compress Docs

Rewrites prose in a file to be shorter, in place, keeping structure and every literal intact.

This is a file operation, not a response style. The `Terse` output style governs how you talk;
this skill governs what you write into an existing document on disk when asked.

## Before editing anything

1. Check the extension against the boundaries below. If it is not on the allowed list, stop and
   say so.
2. Back up the original to the out-of-tree data directory, never beside the source:
   `~/.claude/data/compress-docs/<original-name>.original.<ext>`.
   Create the directory if absent. Never overwrite an existing backup — suffix with a timestamp.
3. Never compress a `*.original.*` file. Skip it.

## Boundaries

**Compress only:** `.md`, `.txt`, `.typ`, `.typst`, `.tex`, and extensionless text files.

**Never modify:** `.py`, `.js`, `.ts`, `.tsx`, `.json`, `.yaml`, `.yml`, `.toml`, `.env`, `.lock`,
`.css`, `.html`, `.xml`, `.sql`, `.sh`.

Mixed file (prose plus code)? Compress the prose sections only.

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

- All headings, with their exact text. Compress the body beneath, never the heading.
- Bullet hierarchy and nesting depth.
- List numbering.
- Tables: compress cell text, keep every row, column, and the header.
- YAML frontmatter: untouched.

## Compress

- Short synonyms: "big" not "extensive", "fix" not "implement a solution for", "use" not "utilize".
- Fragments are fine: "Run tests before commit", not "You should always run tests before
  committing".
- Drop "you should", "make sure to", "remember to". State the action.
- Cut filler (just, really, basically, actually, simply) and connective fluff (however,
  furthermore, additionally).
- Merge bullets that say the same thing twice.
- Where several examples demonstrate one pattern, keep the clearest and cut the rest.
- One idea per sentence, target 20 words. Active voice. Imperative for instructions.

Never add a word to sound compressed. If the shorter phrasing is not actually shorter, keep the
original.

## Example

Original:

> You should always make sure to run the test suite before pushing any changes to the main branch.
> This is important because it helps catch bugs early and prevents broken builds from being
> deployed to production.

Compressed:

> Run tests before push to main. Catches bugs early, prevents broken prod deploys.

## After

Report one line per file: path, before and after line counts, backup location.

If compression would lose a distinction you cannot preserve in fewer words, keep the longer
wording and say which passage you left alone. Meaning outranks length.

## Related

- `Terse` output style — conversation compression, not files.
- `agentic-standards/references/no-ai-slop.md` — removing AI patterns while preserving an author's
  voice. Different goal: that guide protects voice and cadence, this one strips them for brevity.
  Do not run both on the same document without deciding which you want.
