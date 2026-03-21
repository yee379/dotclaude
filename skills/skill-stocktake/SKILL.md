---
name: skill-stocktake
description: "Use when auditing Claude skills and commands for quality. Supports Quick Scan (changed skills only) and Full Stocktake modes with sequential subagent batch evaluation."
origin: ECC
---

# skill-stocktake

Slash command (`/skill-stocktake`) that audits all Claude skills and commands using a quality checklist + AI holistic judgment. Supports two modes: Quick Scan for recently changed skills, and Full Stocktake for a complete review.

## Scope

The command targets the following paths **relative to the directory where it is invoked**:

| Path | Description |
|------|-------------|
| `~/.claude/skills/` | Global skills (all projects) |
| `{cwd}/.claude/skills/` | Project-level skills (if the directory exists) |

**At the start of Phase 1, the command explicitly lists which paths were found and scanned.**

### Targeting a specific project

To include project-level skills, run from that project's root directory:

```bash
cd ~/path/to/my-project
/skill-stocktake
```

If the project has no `.claude/skills/` directory, only global skills and commands are evaluated.

## Modes

| Mode | Trigger | Duration |
|------|---------|---------|
| Quick Scan | `results.json` exists (default) | 5–10 min |
| Full Stocktake | `results.json` absent, or `/skill-stocktake full` | 20–30 min |

**Results cache:** `~/.claude/skills/skill-stocktake/results.json`

## Quick Scan Flow

Re-evaluate only skills that have changed since the last run (5–10 min).

1. Read `~/.claude/skills/skill-stocktake/results.json`
2. Run: `bash ~/.claude/skills/skill-stocktake/scripts/quick-diff.sh \
         ~/.claude/skills/skill-stocktake/results.json`
   (Project dir is auto-detected from `$PWD/.claude/skills`; pass it explicitly only if needed)
