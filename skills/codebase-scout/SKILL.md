---
name: codebase-scout
description: Proactive backlog generation — reads the codebase, existing TODOs, and project goals to surface prioritised improvement candidates across quality, tech debt, features, security, and production-readiness. Presents candidates for user acceptance, then writes accepted items into todo/ and TODO.md. Use when asked to "find what to work on", "scout for improvements", "what should we do next", "find tech debt", "build the backlog", or "what features should we add".
license: MIT
compatibility: opencode
---

# TODO Scout

Explore the codebase and project state to surface prioritised improvement candidates — then
write accepted ones into the backlog as first-class task files.

This skill is **generative and exploratory**, not evaluative. It asks "what *should* we build
or fix?" rather than "is this plan safe to build?". It runs before `/codebase-draft-prd`, feeding
the backlog that `/codebase-workflow` tracks.

## Workflow position

```
/codebase-scout            ← YOU ARE HERE: read codebase → surface candidates → populate backlog
      │
      ▼
/codebase-workflow    ← user picks an item, task file already exists
      │
      ▼
/codebase-draft-prd          ← turns thin task file into a full design
      │
      ▼
/codebase-board-review → implementation → /codebase-closeout → /prod-release
```

---

## When to Activate

- "What should we work on next?"
- "Find tech debt / improvements / things that need fixing"
- "Scout the codebase for issues"
- "Build the backlog" / "fill the backlog"
- "What would make this project better?"
- Starting a new session with no clear next task
- After shipping a feature — before picking the next one
- When the backlog looks thin or stale

---

## Lenses

The scout examines the project through **seven lenses**. Lenses 1–6 are inward-facing: they
read the codebase and surface problems that already exist. Lens 7 is outward-facing: it
researches the broader ecosystem and surfaces features worth building. Run lenses 1–6 by
default; Lens 7 is **opt-in** because it is slower and more speculative.

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

The user can scope to one or more lenses: `/codebase-scout security` or `/codebase-scout debt quality`.
Lens 7 is activated with `--market`, `--features-deep`, or by naming it explicitly.

---

## Step 0: Orient

Before exploring, answer these questions:

1. **Read `TODO.md`** (if it exists) — what's already tracked? Do not re-surface items that are
   already open or in progress. Note the next available task number.

2. **Read `CLAUDE.md`, `README.md`, `ARCHITECTURE.md`** (if they exist) — understand the
   project's stated goals, tech stack, domain, and target users. This context is especially
   important for Lens 7 — knowing what the project *is* determines what comparators to research.

3. **Scan the git log** for recent activity:
   ```bash
   git log --oneline -20
   git diff $(git merge-base HEAD main 2>/dev/null || echo HEAD~10)...HEAD --stat 2>/dev/null | head -40
   ```
   Recent churn areas are high-signal: files changed often are either important or troubled.

4. **Announce scope and ask about Lens 7** — unless `--market` or `--market-only` was
   already passed (in which case the answer is known), always ask before proceeding:

   > "Ready to scout [all lenses / named lenses]. Before I start — do you also want
   > **Lens 7: Market & ecosystem**? It researches comparable projects and user demand
   > signals to surface feature ideas grounded in real evidence. It runs in parallel with
   > the codebase lenses but takes longer due to web research.
   >
   > **y** / **n** / **market-only** (skip codebase lenses, just do market research)"

   Wait for the response before launching any subagents. If the user says **y**, add Lens 7
   to the active set. If **n**, proceed with codebase lenses only. If **market-only**, skip
   Lenses 1–6 and run Lens 7 alone.

---

## Step 1: Parallel lens exploration

Launch one subagent per active lens, all in parallel (`run_in_background: true`). Each subagent
explores the codebase for its specific lens and writes findings to a shared scratch file.

**Lenses 1–6** use this codebase-reading subagent prompt:

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

**Lens-specific signals to look for:**

