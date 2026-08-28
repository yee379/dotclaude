---
name: closeout-prd
description: Feature close-out and documentation update. Runs after a feature lands — diffs what shipped, updates README/ARCHITECTURE/CONTRIBUTING/CLAUDE.md, polishes CHANGELOG voice, closes out todo/ task files, syncs TODO.md, optionally bumps VERSION, and tags the git tree when a bump lands. Use when asked to "update the docs", "close out this feature", "sync documentation", or "post-ship docs".
license: MIT
compatibility: opencode
---

# Plan Closeout: Feature Close-Out

## Workflow position

```
/draft-prd → /board-review → implementation
      │
      ▼
/closeout-prd         ← YOU ARE HERE: feature has landed — close out the task
      │                  file, sync TODO.md, apply all doc updates, polish
      │                  CHANGELOG voice, bump VERSION, tag the tree on a bump
      ▼
/prod-release
```

**The handoff from `/doc-review`:** That skill identified which docs need updating and added the work to the plan. This skill executes those updates after the code ships. If `doc-review` ran, check its output (look for plan amendments and the deferred-to-doc-release list) — use it as your starting checklist rather than discovering everything from scratch.

---

You are running the `/closeout-prd` workflow. This runs **after the feature has landed** (code
merged or about to merge). Your job: close out the feature cleanly — mark the task done, ensure
every documentation file in the project is accurate and up to date, and leave the project in a
state where the next contributor can orient themselves without asking questions.

**Model routing:** Auto-updates (factual corrections, path changes, count updates, marking TODOs complete) are **`haiku`-eligible**. Risky or narrative changes — rewrites, section removals, CHANGELOG voice polish, cross-doc contradictions — require **`sonnet`**. Never downgrade to Haiku for decisions you'd stop and ask the user about.

You are mostly automated. Make obvious factual updates directly. Stop and ask only for risky or
subjective decisions.

**Only stop for:**
- Risky/questionable doc changes (narrative, philosophy, security, removals, large rewrites)
- VERSION bump decision — every time, even if already bumped on the branch (see Step 8)
- New TODOS items to add
- Cross-doc contradictions that are narrative (not factual)

**Never stop for:**
- Factual corrections clearly from the diff
- Adding items to tables/lists
- Updating paths, counts, version numbers
- Fixing stale cross-references
- CHANGELOG voice polish (minor wording adjustments)
- Marking TODOS complete
- Cross-doc factual inconsistencies (e.g., version number mismatch)

**NEVER do:**
- Overwrite, replace, or regenerate CHANGELOG entries — polish wording only, preserve all content
- Bump VERSION without asking — always use AskUserQuestion for version changes
- Use `Write` tool on CHANGELOG.md — always use `Edit` with exact `old_string` matches

---

## Step 1: Pre-flight & Diff Analysis

1. Check the current branch. If on the base branch, **abort**: "You're on the base branch. Run from a feature branch."

2. Gather context about what changed:

```bash
git diff <base>...HEAD --stat
```

```bash
git log <base>..HEAD --oneline
```

```bash
git diff <base>...HEAD --name-only
```

3. Discover all documentation files in the repo:

```bash
find . -maxdepth 2 -name "*.md" -not -path "./.git/*" -not -path "./node_modules/*" | sort
```

4. Classify the changes into categories relevant to documentation:
   - **New features** — new files, new commands, new skills, new capabilities
   - **Changed behavior** — modified services, updated APIs, config changes
   - **Removed functionality** — deleted files, removed commands
   - **Infrastructure** — build system, test infrastructure, CI

5. Output a brief summary: "Analyzing N files changed across M commits. Found K documentation files to review."

---

## Step 2: Per-File Documentation Audit

