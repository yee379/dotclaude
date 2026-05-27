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
