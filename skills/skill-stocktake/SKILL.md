---
name: skill-stocktake
description: "Use when auditing Claude skills and commands for quality. Supports Quick Scan (changed skills only) and Full Stocktake modes with sequential subagent batch evaluation."
origin: ECC
---

# skill-stocktake

Audits all Claude skills and commands using a quality checklist plus holistic AI judgment.

## Scope and modes

Targets, relative to the invocation directory: `~/.claude/skills/` (global) and
`{cwd}/.claude/skills/` (project-level, if present). To include a project's skills, run from its
root. **Phase 1 explicitly lists which paths were found and scanned.**

| Mode | Trigger | Duration |
|------|---------|---------|
| Quick Scan | `results.json` exists (default) | 5–10 min |
| Full Stocktake | `results.json` absent, or `/skill-stocktake full` | 20–30 min |

Results cache: `~/.claude/skills/skill-stocktake/results.json`.

**Path expansion — applies everywhere below.** Scan output uses `~`-prefixed paths. Subagents may
resolve `~` to `/root/` rather than the current user's home, so **always expand to absolute paths
before putting them in a subagent prompt**:

```bash
echo "$SCAN_OUTPUT" | sed "s|~|$HOME|g"
```

Both scripts auto-detect the project dir from `$PWD/.claude/skills`; pass it explicitly only if
needed.

## Quick Scan

1. Read `results.json`.
2. `bash ~/.claude/skills/skill-stocktake/scripts/quick-diff.sh ~/.claude/skills/skill-stocktake/results.json`
3. Output `[]` → report "No changes since last run." and stop.
4. Re-evaluate only the changed files against the Phase 2 criteria; carry forward unchanged
   skills from the previous results; output only the diff.
5. `bash ~/.claude/skills/skill-stocktake/scripts/save-results.sh ~/.claude/skills/skill-stocktake/results.json <<< "$EVAL_RESULTS"`

## Full Stocktake

### Phase 1 — Inventory

`bash ~/.claude/skills/skill-stocktake/scripts/scan.sh` enumerates skill files, extracts
frontmatter, and collects UTC mtimes. Present its scan summary and inventory table:

```
Scanning:
  ✓ ~/.claude/skills/         (17 files)
  ✗ {cwd}/.claude/skills/    (not found — global skills only)
```

| Skill | 7d use | 30d use | Description |
|-------|--------|---------|-------------|

### Phase 2 — Quality evaluation

Read `references/skill-design-patterns.md` and include its contents verbatim as `[PATTERNS]`.
Then launch a general-purpose subagent:

```text
Agent(
  subagent_type="general-purpose",
  prompt="
Evaluate the following skill inventory against the checklist.

[INVENTORY]

[CHECKLIST]

[PATTERNS]

Return JSON for each skill:
{ \"verdict\": \"Keep\"|\"Improve\"|\"Update\"|\"Retire\"|\"Merge into [X]\", \"reason\": \"...\" }
"
)
```

**~20 skills per invocation** to keep context manageable. Save intermediate results to
`results.json` with `status: "in_progress"` after each chunk; set `"completed"` when done. On
startup, `status: "in_progress"` means resume from the first unevaluated skill.

**Checklist:**

```
- [ ] Content overlap with other skills checked
- [ ] Overlap with MEMORY.md / CLAUDE.md checked
- [ ] Freshness of technical references verified (WebSearch if tool names / CLI flags / APIs are present)
- [ ] Usage frequency considered
- [ ] Structural pattern identified (see references/skill-design-patterns.md)
- [ ] Pattern applied correctly: steps explicit, gating conditions present where needed,
      references/assets loaded at the right step
- [ ] Instructions do not cram multiple patterns into one monolithic prompt
- [ ] Conciseness assessed: motivational preamble, repeated examples, prose that could be
      bullets, and inline templates >20 lines are flagged
```

**Verdicts:**