Read each documentation file and cross-reference it against the diff. Use these generic heuristics
(adapt to whatever project you're in):

**README.md:**
- Does it describe all features and capabilities visible in the diff?
- Are install/setup instructions consistent with the changes?
- Are examples, demos, and usage descriptions still valid?
- Are troubleshoot steps still accurate?

**ARCHITECTURE.md:**
- Do ASCII diagrams and component descriptions match the current code?
- Are design decisions and "why" explanations still accurate?
- Be conservative — only update things clearly contradicted by the diff. Architecture docs
  describe things unlikely to change frequently.

**CONTRIBUTING.md — New contributor smoke test:**
- Walk through the setup instructions as if you are a brand new contributor.
- Are the listed commands accurate? Would each step succeed?
- Do test tier descriptions match the current test infrastructure?
- Are workflow descriptions (dev setup, contributor mode, etc.) current?
- Flag anything that would fail or confuse a first-time contributor.

**CLAUDE.md / project instructions:**
- Does the project structure section match the actual file tree?
- Are listed commands and scripts accurate?
- Do build/test instructions match what's in package.json (or equivalent)?

**Any other .md files:**
- Read the file, determine its purpose and audience.
- Cross-reference against the diff to check if it contradicts anything the file says.

For each file, classify needed updates as:

- **Auto-update** — Factual corrections clearly warranted by the diff: adding an item to a
  table, updating a file path, fixing a count, updating a project structure tree.
- **Ask user** — Narrative changes, section removal, security model changes, large rewrites
  (more than ~10 lines in one section), ambiguous relevance, adding entirely new sections.

---

## Step 3: Apply Auto-Updates

Make all clear, factual updates directly using the Edit tool.

For each file modified, output a one-line summary describing **what specifically changed** — not
just "Updated README.md" but "README.md: added /new-skill to skills table, updated skill count
from 9 to 10."

**Never auto-update:**
- README introduction or project positioning
- ARCHITECTURE philosophy or design rationale
- Security model descriptions
- Do not remove entire sections from any document

---

## Step 4: Ask About Risky/Questionable Changes

For each risky or questionable update identified in Step 2, use AskUserQuestion with:
- Context: project name, branch, which doc file, what we're reviewing
- The specific documentation decision
- `RECOMMENDATION: Choose [X] because [one-line reason]`
- Options including C) Skip — leave as-is

Apply approved changes immediately after each answer.

---

## Step 5: CHANGELOG Voice Polish

**CRITICAL — NEVER CLOBBER CHANGELOG ENTRIES.**

This step polishes voice. It does NOT rewrite, replace, or regenerate CHANGELOG content.

A real incident occurred where an agent replaced existing CHANGELOG entries when it should have
preserved them. This skill must NEVER do that.

**Rules:**
1. Read the entire CHANGELOG.md first. Understand what is already there.
2. Only modify wording within existing entries. Never delete, reorder, or replace entries.
3. Never regenerate a CHANGELOG entry from scratch. The entry was written by `/ship` from the
   actual diff and commit history. It is the source of truth. You are polishing prose, not
   rewriting history.
4. If an entry looks wrong or incomplete, use AskUserQuestion — do NOT silently fix it.
5. Use Edit tool with exact `old_string` matches — never use Write to overwrite CHANGELOG.md.

**If CHANGELOG was not modified in this branch:** skip this step.

**If CHANGELOG was modified in this branch**, review the entry for voice:

- **Sell test:** Would a user reading each bullet think "oh nice, I want to try that"? If not,
  rewrite the wording (not the content).
- Lead with what the user can now **do** — not implementation details.
- "You can now..." not "Refactored the..."
- Flag and rewrite any entry that reads like a commit message.
- Internal/contributor changes belong in a separate "### For contributors" subsection.
- Auto-fix minor voice adjustments. Use AskUserQuestion if a rewrite would alter meaning.

---

## Step 6: Cross-Doc Consistency & Discoverability Check

After auditing each file individually, do a cross-doc consistency pass:

1. Does the README's feature/capability list match what CLAUDE.md (or project instructions) describes?
2. Does ARCHITECTURE's component list match CONTRIBUTING's project structure description?
3. Does CHANGELOG's latest version match the VERSION file?
4. **Discoverability:** Is every documentation file reachable from README.md or CLAUDE.md? If
   ARCHITECTURE.md exists but neither README nor CLAUDE.md links to it, flag it. Every doc
   should be discoverable from one of the two entry-point files.
5. Flag any contradictions between documents. Auto-fix clear factual inconsistencies (e.g., a
   version mismatch). Use AskUserQuestion for narrative contradictions.

---

## Step 7: TODO Cleanup

The canonical TODO format is defined by the `/prd-workflow` skill: a `TODO.md` priority
index plus individual task files in `todo/<n>-<slug>.md`. If neither exists, skip this step.

1. **Completed task files not yet marked:** Cross-reference the diff against `todo/*.md` files
   with status `🔄 In Progress` or `👀 In Review`. If a task file is clearly completed by the
   changes in this branch, update its status to `✅ Done`, set `**Shipped:**` to today's date,
   and tick any remaining checklist items. Be conservative — only mark done with clear evidence
   in the diff.

2. **Sync `TODO.md`:** For every task file status change made in step 1, update the corresponding
   row in `TODO.md` to match (status column, PR column if missing). `TODO.md` must never lag the
   task files.

3. **Stale task file descriptions:** If a task file references files or components that were
   significantly renamed or restructured by the diff, its description may be stale. Use
   AskUserQuestion to confirm whether the task file should be updated, completed, or left as-is.

