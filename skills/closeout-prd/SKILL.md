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
/closeout-prd   ← YOU ARE HERE: close out the task file, sync TODO.md, apply doc
      │           updates, polish CHANGELOG voice, bump VERSION, tag on a bump
      ▼
/prod-release
```

Runs **after the feature has landed**. Close out the feature cleanly: mark the task done, make
every documentation file accurate, and leave the project so the next contributor can orient
themselves without asking questions.

**Handoff from `/doc-review`:** that skill identified which docs need updating and added the work
to the plan. If it ran, use its output (plan amendments, deferred-to-doc-release list) as your
starting checklist rather than rediscovering everything.

**Model routing:** factual auto-updates (path changes, count updates, marking TODOs complete) are
**`haiku`-eligible**. Rewrites, section removals, CHANGELOG voice polish, and cross-doc
contradictions require **`sonnet`**. Never downgrade to Haiku for a decision you would stop and
ask about.

---

## Operating rules

Mostly automated. Make obvious factual updates directly; stop only for risky or subjective calls.

| | |
|---|---|
| **Stop for** | Risky doc changes (narrative, philosophy, security, removals, rewrites >~10 lines in one section) · VERSION bump not already decided this session (Step 8) · new TODO items · *narrative* cross-doc contradictions |
| **Never stop for** | Factual corrections clear from the diff · adding items to tables/lists · paths, counts, version numbers · stale cross-references · minor CHANGELOG voice polish · marking TODOs complete · factual cross-doc inconsistencies |

Three hard rules, in force throughout:

1. **Never clobber the CHANGELOG.** Polish wording only — never delete, reorder, replace, or
   regenerate an entry. Use `Edit` with exact `old_string` matches; never `Write` on CHANGELOG.md.
   An agent once replaced existing entries it should have preserved; this skill must not.
2. **Never bump VERSION silently** — but a decision already given is not a question still open
   (Step 8).
3. **Tag locally, never push.** Pushing a tag can trigger CI/CD, image builds, and deploys —
   that is `/prod-release`'s call.

Always read a file's full content before modifying it. Every edit gets a one-line summary saying
**what specifically changed** — "README.md: added /new-skill to skills table, updated count 9→10",
not "Updated README.md". Audit heuristics are generic and must work on any repo. Voice: friendly
and user-forward, written for a smart person who has not seen the code.

---

## Step 1: Pre-flight & diff analysis

If on the base branch, **abort**: "You're on the base branch. Run from a feature branch."

```bash
git diff <base>...HEAD --stat
git log <base>..HEAD --oneline
git diff <base>...HEAD --name-only
find . -maxdepth 2 -name "*.md" -not -path "./.git/*" -not -path "./node_modules/*" | sort
```

Classify the changes as **new features** (new files, commands, skills, capabilities), **changed
behaviour** (modified services, APIs, config), **removed functionality**, or **infrastructure**
(build, test, CI).

Output: "Analyzing N files changed across M commits. Found K documentation files to review."

---

## Step 2: Per-file documentation audit

Read each doc file and cross-reference against the diff.

**README.md** — does it describe every feature visible in the diff? Are install/setup
instructions, examples, demos, and troubleshooting steps still valid?

**ARCHITECTURE.md** — do ASCII diagrams and component descriptions match the code? Are the "why"
explanations still accurate? Be conservative: only update what the diff clearly contradicts.

**CONTRIBUTING.md** — walk the setup instructions as a brand new contributor. Are the commands
accurate? Would each step succeed? Do test tier descriptions match the current infrastructure?
Flag anything that would fail or confuse a first-timer.

**CLAUDE.md / project instructions** — does the project structure section match the real file
tree? Are listed commands and scripts accurate? Do build/test instructions match `package.json`
or equivalent?

**Any other `.md`** — determine its purpose and audience, then check whether the diff contradicts
it.

Classify each needed update as **auto-update** (factual: a table row, a path, a count, a structure
tree) or **ask user** (narrative, section removal, security model, large rewrite, ambiguous
relevance, an entirely new section).

---

## Step 3: Apply auto-updates

Make all clear factual updates with `Edit`. **Never auto-update** the README introduction or
project positioning, ARCHITECTURE philosophy or design rationale, or security model descriptions —
and never remove an entire section from any document.

---

## Step 4: Ask about risky changes

For each risky update from Step 2, use AskUserQuestion with: the context (project, branch, file,
what is under review), the specific decision, `RECOMMENDATION: Choose [X] because [one-line
reason]`, and an option `C) Skip — leave as-is`. Apply approved changes immediately after each
answer.

---

## Step 5: CHANGELOG voice polish

Skip if CHANGELOG was not modified on this branch. Otherwise read the whole file first, then
review the new entry for voice — under rule 1 above, which is absolute.

- **Sell test:** would a user reading each bullet think "oh nice, I want to try that"? If not,
  rewrite the wording, not the content.
- Lead with what the user can now **do**: "You can now…", not "Refactored the…".
- Rewrite any entry that reads like a commit message.
- Internal/contributor changes go in a separate `### For contributors` subsection.
- Auto-fix minor voice adjustments; use AskUserQuestion if a rewrite would alter meaning, or if an
  entry looks wrong or incomplete. The entry was written by `/ship` from the real diff and commit
  history — it is the source of truth, and you are polishing prose, not rewriting history.

