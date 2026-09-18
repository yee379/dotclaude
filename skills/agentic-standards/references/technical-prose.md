# Technical prose

How to write a technical document that persists in the repo: ADRs, PRDs and plans, todo task
files, research reports and concept notes, runbooks, incident write-ups, review findings files,
and README, ARCHITECTURE, or CHANGELOG entries.

This is the companion to `no-ai-slop.md`. That file assumes a human wrote a draft and the job is
to remove AI patterns without flattening the author's voice. Here there is no prior draft and no
voice to preserve, so these rules supply one. Both files apply to the same document; when they
disagree about voice, this file wins for generated documents and `no-ai-slop.md` wins for edits
to someone else's draft.

Document structure is out of scope. Each artifact type has its own template:

| Artifact | Template |
|---|---|
| ADR | `~/.claude/skills/codebase-arch-review/references/adr-template.md` |
| PRD, plan | `~/.claude/skills/draft-prd/SKILL.md` section *Output template*, with worked section formats in `references/prd-examples.md` |
| Todo task file | `~/.claude/skills/prd-workflow/references/codebase-task-template.md`, `platform-task-template.md` |
| Research report, concept, charge | `~/.claude/skills/research-workflow/references/templates/` |
| Review findings file | `~/.claude/skills/board-review/references/subagent-protocol.md` |

## Write for the third reader

Three people read these documents. The implementer picks it up this week. The reviewer gates it
this week. The archaeologist opens it in six months with no memory of the work, no access to the
session that produced it, and a decision to make.

The first two share your context and will forgive a lot. The third has nothing but the file and
whatever it cites, and is the reader who determines whether writing the document was worth the
tokens. Every rule below follows from serving that reader.

## Leave the session out of it

An agent-authored document leaks its own production history in ways a human author never would.
The archaeologist cannot resolve any of it.

Never write: "as discussed above", "per your request", "the user wants", "I suggested", "as we
saw earlier", "see my earlier analysis", "the current session", or any reference to the
conversation, the prompt, the model, or the agent.

Write absolute dates in `YYYY-MM-DD` form. "Today", "recently", "now", and "the current release"
all decay. Name the person, role, ticket, or commit rather than a pronoun with no antecedent
inside the file.

The test: the document reads correctly with nothing else open except the files it cites.

## Person and tense

**Decisions** take one active sentence, present or future, no conditional: "We will store
sessions in Postgres because the pod restarts lose in-memory state." Not "it is proposed that
sessions could be stored in Postgres", which records a discussion instead of a decision.

**Current state** sections, such as an ADR's Context or a task file's Problem Statement, use
present tense for what is true and past tense for what happened, both stated as fact: "The
resolver returns the raw exception text to the client." Not "the resolver would return", which
reads as hypothetical and makes the reader re-derive whether the bug is real.

**Consequences and risks** use future indicative plus the mechanism: "Every new environment
needs a migration run before the first deploy." Not "may require additional consideration",
which commits to nothing and cannot be checked.

"We" means the team that owns the repository. Never "I". Never the agent as narrator.

Status and metadata fields use the exact vocabulary from the template's status key, not a prose
paraphrase of it, because those fields get grepped and tabulated.

## Separate what is verified, derived, and assumed

Mark all three. The expensive failure is an assumption that reads like a fact, because the
archaeologist has no way to tell them apart and will build on it.

- **Verified:** give the command, file, or symbol that produced the fact.
- **Derived:** give what it was derived from.
- **Assumed:** label it `Assumption:` and state what would falsify it.

"Unknown" is legitimate content, not a gap to paper over: "Unknown: whether the retry path is
covered. No test references `_retry`." A document that hides a hole costs more than one that
names it.

Calibrate with reasons rather than adverbs. "Probably", "likely", and "should be fine" carry no
information unless the next clause gives the reason and the check that would settle it.

State how to derive a value instead of copying the value, per
`~/.claude/skills/draft-prd/references/precision-rules.md` section 1. That rule is written for
plans and applies to every persisted document: a copied number goes stale, and the reader who
catches it stale stops trusting the rest of the file.

## One term per concept

Name each thing once, then repeat that name exactly. Rotating synonyms for variety forces the
reader to keep a mental glossary of which words mean the same thing.

