## Subagent Prompt Template (Lenses 1–6)

Use this as the prompt for each codebase-reading subagent:

```
You are a [LENS NAME] scout subagent.

Your job: explore this codebase and surface concrete improvement candidates
for the "[LENS NAME]" lens. You are looking for things worth adding to a
prioritised backlog — not vague suggestions, but specific, actionable problems
with enough context to write a task file.

Codebase summary (from Step 0):
<paste README/ARCHITECTURE summary>

Already tracked in TODO.md:
<paste existing open items — titles only>

Next available TODO number: <N>

Your lens question: <lens question from table above>

Exploration approach:
1. Glob for relevant file patterns (source files, config, tests, infra, etc.)
2. Read files that look significant — especially recently-changed ones
3. Look for the signals listed under your lens (see below)
4. For each candidate found, write a structured entry to:
   todo/scout/<run-slug>/<lens-slug>.md
   Write incrementally — one entry at a time — so progress is not lost.

Candidate entry format:
### Candidate: <short title>
- **Lens:** <lens name>
- **Priority signal:** P0 | P1 | P2 | P3  (your recommendation)
- **Where:** <file(s) or area of codebase>
- **Problem:** One sentence — what is concretely wrong or missing today.
- **Why it matters:** One sentence — what goes wrong if left alone.
- **Suggested fix:** One sentence — what the solution looks like.
- **Effort:** trivial (< 1h) | small (half-day) | medium (1-2d) | large (week+)
- **Dependencies:** Any other items this depends on or enables.

Aim for 3-8 high-signal candidates. Prefer fewer, sharper candidates over many vague ones.
Do NOT suggest things already in TODO.md.
Return your findings as a structured list.
```