3. If output is `[]`: report "No changes since last run." and stop
4. **Expand `~` paths to absolute paths** before passing to subagents — replace `~` with `$HOME`
   (subagents may resolve `~` as `/root/` rather than the current user's home directory)
5. Re-evaluate only those changed files using the same Phase 2 criteria
6. Carry forward unchanged skills from previous results
7. Output only the diff
8. Run: `bash ~/.claude/skills/skill-stocktake/scripts/save-results.sh \
         ~/.claude/skills/skill-stocktake/results.json <<< "$EVAL_RESULTS"`

## Full Stocktake Flow

### Phase 1 — Inventory

Run: `bash ~/.claude/skills/skill-stocktake/scripts/scan.sh`

The script enumerates skill files, extracts frontmatter, and collects UTC mtimes.
Project dir is auto-detected from `$PWD/.claude/skills`; pass it explicitly only if needed.
Present the scan summary and inventory table from the script output:

```
Scanning:
  ✓ ~/.claude/skills/         (17 files)
  ✗ {cwd}/.claude/skills/    (not found — global skills only)
```

| Skill | 7d use | 30d use | Description |
|-------|--------|---------|-------------|

### Phase 2 — Quality Evaluation

**Path expansion — IMPORTANT:** The scan output uses `~`-prefixed paths (e.g. `~/.claude/skills/foo/SKILL.md`).
Before passing any paths to a subagent, expand them to absolute paths using `$HOME`:

```bash
# e.g. replace ~ with $HOME in all paths before including them in a subagent prompt
echo "$SCAN_OUTPUT" | sed "s|~|$HOME|g"
```

Subagents run in a different environment where `~` may expand to `/root/` instead of the
current user's home directory. Always pass absolute paths.

Launch an Agent tool subagent (**general-purpose agent**) with the full inventory and checklist:

```text
Agent(
  subagent_type="general-purpose",
  prompt="
Evaluate the following skill inventory against the checklist.

[INVENTORY]

[CHECKLIST]

Return JSON for each skill:
{ \"verdict\": \"Keep\"|\"Improve\"|\"Update\"|\"Retire\"|\"Merge into [X]\", \"reason\": \"...\" }
"
)
```

The subagent reads each skill, applies the checklist, and returns per-skill JSON:

`{ "verdict": "Keep"|"Improve"|"Update"|"Retire"|"Merge into [X]", "reason": "..." }`

**Chunk guidance:** Process ~20 skills per subagent invocation to keep context manageable. Save intermediate results to `results.json` (`status: "in_progress"`) after each chunk.

After all skills are evaluated: set `status: "completed"`, proceed to Phase 3.

**Resume detection:** If `status: "in_progress"` is found on startup, resume from the first unevaluated skill.

Each skill is evaluated against this checklist:

```
- [ ] Content overlap with other skills checked
- [ ] Overlap with MEMORY.md / CLAUDE.md checked
- [ ] Freshness of technical references verified (use WebSearch if tool names / CLI flags / APIs are present)
- [ ] Usage frequency considered
- [ ] Structural pattern identified (see Skill Design Patterns below)
- [ ] Pattern applied correctly: steps are explicit, gating conditions present where needed, references/assets loaded at the right step
- [ ] Instructions do not try to cram multiple patterns into a single monolithic prompt
```

Verdict criteria:

| Verdict | Meaning |
|---------|---------|
| Keep | Useful and current |
| Improve | Worth keeping, but specific improvements needed |
| Update | Referenced technology is outdated (verify with WebSearch) |
| Retire | Low quality, stale, or cost-asymmetric |
| Merge into [X] | Substantial overlap with another skill; name the merge target |

Evaluation is **holistic AI judgment** — not a numeric rubric. Guiding dimensions:
- **Actionability**: code examples, commands, or steps that let you act immediately
- **Scope fit**: name, trigger, and content are aligned; not too broad or narrow
- **Uniqueness**: value not replaceable by MEMORY.md / CLAUDE.md / another skill
- **Currency**: technical references work in the current environment
- **Pattern fit**: skill uses a recognisable structural pattern; instructions are not a shapeless blob

**Reason quality requirements** — the `reason` field must be self-contained and decision-enabling:
- Do NOT write "unchanged" alone — always restate the core evidence
- For **Retire**: state (1) what specific defect was found, (2) what covers the same need instead
  - Bad: `"Superseded"`
  - Good: `"disable-model-invocation: true already set; superseded by continuous-learning-v2 which covers all the same patterns plus confidence scoring. No unique content remains."`
- For **Merge**: name the target and describe what content to integrate
  - Bad: `"Overlaps with X"`
  - Good: `"42-line thin content; Step 4 of chatlog-to-article already covers the same workflow. Integrate the 'article angle' tip as a note in that skill."`
- For **Improve**: describe the specific change needed (what section, what action, target size if relevant)
  - Bad: `"Too long"`
  - Good: `"276 lines; Section 'Framework Comparison' (L80–140) duplicates ai-era-architecture-principles; delete it to reach ~150 lines."`
  - Pattern violations are also valid Improve reasons — name the pattern that fits and what's missing (e.g. "Reviewer pattern: checklist is inlined as 40 prose lines — extract to references/review-checklist.md so it can be swapped independently")
- For **Keep** (mtime-only change in Quick Scan): restate the original verdict rationale, do not write "unchanged"
  - Bad: `"Unchanged"`
  - Good: `"mtime updated but content unchanged. Unique Python reference explicitly imported by rules/python/; no overlap found."`

### Phase 3 — Summary Table

| Skill | 7d use | Verdict | Reason |
|-------|--------|---------|--------|

### Phase 4 — Consolidation

1. **Retire / Merge**: present detailed justification per file before confirming with user:
   - What specific problem was found (overlap, staleness, broken references, etc.)
   - What alternative covers the same functionality (for Retire: which existing skill/rule; for Merge: the target file and what content to integrate)
   - Impact of removal (any dependent skills, MEMORY.md references, or workflows affected)
2. **Improve**: present specific improvement suggestions with rationale:
   - What to change and why (e.g., "trim 430→200 lines because sections X/Y duplicate python-patterns")
   - User decides whether to act
3. **Update**: present updated content with sources checked
4. Check MEMORY.md line count; propose compression if >100 lines

## Results File Schema

`~/.claude/skills/skill-stocktake/results.json`:

**`evaluated_at`**: Must be set to the actual UTC time of evaluation completion.
Obtain via Bash: `date -u +%Y-%m-%dT%H:%M:%SZ`. Never use a date-only approximation like `T00:00:00Z`.

```json
{
  "evaluated_at": "2026-02-21T10:00:00Z",
  "mode": "full",
  "batch_progress": {
    "total": 80,
    "evaluated": 80,
    "status": "completed"
  },
  "skills": {
    "skill-name": {
      "path": "~/.claude/skills/skill-name/SKILL.md",
      "verdict": "Keep",
      "reason": "Concrete, actionable, unique value for X workflow",
      "mtime": "2026-01-15T08:30:00Z"
    }
  }
}
```

## Notes

- Evaluation is blind: the same checklist applies to all skills regardless of origin (ECC, self-authored, auto-extracted)
- Archive / delete operations always require explicit user confirmation
- No verdict branching by skill origin

---

## Skill Design Patterns

These five patterns describe **how to structure the logic inside a SKILL.md**. Use them when writing new skills, and reference them when issuing Improve verdicts. Patterns compose — a Pipeline can embed a Reviewer step; a Generator can open with Inversion.

### Pattern 1 — Tool Wrapper

> Give the agent on-demand expertise for a specific library or domain.

**When to use:** Skills that apply conventions, best practices, or internal standards for a single technology (e.g. FastAPI, Terraform, a proprietary SDK).

**Structure:**
- Trigger on library-specific keywords
- Load reference docs from `references/` only when needed (lazy loading keeps context clean)
- Apply loaded rules as absolute truth

**Signs a skill needs this pattern:** monolithic system-prompt with hardcoded API conventions; no separation between "rules" and "instructions to apply rules".

**Good signals:** `references/conventions.md` loaded at step 1; instructions reference specific rule names, not prose summaries.

---

### Pattern 2 — Generator

> Produce consistent, structured documents from a reusable template.

**When to use:** Skills that output a predictable artefact on every run — API docs, commit messages, reports, changelogs, project scaffolds.

**Structure:**
1. Load style guide from `references/`
2. Load output template from `assets/`
3. Ask the user for any missing variables (topic, audience, data points)
4. Fill every template section following the style guide
5. Return a single completed document

**Signs a skill needs this pattern:** output format varies run-to-run; instructions contain an ad-hoc template embedded in the prose.

**Good signals:** `assets/` directory exists; Step 3 explicitly lists the variables to collect before generation begins.

---

### Pattern 3 — Reviewer

> Score a submission against a modular, swappable checklist.

**When to use:** Code review, security audit, PR feedback, design critique — any task that applies a rubric to user-submitted content.

**Structure:**
1. Load checklist from `references/review-checklist.md`
2. Read the submission carefully; understand intent before critiquing
3. Apply each checklist rule; for every violation record line, severity (`error` / `warning` / `info`), why it's a problem, and a concrete fix
4. Output: Summary → Findings (errors first) → Score → Top 3 recommendations

**Signs a skill needs this pattern:** checklist is inlined as prose in the instructions; no severity tiers; findings are listed without suggested fixes.

**Good signals:** checklist lives in `references/`; severity levels declared in frontmatter metadata; findings include corrected code snippets.

---

### Pattern 4 — Inversion

> The agent interviews the user before acting.

**When to use:** Tasks where acting on incomplete requirements produces wasted work — project planning, architecture design, complex document drafting.

**Structure:**
- Phase 1 — Problem Discovery: ask one question at a time, wait for each answer
- Phase 2 — Constraints: only after Phase 1 is fully answered
- Phase 3 — Synthesis: **DO NOT start building until all phases are complete**; load `assets/plan-template.md` and fill from gathered answers; confirm with user and iterate

**Signs a skill needs this pattern:** agent dives into generation immediately; requirements are guessed rather than confirmed; no multi-turn gating.

**Good signals:** explicit `DO NOT proceed until…` gate conditions between phases; questions are numbered and asked one at a time; synthesis step references a template loaded only at that point.

---

### Pattern 5 — Pipeline

> Enforce a strict, sequential workflow with hard checkpoints.

**When to use:** Complex multi-step tasks where skipping or reordering steps produces invalid output — documentation generation, deployment workflows, multi-stage data transforms.

**Structure:**
- Steps are numbered and labelled
- Each step loads only the references/assets it needs (keeps context window clean)
- **Gate conditions** between steps: agent explicitly forbidden from proceeding until the user (or a quality check) confirms
- Final step is always a quality check against `references/quality-checklist.md`

**Signs a skill needs this pattern:** steps are described as prose paragraphs with no explicit sequencing; no gate conditions; all references loaded upfront.

**Good signals:** `## Step N —` headings; "Do NOT proceed to Step N+1 until…" statements; different `references/` files loaded at different steps.

---

### Pattern decision guide

| Question | Pattern |
|----------|---------|
| "Apply this library's conventions to user code" | Tool Wrapper |
| "Always output the same document structure" | Generator |
| "Score/audit something against a rubric" | Reviewer |
| "I need requirements before I can act" | Inversion |
| "Multi-step workflow that must not skip" | Pipeline |
| Multiple of the above | Compose them |