4. **New deferred work:** Check the diff for `TODO`, `FIXME`, `HACK`, and `XXX` comments. For
   each one that represents meaningful deferred work (not a trivial inline note), use
   AskUserQuestion to ask whether it should be captured as a new `todo/<n>-<slug>.md` entry and
   added to `TODO.md`.

---

## Step 8: VERSION Bump Question

**CRITICAL — NEVER BUMP VERSION WITHOUT ASKING.** This applies every time, including when a
bump has already happened on the branch — re-confirm rather than defaulting to "no change
needed" or silently picking a bump size on the user's behalf.

1. **If VERSION does not exist:** Skip silently.

2. Check if VERSION was already modified on this branch:

```bash
git diff <base>...HEAD -- VERSION
```

3. **Classify the change size before asking**, regardless of whether VERSION was already
   bumped. Read `git diff <base>...HEAD --stat` and `git diff <base>...HEAD --name-only`
   and judge:

   - **Small (→ PATCH, X.Y.Z+1):** bug fixes, a single new endpoint/field/flag, validation
     tightening, log/metric additions, doc-only changes shipped alongside code, dependency
     bumps, anything that doesn't change how the service is used or add a new capability.
   - **Big (→ MINOR, X.Y+1.0):** a new feature, a new user-facing capability, a behavior
     change significant enough to need its own CHANGELOG story, multiple related small
     changes that together add up to a meaningful release, or anything the user would want
     called out on its own in a release announcement.

   This is a judgment call, not a mechanical line count — a one-line change that flips a
   security-relevant default is "big"; a 200-line refactor with no behavior change is
   "small". State the classification and the reasoning in the question itself so the user is
   confirming a stated judgment, not guessing what you were thinking.

4. **If VERSION was NOT bumped:** Use AskUserQuestion, with the classification from step 3
   driving the recommendation:
   - RECOMMENDATION: **A** if step 3 classified the change as small, **B** if big
   - A) Bump PATCH (X.Y.Z+1) — small change: `<one-line reason from step 3>`
   - B) Bump MINOR (X.Y+1.0) — big change: `<one-line reason from step 3>`
   - C) Skip — no version bump needed

5. **If VERSION was already bumped:** Do NOT skip silently. Check whether the existing bump
   still covers the full scope of changes on this branch:

   a. Read the CHANGELOG entry for the current VERSION. What features does it describe?
   b. Compare against the full diff from step 3. Are there significant changes (new
      features, new skills, new commands, major refactors) NOT mentioned in the CHANGELOG
      entry for the current version?
   c. **If the CHANGELOG entry covers everything:** Skip — output "VERSION: Already bumped to
      vX.Y.Z, covers all changes."
   d. **If there are significant uncovered changes:** classify *those specific uncovered
      changes* by the same small/big rule from step 3, then use AskUserQuestion explaining
      what the current version covers vs what's new:
      - RECOMMENDATION: **A** if the uncovered changes are small, **B** if big
      - A) Bump to next patch (X.Y.Z+1) — small: `<reason>`
      - B) Bump to next minor (X.Y+1.0) — big: `<reason>`
      - C) Keep current version — add new changes to the existing CHANGELOG entry
      - D) Skip — leave version as-is, handle later

   The key insight: a VERSION bump set for "feature A" should not silently absorb "feature B"
   if feature B is substantial enough to deserve its own version entry — and the size of
   that entry (patch vs minor) is itself a judgment call to surface, not assume.

---

## Step 8b: Tag the Git Tree on a VERSION Bump

**Only runs if Step 8 resulted in an actual VERSION bump on this branch** (a fresh bump in
this session, or a prior bump on the branch confirmed in Step 8.4 to still be current). Skip
silently if Step 8 was skipped or if VERSION does not exist.

**Known gap — this rule is scoped to the `/closeout-prd` flow only.** A VERSION bump made
outside this skill (e.g. a hotfix landed via `/troubleshoot` or any other ad hoc change) will
not get tagged automatically — there is no repo-wide hook enforcing "every VERSION-touching
commit gets a tag." If you bump VERSION outside `/closeout-prd`, apply this same procedure
(tag name derivation, collision check, annotated tag, no auto-push) by hand.

1. **Determine the tag name.** If the VERSION file lives at the repo root, the tag is
   `v<VERSION>` (e.g. `v0.18.0`). If the VERSION file lives inside a subdirectory (a
   monorepo with multiple independently-versioned services/packages), prefix the tag with
   that directory's basename so tags from different components never collide:
   `<dirname>-v<VERSION>` (e.g. `s3df-authnz-service-v0.18.0`). Detect the case by checking
   whether the VERSION file's parent directory is the git root:

   ```bash
   VERSION_DIR="$(dirname "$(git ls-files --full-name '**/VERSION' | head -1)")"
   if [ "$VERSION_DIR" = "." ]; then
     TAG="v$(cat VERSION)"
   else
     TAG="$(basename "$VERSION_DIR")-v$(cat "$VERSION_DIR/VERSION")"
   fi
   ```

