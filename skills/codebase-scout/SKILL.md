---
name: codebase-scout
description: Proactive backlog generation — reads the codebase, existing TODOs, and project goals to surface prioritised improvement candidates across quality, tech debt, features, security, and production-readiness. Presents candidates for user acceptance, then writes accepted items into todo/ and TODO.md. Use when asked to "find what to work on", "scout for improvements", "what should we do next", "find tech debt", "build the backlog", or "what features should we add".
license: MIT
compatibility: opencode
---

# TODO Scout

Explore the codebase and project state to surface prioritised improvement candidates, then write
accepted ones into the backlog as first-class task files.

**Generative and exploratory, not evaluative.** It asks "what *should* we build or fix?", not "is
this plan safe to build?". Runs before `/draft-prd`, feeding the backlog `/prd-workflow` tracks.

```
/codebase-scout       ← YOU ARE HERE: read codebase → surface candidates → populate backlog
      │
      ▼
/prd-workflow         ← user picks an item, task file already exists
      │
      ▼
/draft-prd            ← turns the thin task file into a full design
      │
      ▼
/board-review → implementation → /closeout-prd → /prod-release
```

Activate on: "what should we work on next?" · "find tech debt / improvements" · "scout the
codebase" · "build the backlog" · a new session with no clear next task · just after shipping ·
a thin or stale backlog.

## Invocation

```
/codebase-scout                  — lenses 1–6, full codebase
/codebase-scout security         — one lens
/codebase-scout debt quality     — several lenses
/codebase-scout --market         — lenses 1–6 plus Lens 7
/codebase-scout --market-only    — Lens 7 alone
/codebase-scout --quick          — P0/P1 only: skips lenses 5 and 6, caps at 5 candidates
/codebase-scout --area src/api   — restrict codebase lens globs to a subdirectory
```

`--quick` is incompatible with Lens 7 — market research is inherently P2/P3 territory. `--area`
does not affect Lens 7.

## Lenses

Lenses 1–6 are inward-facing: they read the codebase and surface problems that already exist.
Lens 7 is outward-facing and **opt-in** — slower and more speculative.

```
LENS                      DEFAULT   QUESTION
──────────────────────────────────────────────────────────────────────────
1. Code quality           ✅ on     Where is the code fragile, duplicated, or hard to change?
2. Tech debt              ✅ on     What shortcuts are compounding? What will hurt in 6 months?
3. Production             ✅ on     What would fail at 3am? What's missing for prod-readiness?
4. Security               ✅ on     What attack surfaces, secret leaks, or auth gaps exist?
5. Features               ✅ on     What's obviously missing that users/operators would want?
6. Developer XP           ✅ on     What slows down working in this codebase day-to-day?
7. Market & ecosystem     ⬜ opt-in What do comparable projects do that this one doesn't?
──────────────────────────────────────────────────────────────────────────
```

---

## Step 0: Orient

1. **Read `TODO.md`** — what is already tracked? Never re-surface an open or in-progress item.
   Note the next available number.
2. **Read `CLAUDE.md`, `README.md`, `ARCHITECTURE.md`** — the project's stated goals, stack,
   domain, and target users. Essential for Lens 7: what the project *is* determines the
   comparators.
3. **Scan recent activity** — churn is high-signal, since often-changed files are either
   important or troubled:
   ```bash
   git log --oneline -20
   git diff $(git merge-base HEAD main 2>/dev/null || echo HEAD~10)...HEAD --stat 2>/dev/null | head -40
   ```
4. **Announce scope and ask about Lens 7** — unless `--market` or `--market-only` already
   answered it. Wait for the response before launching anything.

   > "Ready to scout [lenses]. Before I start — do you also want **Lens 7: Market & ecosystem**?
   > It researches comparable projects and user demand signals to surface feature ideas grounded
   > in real evidence. It runs in parallel with the codebase lenses but takes longer due to web
   > research.
   >
   > **y** / **n** / **market-only** (skip codebase lenses)"

## Step 1: Parallel lens exploration

One subagent per active lens, all in parallel (`run_in_background: true`), each writing findings
to `todo/scout/<run-slug>/<lens-slug>.md`.

**Lenses 1–6:** load `references/lens-codebase-subagent.md` as the prompt template and substitute
the lens name, its question, and the codebase summary.

**Lens 7:** load `references/lens-market-subagent.md` — a web research subagent, not a
codebase-reading one. It looks outward at comparable projects, competitor features, ecosystem
trends, and demand patterns. Substitute the project summary and existing TODO items. The grounding
rule lives in that file: **every candidate carries a source URL — no evidence, no candidate.**
Suited to quarterly "where should this go?" and pre-roadmap sessions, not sprint-level scouting.

### Signals per lens

**1 — Code quality.** Functions >50 lines with multiple responsibilities · copy-pasted blocks
(Rule of Three: three instances means extract) · shallow abstractions that pass data through
without simplifying it · premature abstractions built before two real use cases · missing or
wrong error handling (bare `except`, swallowed errors) · magic numbers and hardcoded strings ·
dead code (unused functions, commented blocks >20 lines) · inconsistent naming that breaks the
mental model · files importing from too many modules · parallel data structures updated in
lockstep (a missing abstraction) · divergent change (one module changed for unrelated reasons —
split it) · shotgun surgery (one change requiring edits across many files — consolidate).

**2 — Tech debt.** TODO/FIXME/HACK comments, especially dated ones · dependencies pinned to old
versions · deprecated API usage, library or internal · abstractions grown past their design (god
classes, fat models) · tests that are brittle, slow, skipped, or commented out · hardcoded values
that should be environment-specific · approaches known to hit a wall at scale.