Put code identifiers, file paths, commands, and error strings in backticks and reproduce them
verbatim, including the parts that look like typos. Prefer a symbol name over a line number:
symbols survive edits.

Define a term the reader will not know at first use, in one clause, then move on.

## Let the format follow the content

- **Prose** for causal reasoning: why, trade-offs, mechanism. Bullets strip causality, and a
  Consequences section written as bare bullets degrades into a list of assertions nobody can
  check.
- **Table** for three or more items compared on the same axes: one row per item, one column per
  axis, header naming the axis. Also for measured values whatever the item count — see *Measured
  values in prose* below.
- **Numbered list** for ordered steps, or for items that other sections reference by number.
- **Bullets** for an unordered set whose items are not parallel enough to tabulate.
- **Code block**, with a language tag, for anything meant to be copied and run.

Keep the template's headings even when a section is one line. Write "None." under a heading
rather than deleting it, so the reader can see the section was considered rather than skipped.
Add headings beyond the template only when a reader would navigate to that section directly.

Do not pad. A four-line ADR with the right Decision beats forty lines of context around a vague
one.

### Measured values in prose

Counts, ratios, durations, sizes, and percentages become unreadable interleaved with sentences.
The reader has to lift each value out of the prose, compute the ratio the sentence leaves
implicit, hold it while parsing the next one, then compare values that are not aligned. None of
that survives a second reading, and the numbers cannot be diffed against a later measurement.

**Threshold: more than one measured value in a sentence, or more than three in a paragraph, goes
in a table.** Below that, a single number that is the point of its sentence stays inline —
"rollback takes 40 minutes by hand" needs no table.

Fails:

> 47 of 72 open tickets and 3,234 of 4,484 resolved — …

Passes:

| Category | Matched | Total | Share |
|---|---|---|---|
| Open | 47 | 72 | 65% |
| Resolved | 3,234 | 4,484 | 72% |

Give every `x of y` its computed ratio, because the reader computes it anyway. Date the table and
name the command or query behind it, so a later reader re-derives rather than trusts. This is the
discipline of `draft-prd` Phase 2's `## Measured facts` block, applied to any persisted document.

The prose around the table carries what the numbers mean, not the numbers again. State the one
conclusion the table supports and leave the values to the table.

## Write the costs down

Negative consequences, risk lists, and the cons of a rejected option fail in one recognisable
way: every entry is mild and survivable. That pattern means the option was never understood well
enough to reject.

Name the cost someone would actually feel, and say who feels it and when. "Rollback needs a
manual schema revert, done by hand by whoever is on call" beats "some additional operational
complexity". For a rejected option, give the concrete reason it lost rather than calling it less
suitable.

## Voice

Plain, direct, and unhurried. Short sentences carrying one fact each, varied enough that the page
does not read like a filled-in form. Flat corporate register is its own kind of slop: "This
document outlines the proposed approach" tells the reader nothing they did not get from the
title.

Three things `no-ai-slop.md` protects do not transfer here: jokes, profanity and blunt asides,
and phrases such as "I think" or "to be honest". That file protects them because they belong to a
human author whose voice is worth keeping. A generated document has no such author, so keep the
register even.

Chat output styles never reach these files. `Terse` and `Terse Ultra` compress the conversation;
articles, conjunctions, and complete sentences stay intact in the document whatever style is
active.

## Self-check before saving

1. Run `no-ai-slop-eval.md`, sections *Words to cut* and *Patterns to cut* in full, and *Final
   read* except its voice-recognition, *What changed*, and detect-request items. Skip *Editing
   principles* entirely: it checks fidelity to a human draft that does not exist here.
2. Search your own draft for session leakage: "as discussed", "per your request", "the user",
   "I ", "today", "above", "earlier", "we saw".
3. Every number: does the document say how to re-derive it, or is it a copy that will go stale?
   Any sentence holding more than one measured value, or paragraph holding more than three —
   moved into a table?
4. Every assumption: labelled, with a falsifier?
5. Every risk and negative consequence: names a cost someone would feel, and who feels it?
6. Would the archaeologist, holding only this document and the files it cites, reach the same
   decision?

Never invent a fact, number, source, or falsifier to satisfy one of these checks. If the fact is
missing, ask, or write it down as unknown.