2. **Check for a collision** before tagging — a version bump that reuses an already-tagged
   number is itself a bug worth surfacing, not silently overwriting:

   ```bash
   git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && echo "COLLISION"
   ```

   If a collision is found, do not tag. Warn: "Tag `$TAG` already exists (pointing at
   `<sha>`) — VERSION was bumped to a number already tagged. Confirm the VERSION bump is
   correct before retagging manually." and continue with the rest of Step 9 without tagging.

3. **Create an annotated tag** (not lightweight) once the version-bump commit from Step 9
   exists, so the tag points at the commit that actually contains the VERSION file change,
   not a prior commit:

   ```bash
   git tag -a "$TAG" -m "$TAG

   <one-line summary of what this version bump covers, drawn from the CHANGELOG
   entry or commit message Step 9 just wrote>"
   ```

4. **Do not push the tag automatically.** Pushing a tag is a release action with its own
   blast radius (can trigger CI/CD, container builds, deploy pipelines) and belongs to
   `/prod-release`, not this skill. Report the tag was created locally and how to push it:

   ```
   Tagged $TAG locally. Push when ready to release: git push origin $TAG
   ```

5. **If `git tag` fails for any reason** (dirty tree, detached HEAD, no commits yet): warn
   and continue — a failed tag must never block the rest of the closeout.

---

## Step 9: Commit & Output

**Empty check first:** Run `git status` (never use `-uall`). If no documentation files were
modified by any previous step, output "All documentation is up to date." and exit without
committing.

**Commit:**

Stage and commit following the git discipline in `/prd-workflow` (stage by name, one
concern per commit). Use `docs:` as the commit type:

```
docs: update project documentation for vX.Y.Z.W
```

Push to the current branch:

```bash
git push
```

**PR body update (idempotent, race-safe):**

1. Read the existing PR body into a PID-unique tempfile:

```bash
gh pr view --json body -q .body > /tmp/pr-body-$$.md
```

2. If the tempfile already contains a `## Documentation` section, replace that section with the
   updated content. If it does not contain one, append a `## Documentation` section at the end.

3. The Documentation section should include a **doc diff preview** — for each file modified,
   describe what specifically changed (e.g., "README.md: added /document-release to skills
   table, updated skill count from 9 to 10").

4. Write the updated body back:

```bash
gh pr edit --body-file /tmp/pr-body-$$.md
```

5. Clean up the tempfile:

```bash
rm -f /tmp/pr-body-$$.md
```

6. If `gh pr view` fails (no PR exists): skip with message "No PR found — skipping body update."
7. If `gh pr edit` fails: warn "Could not update PR body — documentation changes are in the
   commit." and continue.

**Structured doc health summary (final output):**

Output a scannable summary showing every documentation file's status:

```
Documentation health:
  README.md       [status] ([details])
  ARCHITECTURE.md [status] ([details])
  CONTRIBUTING.md [status] ([details])
  CHANGELOG.md    [status] ([details])
  TODO.md         [status] ([details])
  VERSION         [status] ([details])
  Git tag         [status] ([details])
```

Where status is one of:
- Updated — with description of what changed
- Current — no changes needed
- Voice polished — wording adjusted
- Not bumped — user chose to skip
- Already bumped — version was set by /ship
- Skipped — file does not exist

`Git tag` status is one of: `Created <tag> (not pushed)`, `Skipped — no VERSION bump`,
`Collision — <tag> already exists`, or `Failed — <reason>`.

---

## Important Rules

- **Read before editing.** Always read the full content of a file before modifying it.
- **Never clobber CHANGELOG.** Polish wording only. Never delete, replace, or regenerate entries.
- **Never bump VERSION silently.** Always ask, every time — even if already bumped, check whether it covers the full scope of changes. Never pick patch-vs-minor on the user's behalf; classify the change size, state your reasoning, and let the recommendation in AskUserQuestion reflect it, but the user makes the final call.
- **Tag locally, never push automatically.** A VERSION bump gets an annotated git tag as part of this skill's normal flow — but pushing that tag (which can trigger CI/CD, image builds, or deploys) is `/prod-release`'s call, not this skill's.
- **Be explicit about what changed.** Every edit gets a one-line summary.
- **Generic heuristics, not project-specific.** The audit checks work on any repo.
- **Discoverability matters.** Every doc file should be reachable from README or CLAUDE.md.
- **Voice: friendly, user-forward, not obscure.** Write like you're explaining to a smart person
  who hasn't seen the code.