### Lens 1 — Code quality
- Functions > 50 lines with multiple responsibilities
- Copy-pasted blocks (same logic in 2+ places)
- Missing or incorrect error handling (bare `except`, swallowed errors)
- Magic numbers / hardcoded strings that should be constants or config
- Dead code (unused functions, commented-out blocks > 20 lines)
- Inconsistent naming or style that breaks the mental model
- Files that import from too many other modules (high fan-in coupling)

### Lens 2 — Tech debt
- TODOs, FIXMEs, HACKs in comments — especially ones with dates
- Dependencies pinned to old versions (check package files)
- Deprecated API usage (library or internal)
- Abstraction that has grown past its original design (god classes, fat models)
- Tests that are brittle, slow, or have been skipped/commented out
- Config values that should be environment-specific but are hardcoded
- Areas where the current approach is known to hit a wall at scale

### Lens 3 — Production readiness
- Missing health check / readiness probe endpoints
- No graceful shutdown handling
- Secrets or credentials in code, config files, or git history
- Missing request timeout / circuit breaker for external calls
- No retry logic for transient failures (network, DB)
- Missing or incomplete logging (no request IDs, no structured logs)
- Error responses that leak internal details to clients
- No rate limiting on public-facing endpoints
- Missing database connection pool limits or query timeouts
- Lack of observability: no metrics, no tracing, no alerting hooks