| Verdict | Meaning |
|---------|---------|
| Keep | Useful and current |
| Improve | Worth keeping, but specific improvements needed |
| Update | Referenced technology is outdated (verify with WebSearch) |
| Retire | Low quality, stale, or cost-asymmetric |
| Merge into [X] | Substantial overlap with another skill; name the target |

Evaluation is **holistic judgment, not a numeric rubric.** Dimensions: **actionability** (examples,
commands, or steps you can act on immediately) · **scope fit** (name, trigger, and content
aligned; not too broad or narrow) · **uniqueness** (not replaceable by MEMORY.md, CLAUDE.md, or
another skill) · **currency** (references work in the current environment) · **pattern fit** (a
recognisable structure, not a shapeless blob) · **conciseness** (every line earns its place —
right-size by pattern: Tool Wrapper 50–100 lines, Reviewer/Inversion 60–120, Generator/Pipeline
100–200).

### Reason quality

The `reason` field must be self-contained and decision-enabling. **Never write "unchanged" alone**
— always restate the core evidence.

| Verdict | Requirement | Bad → Good |
|---|---|---|
| Retire | The specific defect found, and what covers the same need | `"Superseded"` → `"disable-model-invocation: true already set; superseded by continuous-learning-v2, which covers the same patterns plus confidence scoring. No unique content remains."` |
| Merge | The target, and what content to integrate | `"Overlaps with X"` → `"42-line thin content; Step 4 of chatlog-to-article already covers this workflow. Integrate the 'article angle' tip as a note there."` |
| Improve | The section, the action, and the target size | `"Too long"` → `"276 lines; 'Framework Comparison' (L80–140) duplicates ai-era-architecture-principles; delete to reach ~150 lines."` |
| Keep (mtime-only) | The original rationale, restated | `"Unchanged"` → `"mtime updated, content unchanged. Unique Python reference imported by rules/python/; no overlap found."` |

A pattern violation is a valid Improve reason — name the pattern that fits and what's missing:
*"Reviewer pattern: checklist is inlined as 40 prose lines — extract to
references/review-checklist.md so it can be swapped independently."*

**Condensation moves**, in order, for any length or verbosity finding. Name the moves and the
target line count:

1. **Delete** — motivational preamble, "Remember:" footers, examples repeating a pattern already shown
2. **Move to `references/`** — inline templates >20 lines, large checklists, reference tables, so
   they lazy-load
3. **Collapse** — three examples making the same point → one annotated representative
4. **Convert** — narrative prose → a checklist item or a gate condition

Example: *"380 lines; preamble (L1–15) is motivational — delete; inline template (L120–190) →
assets/plan-template.md; three equivalent mock examples (L200–260) collapse to one. Target:
~180 lines."*

### Phase 3 — Summary

| Skill | 7d use | Verdict | Reason |
|-------|--------|---------|--------|

### Phase 4 — Consolidation

1. **Retire / Merge** — per file, before confirming with the user: the specific problem found
   (overlap, staleness, broken references), what alternative covers the same functionality
   (which skill, or the merge target and content to integrate), and the impact of removal
   (dependent skills, MEMORY.md references, affected workflows).
2. **Improve** — the specific change and why; for length findings, apply the condensation moves
   above and state the target. The user decides whether to act.
3. **Update** — present updated content with sources checked.
4. Check MEMORY.md line count; propose compression if over 100 lines.

## Results schema

`evaluated_at` must be the actual UTC completion time from `date -u +%Y-%m-%dT%H:%M:%SZ` — never
a date-only approximation like `T00:00:00Z`.

```json
{
  "evaluated_at": "2026-02-21T10:00:00Z",
  "mode": "full",
  "batch_progress": { "total": 80, "evaluated": 80, "status": "completed" },
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

- **Evaluation is blind** — the same checklist applies regardless of origin (ECC, self-authored,
  auto-extracted). No verdict branching by origin.
- Archive and delete operations always require explicit user confirmation.
- `references/skill-design-patterns.md` is also worth loading when writing a new skill, to choose
  the right pattern.
