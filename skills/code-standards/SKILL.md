---
name: code-standards
description: Language-agnostic coding standards — minimal-code discipline (the ladder), naming, immutability, error handling, type safety, API design, file organisation, comments, and code smells. Use when starting a module, reviewing for maintainability, refactoring to convention, or deciding how much code to write.
origin: ECC
---

# Coding Standards & Best Practices

Universal standards for starting a project or module, reviewing for maintainability, refactoring
to convention, setting up lint/format/type-check rules, or onboarding contributors.

Language-agnostic. Reference examples are TypeScript-flavoured; `/python-patterns` and
`/react-patterns` carry language and framework depth.

## Principles

**Readability first** — code is read more than written. Clear names, self-documenting over
commented, consistent formatting.

**KISS** — the simplest solution that works. No over-engineering, no premature optimisation.
Understandable beats clever.

**DRY** — extract common logic, reuse components, share utilities. No copy-paste programming.

**YAGNI** — don't build before it's needed. Avoid speculative generality; add complexity when
required, refactor when it arrives.

The ladder below is how KISS, DRY, and YAGNI get applied in practice.

## Build the least code that works

Do things efficiently, not carelessly. Each action has to have a purpose and goal. Do not
over-engineer. The best code is the code never written.

No drift back to over-building. This is a reflex, not an occasional review pass.

### The ladder

Stop at the first rung that holds:

1. **Does this need to exist at all?** Speculative need = skip it, say so in one line. (YAGNI)
2. **Already in this codebase?** A helper, util, type, or pattern that already lives here → reuse
   it. Look before you write; re-implementing what's a few files over is the most common slop.
3. **Stdlib does it?** Use it.
4. **Native platform feature covers it?** `<input type="date">` over a picker lib, CSS over JS,
   DB constraint over app code.
5. **Already-installed dependency solves it?** Use it. Never add a new one for what a few lines
   can do.
6. **Can it be one line?** One line.
7. Only then: the minimum code that works.

For rungs 2–5, `/search-first` is the workflow that answers them. Use it rather than guessing
whether something already exists.

The ladder runs *after* you understand the problem, not instead of it. Read the task and the code
it touches first, trace the real flow end to end, then climb. Two rungs work → take the higher one
and move on. The first lazy solution that works is the right one, once you actually know what the
change has to touch.

### Bug fix = root cause, not symptom

A report names a symptom. Before you edit, grep every caller of the function you're about to
touch. The lazy fix *is* the root-cause fix: one guard in the shared function is a smaller diff
than a guard in every caller, and patching only the path the ticket names leaves every sibling
caller still broken. Fix it once, where all callers route through.

### Rules

- No unrequested abstractions: no interface with one implementation, no factory for one product,
  no config for a value that never changes.
- No boilerplate, no scaffolding "for later". Later can scaffold for itself.
- Deletion over addition. Boring over clever; clever is what someone decodes at 3am.
- Fewest files possible. Shortest working diff wins, but only once you understand the problem.
  The smallest change in the wrong place isn't lazy, it's a second bug.
- Complex request? Ship the lazy version and question it in the same response: "Did X; Y covers
  it. Need full X? Say so." Never stall on an answer you can default.
- Two stdlib options, same size? Take the one that's correct on edge cases. Lazy means writing
  less code, not picking the flimsier algorithm.
- Mark deliberate simplifications that cut a real corner with a known ceiling (global lock, O(n²)
  scan, naive heuristic).
- Hardware is never the ideal on paper: a real clock drifts, a real sensor reads off, a PCA9685
  runs a few percent fast. Leave the calibration knob, not just less code. The physical world
  needs tuning a minimal model can't see.

### Output

Code first. Then at most three short lines: what was skipped, when to add it. No essays, no
feature tours, no design notes. If the explanation is longer than the code, delete the
explanation. Every paragraph defending a simplification is complexity smuggled back in as prose.

Pattern: `[code] → skipped: [X], add when [Y].`

Explanation the user explicitly asked for (a report, a walkthrough, per-phase notes) is not debt.
Give it in full. The rule is only against unrequested prose.

This governs what you build, not how you talk.

### Intensity

| Level | What changes |
|---|---|
| `lite` | Build what's asked, but name the lazier alternative in one line. User picks. |
| `full` | The ladder enforced. Stdlib and native first. Shortest diff, shortest explanation. **Default.** |
| `ultra` | YAGNI extremist. Deletion before addition. Ship the one-liner and challenge the rest of the requirement in the same breath. |

Example — "Add a cache for these API responses."

- **lite:** "Done, cache added. FYI: `functools.lru_cache` covers this in one line if you'd rather
  not own a cache class."
- **full:** "`@lru_cache(maxsize=1000)` on the fetch function. Skipped custom cache class, add when
  `lru_cache` measurably falls short."
- **ultra:** "No cache until a profiler says so. When it does: `@lru_cache`. A hand-rolled TTL
  cache class is a bug farm with a hit rate."

### When NOT to be lazy

Never simplify away: input validation at trust boundaries, error handling that prevents data loss,
security measures, accessibility basics, anything explicitly requested. If the user insists on the
full version, build it and don't re-argue.

Never be lazy about understanding the problem. The ladder shortens the solution, never the
reading. Trace the whole thing first — every file the change touches, the actual flow — before
picking a rung. Laziness that skips comprehension to ship a small diff is the dangerous kind: it
dresses up as efficiency and ships a confident wrong fix. Read fully, then be lazy.

### Tests for lazy code

`/tdd-standards` owns testing and takes precedence for product code — features, bug fixes, and
refactors routed there get its full workflow and coverage expectations.

Outside that scope (one-off scripts, spikes, throwaway tooling), lazy code without its check is
still unfinished. Non-trivial logic — a branch, a loop, a parser, a money or security path —
leaves ONE runnable check behind: the smallest thing that fails if the logic breaks. An
assert-based `demo()` / `__main__` self-check, or one small `test_*.py`. No frameworks, no
fixtures, no per-function suites unless asked. Trivial one-liners need no test; YAGNI applies to
tests too.

## Reference material

| Topic | File |
|---|---|
| Variable, function, and file naming | `references/naming-conventions.md` |
| Immutability, error handling, async/await, type safety | `references/patterns.md` |
| REST conventions, response format, schema input validation | `references/api-design.md` |
| Application and route file layout | `references/project-structure.md` |
| When to comment, and doc-comment patterns | `references/comments.md` |
| Query shape and result bounding | `references/performance.md` |
| Before/after examples of each anti-pattern | `references/code-smells.md` |

## Code smells

Watch for long functions (>50 lines), deep nesting (5+ levels), magic numbers, dead code, and
inconsistent naming. Examples in `references/code-smells.md`.

## Related skills

- `/search-first` — answers ladder rungs 2–5 before you write custom code.
- `/tdd-standards` — testing standards; authoritative for product code.
- `/python-patterns`, `/react-patterns` — language and framework specifics.
