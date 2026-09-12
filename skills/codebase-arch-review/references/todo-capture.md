# TODO Capture Protocol

Shared by `/codebase-arch-review`, `/codebase-eng-review`, and `/codebase-design-review`. Loaded
at the end of a review, when surfacing deferred work.

**Present each potential TODO as its own AskUserQuestion. Never batch — one per question. Never
silently skip this step.**

For each, describe:

- **What:** one-line description of the work.
- **Why:** the concrete problem it solves or value it unlocks.
- **Pros:** what you gain by doing it.
- **Cons:** cost, complexity, or risk of doing it.
- **Context:** enough that someone picking this up in 3 months understands the motivation, the
  current state, and where to start.
- **Depends on / blocked by:** prerequisites or ordering constraints.

Then offer: **A)** Add to TODOS.md · **B)** Skip — not valuable enough · **C)** Build it now in
this PR instead of deferring.

**Do not append vague bullet points.** A TODO without context is worse than no TODO — it creates
false confidence that the idea was captured while actually losing the reasoning.