---

## Step 6: Cross-doc consistency & discoverability

1. Does README's capability list match CLAUDE.md's?
2. Does ARCHITECTURE's component list match CONTRIBUTING's project structure?
3. Does CHANGELOG's latest version match the VERSION file?
4. **Discoverability:** is every doc file reachable from README.md or CLAUDE.md? An
   ARCHITECTURE.md that neither links to is a finding.
5. Auto-fix clear factual inconsistencies; AskUserQuestion for narrative contradictions.

---

## Step 7: TODO cleanup

Canonical format is `/prd-workflow`'s: a `TODO.md` priority index plus task files in
`todo/<n>-<slug>.md`. If neither exists, skip.

1. **Completed but unmarked:** cross-reference the diff against `todo/*.md` files at `🔄 In
   Progress` or `👀 In Review`. Where clearly completed by this branch, set status `✅ Done`, set
   `**Shipped:**` to today, and tick remaining checklist items. Be conservative — clear diff
   evidence only.
2. **Sync `TODO.md`** for every status change (status column, PR column if missing). `TODO.md`
   must never lag the task files.
3. **Stale descriptions:** if a task file references files or components the diff significantly
   renamed or restructured, AskUserQuestion whether to update, complete, or leave it.
4. **New deferred work:** check the diff for `TODO`, `FIXME`, `HACK`, `XXX`. For each representing
   meaningful deferred work, AskUserQuestion whether to capture it as a new
   `todo/<n>-<slug>.md` and add it to `TODO.md`.

---

## Step 8: VERSION bump

Skip silently if VERSION does not exist.

**The decision, not the question, is what is required.** If the user named a version or bump size
**in this session** ("bump to 0.3.0", "make it a minor", "patch it"), that *is* the decision — do
not put it to them twice. Instead:

- Still classify the change size and **state the classification and reasoning in one line** before
  applying. That is what the question existed to surface.
- **If your classification disagrees** — they said patch and the diff removes a public command —
  say so in a sentence, then apply what they asked for. A disagreement they can overrule is the
  goal; blocking on it is not.
- **If the named version is not a legal successor** (already tagged, lower than current,
  malformed), stop and say so. That is a different question and has not been settled.

A bump made on the branch by tooling is **not** a decision.

**Classify the change size** from `git diff <base>...HEAD --stat` and `--name-only`, regardless of
whether VERSION was already bumped:

- **Small → PATCH (X.Y.Z+1):** bug fixes, a single new endpoint/field/flag, validation tightening,
  log/metric additions, doc-only changes alongside code, dependency bumps — anything that does not
  change how the service is used or add a capability.
- **Big → MINOR (X.Y+1.0):** a new feature or user-facing capability, a behaviour change needing
  its own CHANGELOG story, several small changes that together make a meaningful release, or
  anything worth calling out in a release announcement.

A judgement call, not a line count: a one-line change flipping a security-relevant default is
big; a 200-line refactor with no behaviour change is small. State the classification and reasoning
in the question, so the user confirms a stated judgement rather than guessing yours.

Then check `git diff <base>...HEAD -- VERSION`:

**Not bumped** — AskUserQuestion, recommendation driven by the classification (**A** if small,
**B** if big):
- A) Bump PATCH (X.Y.Z+1) — small change: `<reason>`
- B) Bump MINOR (X.Y+1.0) — big change: `<reason>`
- C) Skip — no version bump needed

**Already bumped** — do not skip silently. Read the CHANGELOG entry for the current VERSION and
compare against the full diff. If the entry covers everything, output "VERSION: Already bumped to
vX.Y.Z, covers all changes." If significant changes are uncovered, classify *those* by the same
rule and ask:
- A) Bump to next patch (X.Y.Z+1) — small: `<reason>`
- B) Bump to next minor (X.Y+1.0) — big: `<reason>`
- C) Keep current version — add new changes to the existing CHANGELOG entry
- D) Skip — leave as-is, handle later

A bump set for "feature A" should not silently absorb "feature B" if B deserves its own entry —
and patch-vs-minor for it is itself a judgement to surface, not assume.

---

## Step 8b: Tag the git tree on a bump

Runs only if Step 8 produced an actual bump on this branch (fresh, or a prior branch bump
confirmed still current). Skip silently otherwise.

**Known gap:** this rule is scoped to `/closeout-prd`. A VERSION bump made elsewhere (a hotfix via
`/troubleshoot`, any ad hoc change) is not tagged automatically — there is no repo-wide hook. Apply
this same procedure by hand in that case.

1. **Derive the tag name.** Root VERSION → `v<VERSION>`. VERSION inside a subdirectory (monorepo
   with independently-versioned components) → `<dirname>-v<VERSION>`, so component tags cannot
   collide:

   ```bash
   VERSION_DIR="$(dirname "$(git ls-files --full-name '**/VERSION' | head -1)")"
   if [ "$VERSION_DIR" = "." ]; then
     TAG="v$(cat VERSION)"
   else
     TAG="$(basename "$VERSION_DIR")-v$(cat "$VERSION_DIR/VERSION")"
   fi
   ```

2. **Check for a collision** — a bump reusing an already-tagged number is itself a bug worth
   surfacing:

   ```bash
   git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && echo "COLLISION"
   ```

   On collision, do not tag. Warn: "Tag `$TAG` already exists (pointing at `<sha>`) — VERSION was
   bumped to a number already tagged. Confirm the bump is correct before retagging manually," then
   continue the closeout without tagging.

3. **Create an annotated tag** (not lightweight) *after* Step 9's commit exists, so it points at
   the commit containing the VERSION change:

   ```bash
   git tag -a "$TAG" -m "$TAG

   <one-line summary of what this bump covers, from the CHANGELOG entry or Step 9's commit message>"
   ```

4. **Do not push it.** Report: `Tagged $TAG locally. Push when ready to release: git push origin $TAG`

5. **If `git tag` fails** (dirty tree, detached HEAD, no commits): warn and continue — a failed tag
   must never block the closeout.

---

## Step 9: Commit & output

**Empty check first:** run `git status` (never `-uall`). If no doc files were modified, output
"All documentation is up to date." and exit without committing.

Stage and commit per the git discipline in `/prd-workflow` (stage by name, one concern per
commit), using type `docs:`:

```
docs: update project documentation for vX.Y.Z.W
```

Then `git push`.

**PR body update (idempotent, race-safe):**

```bash
gh pr view --json body -q .body > /tmp/pr-body-$$.md
# replace an existing ## Documentation section, or append one
gh pr edit --body-file /tmp/pr-body-$$.md
rm -f /tmp/pr-body-$$.md
```

The `## Documentation` section includes a **doc diff preview** — per file, what specifically
changed. If `gh pr view` fails: "No PR found — skipping body update." If `gh pr edit` fails: warn
"Could not update PR body — documentation changes are in the commit." and continue.

**Final output — doc health summary:**

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

Status: `Updated` (with what changed) · `Current` · `Voice polished` · `Not bumped` (user skipped)
· `Already bumped` (set by /ship) · `Skipped` (file absent).

`Git tag`: `Created <tag> (not pushed)` · `Skipped — no VERSION bump` · `Collision — <tag> already
exists` · `Failed — <reason>`.