### Lens 4 — Security
- User input that flows to SQL, shell, file paths, or template engines without validation
- Authentication checks that can be bypassed (missing middleware, wrong order)
- Authorisation gaps (user A can access user B's resources)
- Secrets in environment variable names that suggest they're checked into source
- Dependencies with known CVEs (check `npm audit`, `pip-audit`, `trivy`, etc.)
- Missing CSRF protection on state-changing endpoints
- Overly broad CORS policy (`*`)
- JWT/session tokens with long expiry and no revocation story
- File upload handlers that don't validate type/size/content

### Lens 5 — Features
- Obvious gaps relative to the project's stated goals (from README/ARCHITECTURE)
- Partial implementations with clear next steps (feature flags that are never on)
- Repeated patterns that suggest an abstraction is missing
- Common user/operator workflows that require too many steps
- Missing export/import capabilities for important data
- Admin or observability tools that don't exist (no audit log, no admin panel)
- API endpoints that exist but lack documented error cases or validation

### Lens 6 — Developer experience
- Local setup that requires > 5 manual steps (missing Makefile, docker-compose, scripts)
- Tests that take > 60s to run in full, with no fast subset
- No linting / formatting enforced in CI
- Missing or stale documentation for non-obvious design decisions
- Hard-to-mock external dependencies (no interfaces, no test doubles)
- Dev/prod config parity gaps (works locally, breaks in CI or staging)
- Missing seed data or fixtures for common development scenarios

---

### Lens 7 — Market & ecosystem (opt-in)

**This lens is different from Lenses 1–6.** It looks *outward* — at comparable projects,
competitor features, ecosystem trends, and user demand patterns — then cross-references
inward against the codebase to filter out anything already built. It runs a web research
subagent rather than a codebase-reading one.

**When to use:** Quarterly "where should this project go?" sessions, pre-roadmap planning,
when the inward lenses are clean but you want to find the next meaningful feature bets.
Not suited to sprint-level scouting.

**Subagent prompt for Lens 7:**

```
You are a market & ecosystem scout subagent for a software project.

Your job: research the broader landscape for this project and surface concrete
feature or capability gaps — things comparable projects or tools do that this
one does not, that would be genuinely valuable to users.

Project summary (from README/ARCHITECTURE):
<paste project description, domain, tech stack, target users>

Already tracked in TODO.md (do not re-suggest):
<paste existing open items — titles only>

Research approach:
1. Identify 3-5 directly comparable projects, tools, or products in this domain.
   For each, use WebSearch + WebFetch to find:
   - Their feature list / changelog / roadmap
   - User reviews, GitHub issues, community discussions praising specific features
   - Recent additions that got strong positive reception
2. Search for: "[domain] most requested features", "[domain] user pain points",
   "[tool name] alternatives", "what [tool name] is missing"
3. Check ecosystem trends: are there patterns in adjacent tools that haven't
   reached this domain yet?
4. Cross-reference each candidate against the project summary — discard anything
   that is clearly already built, out of scope, or architecturally incompatible.

Write findings incrementally to: todo/scout/<run-slug>/market.md
Write one candidate entry at a time as you find them — do not wait until the end.

Candidate entry format:
### Candidate: <short title>
- **Lens:** Market & ecosystem
- **Priority signal:** P1 | P2 | P3  (P0 is rarely appropriate for market-driven features)
- **Evidence:** What comparable project has this? Where is user demand documented?
  (include URL)
- **Problem:** One sentence — what users cannot do today with this project.
- **Why it matters:** One sentence — what user need this addresses, grounded in evidence.
- **Suggested approach:** One sentence — rough direction for implementation.
- **Effort:** small (half-day) | medium (1-2d) | large (week+) | XL (multi-week)
- **Already built?** Confirm you checked the project summary — this feature does NOT exist.
- **Dependencies:** Any other items this depends on or enables.

Aim for 4-8 high-signal candidates grounded in real evidence.
Every candidate must have a source URL. Do not suggest things without evidence of demand.
Do NOT suggest things already in TODO.md or clearly present in the project summary.
```

**Grounding rule:** Every Lens 7 candidate must include a source URL as evidence. Candidates
without evidence are dropped at consolidation. "It would be nice" is not sufficient — there
must be a traceable signal (competitor feature, GitHub issue, community post, changelog entry)
that the feature has real demand.

---

## Step 2: Poll and collect

Poll all subagents until complete. Show a simple progress line while waiting:

```
🔍 Scouting...  quality ✅  debt ⏳  production ⏳  security 🔵  features ✅  devxp 🔵  market ⏳
```

(Market column only shown when Lens 7 is active.)

Once all complete, read each `todo/scout/<run-slug>/<lens-slug>.md` file and consolidate
all candidates into a single ranked list.

**Lens 7 post-processing:** before mixing market candidates into the ranked list, run a
quick codebase cross-check on each one — glob and grep for obvious implementations of the
suggested feature. Drop any candidate where the feature already clearly exists. Mark
retained candidates with `[market-verified]` to indicate the cross-check passed.

---

## Step 3: Rank and deduplicate

Before presenting to the user:

1. **Deduplicate** — merge candidates that describe the same underlying problem from different
   lenses. Keep the richer description, note both lenses.

2. **Rank** using this signal stack:
   - P0 first: anything that is actively causing failures or data loss *right now*
   - P1: security gaps, production-readiness gaps, or debt that is actively compounding
   - P2: quality and feature improvements with clear value
   - P3: nice-to-haves, low-signal DX improvements

   Within each tier, prefer: smaller effort → higher impact → more reversible.

3. **Cap at 12 candidates** for presentation. If more were found, keep the highest-signal ones
   and note "N additional lower-signal candidates found — ask to see them."

---

## Step 4: Present candidates

Show the ranked list in a clear table, then expand each one:

```
TODO Scout — <N> candidates found  (<date>)
══════════════════════════════════════════════════════════════════
#   Title                              Lens        Priority  Effort
──────────────────────────────────────────────────────────────────
1   Missing request timeouts on API    Production  🟠 P1     small
2   Auth bypass in admin middleware    Security    🔴 P0     small
3   User.find_all() loads all rows     Debt        🟠 P1     trivial
4   No structured logging              Production  🟡 P2     medium
5   Duplicate validation logic (×3)    Quality     🟡 P2     small
...
══════════════════════════════════════════════════════════════════
```

Then for each candidate, show the full entry (problem, why it matters, suggested fix, effort,
dependencies).

After presenting all candidates, ask:

> "Which of these should I add to the backlog? You can say:
> - **all** — add everything
> - **numbers** — e.g. '1 3 5' to add specific ones
> - **priority** — e.g. 'P0 and P1 only'
> - **none** — skip for now
>
> You can also adjust priority or title before I write them."

---

## Step 5: Write accepted items

For each accepted candidate:

1. **Assign the next TODO number** (from the sequence in `TODO.md`).

2. **Create `todo/<number>-<slug>.md`** using the standard task file template. Pre-fill:
   - Problem Statement (from candidate's "Problem" + "Why it matters")
   - Goals (1-2 goals derived from "Suggested fix")
   - Priority and Status (`⬜ Open`)
   - Source: `> *Surfaced by /codebase-scout on <date> — <lens> lens*`
   - Leave Design and Implementation Plan sections as stubs — those get filled by
     `/codebase-draft-prd` when the item is picked up.

3. **Add a row to `TODO.md`** with the correct priority, `⬜ Open` status, branch `—`, PR `—`.

4. After all items are written, show a confirmation:

```
Added to backlog:
  #007  Auth bypass in admin middleware        🔴 P0
  #008  Missing request timeouts on API        🟠 P1
  #009  User.find_all() loads all rows         🟠 P1

TODO.md updated. Run /codebase-workflow to pick the next item.
```

5. Commit:
```bash
git add TODO.md todo/
git commit -m "docs(todo): add N scout candidates from /codebase-scout [<lens(es)>]"
```

---

## Step 6: Suggest next action

After writing items, always suggest what to do next based on what was found:

- If any P0 items were added: "There's a P0 item — recommend picking it up immediately with
  `/codebase-workflow`."
- If security items were added: "Consider running `/security-review` for a deeper pass."
- If production-readiness items were added: "Consider running `/twelve-factor-standards` for a
  systematic audit."
- If the backlog is now well-stocked: "Run `/codebase-workflow` to review the full backlog
  and pick the highest-value item."

---

## Quality rules

1. **Specific over vague.** "Add timeout to `PaymentClient.charge()` in `services/payment.py`"
   is a good candidate. "Improve error handling" is not.
2. **Problem first.** Every candidate must describe what is broken or missing *today* — not
   just describe a solution. A well-written problem statement makes the fix obvious.
3. **Don't duplicate the backlog.** Always read `TODO.md` first. Never surface what's already
   tracked.
4. **Effort honesty.** Don't underestimate to make items look attractive. A wrong effort
   estimate is worse than none.
5. **Fewer, sharper candidates win.** 5 high-signal items are better than 15 vague ones.
   The user's attention is the scarce resource.
6. **Write task files that can be picked up cold.** The Problem Statement must be good enough
   that someone reading the file three months from now immediately understands what to do and
   why.

---

## Integration with other skills

| Skill | How it integrates |
|-------|------------------|
| `/codebase-workflow` | Scout writes task files in the same format; `/codebase-workflow` picks them up |
| `/codebase-draft-prd` | Scout writes thin task files; `/codebase-draft-prd` fills in the design when the item is picked |
| `/codebase-board-review` | Scout does not gate items — that happens later when a design exists |
| `/security-review` | Scout's security lens is a quick pass; `/security-review` is the deep audit |
| `/twelve-factor-standards` | Scout's production lens overlaps; `/twelve-factor-standards` is the systematic checklist |
| `/code-review` | Scout finds structural patterns; `/code-review` reviews specific changes |

---

## Invocation variants

```
/codebase-scout                        — lenses 1–6, full codebase
/codebase-scout security               — security lens only
/codebase-scout debt quality           — two lenses
/codebase-scout --market               — lenses 1–6 plus Lens 7 (market & ecosystem)
/codebase-scout --market-only          — Lens 7 only, skip codebase lenses
/codebase-scout --quick                — surface only P0/P1 candidates, skip P2/P3
/codebase-scout --area src/api         — scope codebase lenses to a subdirectory
```

When `--market` or `--market-only` is passed: activate Lens 7 in parallel with other active
lenses. Announce to the user that it will take longer due to web research.

When `--quick` is passed: skip Lens 5 (features) and Lens 6 (devxp), focus on P0/P1 signals
only, cap at 5 candidates. Lens 7 is not compatible with `--quick` — market research is
inherently P2/P3 territory.

When `--area` is passed: restrict glob patterns for codebase lenses to the specified path.
Lens 7 is unaffected by `--area`.