**3 — Production readiness.** Missing health/readiness endpoints · no graceful shutdown · secrets
in code, config, or git history · no request timeout or circuit breaker on external calls · no
retry for transient failures · incomplete logging (no request IDs, unstructured) · error responses
leaking internals · no rate limiting on public endpoints · missing connection pool limits or query
timeouts · no metrics, tracing, or alerting hooks.

**4 — Security.** User input reaching SQL, shell, file paths, or template engines unvalidated ·
auth checks bypassable (missing middleware, wrong order) · authorisation gaps (user A reaching
user B's resources) · secrets suggested by env var names checked into source · dependencies with
known CVEs (`npm audit`, `pip-audit`, `trivy`) · missing CSRF protection on state-changing
endpoints · `*` CORS · long-expiry tokens with no revocation story · file uploads not validating
type, size, or content.

**5 — Features.** Gaps against the project's stated goals · partial implementations with clear
next steps (flags never turned on) · repeated patterns suggesting a missing abstraction · common
workflows needing too many steps · missing export/import for important data · absent admin or
observability tooling (no audit log, no admin panel) · endpoints lacking documented error cases.

**6 — Developer experience.** Local setup needing >5 manual steps · full test runs over 60s with
no fast subset · no linting or formatting in CI · missing or stale documentation for non-obvious
decisions · hard-to-mock dependencies (no interfaces, no test doubles) · dev/prod parity gaps ·
missing seed data or fixtures.

## Step 2: Poll and collect

```
🔍 Scouting...  quality ✅  debt ⏳  production ⏳  security 🔵  features ✅  devxp 🔵  market ⏳
```

Once all complete, read each lens file and consolidate into one ranked list. **Lens 7
post-processing:** before mixing market candidates in, glob and grep for obvious implementations
of each suggested feature. Drop anything that clearly already exists; mark the rest
`[market-verified]`.

## Step 3: Rank and deduplicate

1. **Deduplicate** — merge candidates describing the same underlying problem from different
   lenses. Keep the richer description, note both lenses.
2. **Rank:** P0 — actively causing failures or data loss *right now* · P1 — security gaps,
   production-readiness gaps, actively compounding debt · P2 — quality and feature improvements
   with clear value · P3 — nice-to-haves, low-signal DX. Within a tier prefer smaller effort,
   higher impact, more reversible.
3. **Cap at 12** for presentation (5 with `--quick`). If more were found, note "N additional
   lower-signal candidates found — ask to see them."

## Step 4: Present

```
TODO Scout — <N> candidates found  (<date>)
══════════════════════════════════════════════════════════════════
#   Title                              Lens        Priority  Effort
──────────────────────────────────────────────────────────────────
1   Missing request timeouts on API    Production  🟠 P1     small
2   Auth bypass in admin middleware    Security    🔴 P0     small
3   User.find_all() loads all rows     Debt        🟠 P1     trivial
══════════════════════════════════════════════════════════════════
```

Then expand each: problem, why it matters, suggested fix, effort, dependencies. Then ask:

> "Which should I add to the backlog? **all** · **numbers** (e.g. '1 3 5') · **priority**
> (e.g. 'P0 and P1 only') · **none**. You can also adjust priority or title before I write them."

## Step 5: Write accepted items

Per accepted candidate: assign the next number from `TODO.md` → create `todo/<number>-<slug>.md`
from the standard template, pre-filling Problem Statement (from "Problem" + "Why it matters"),
Goals (1–2, from "Suggested fix"), priority, status `⬜ Open`, and
`> *Surfaced by /codebase-scout on <date> — <lens> lens*`. Leave Design and Implementation Plan as
stubs for `/draft-prd`. Add the `TODO.md` row (priority, `⬜ Open`, branch `—`, PR `—`).

```
Added to backlog:
  #007  Auth bypass in admin middleware        🔴 P0
  #008  Missing request timeouts on API        🟠 P1

TODO.md updated. Run /prd-workflow to pick the next item.
```

```bash
git add TODO.md todo/
git commit -m "docs(todo): add N scout candidates from /codebase-scout [<lens(es)>]"
```

## Step 6: Suggest next action

Any P0 added → "There's a P0 item — recommend picking it up immediately with `/prd-workflow`."
Security items → "Consider `/security-review` for a deeper pass." Production items → "Consider
`/twelve-factor-standards` for a systematic audit." Otherwise → "Run `/prd-workflow` to review the
full backlog and pick the highest-value item."

---

## Quality rules

1. **Specific over vague.** "Add timeout to `PaymentClient.charge()` in `services/payment.py`" is
   a candidate. "Improve error handling" is not.
2. **Problem first.** Describe what is broken or missing *today*, not just a solution. A good
   problem statement makes the fix obvious.
3. **Effort honesty.** Never underestimate to make an item attractive — a wrong estimate is worse
   than none.
4. **Fewer, sharper candidates win.** Five high-signal items beat fifteen vague ones; the user's
   attention is the scarce resource.
5. **Task files must be pickupable cold.** The Problem Statement should be good enough that
   someone reading it in three months knows what to do and why.

## Integration

| Skill | Integration |
|-------|------------|
| `/prd-workflow` | Same task file format; picks up what scout writes |
| `/draft-prd` | Fills in the design when a scouted item is picked |
| `/board-review` | Does not gate scout items — that happens once a design exists |
| `/security-review` | Scout's security lens is a quick pass; that is the deep audit |
| `/twelve-factor-standards` | Overlaps the production lens; that is the systematic checklist |
| `/code-review` | Scout finds structural patterns; that reviews specific changes |
