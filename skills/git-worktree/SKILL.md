---
name: git-worktree
description: Isolate every work stream in its own git worktree branched off main — create the worktree, commit as work completes, merge back, then remove the worktree and delete the branch. Use when starting any implementation task, running parallel agents, or cleaning up stale worktrees and branches.
origin: local
---

# Git Worktree Workflow

One worktree per work stream, each on its own new branch off `main`. Never mix unrelated tasks,
parallel agents, or independent features in one working tree. See `agentic-standards` § Work
Isolation & Commit Discipline for the commit cadence and message format this workflow assumes.

A branch cannot be checked out in two worktrees at once. That constraint is the point: it stops
parallel agents colliding on the same branch.

## When to use

- Starting any implementation task — feature, bug fix, refactor.
- Running parallel agents on independent work.
- Cleaning up worktrees and branches left behind by earlier sessions.

## When not to use

- Single-file documentation or config edits the user is watching live.
- The repository is not a git repository, and no `WorktreeCreate`/`WorktreeRemove` hooks exist.
- The user asked only to switch branches. Use `git switch`.

## Two ways in

**Harness tool, for the current session.** `EnterWorktree` creates a worktree under
`.claude/worktrees/` on a new branch and moves the session into it. The base ref comes from the
`worktree.baseRef` setting: `fresh` (the default) branches from `origin/<default-branch>`, `head`
branches from local `HEAD`. Prefer the default — branching off `origin/main` avoids inheriting
whatever is uncommitted or unpushed locally.

`EnterWorktree` is gated: it fires only when the user asks for a worktree or when `CLAUDE.md` or a
memory instructs it. This skill alone does not authorize it. Check `CLAUDE.md` § Working Discipline
for a standing instruction; if there is none, ask the user before calling it.

**Plain git, for parallel agents and anything outside the session.**

```
git fetch origin
git worktree add -b <branch> .claude/worktrees/<name> origin/main
```

Pass the path to a subagent, or use the `Agent` tool's `isolation: "worktree"` to have the harness
provision one per agent.

## Working in it

Commit each completed unit as it lands. Uncommitted work does not count as done, and a worktree
holding only uncommitted changes cannot be cleaned up without discarding them.

Never `cd` between worktrees mid-session when `CLAUDE.md` forbids changing directory. Use
`EnterWorktree` with `path`, or `git -C <path>` for one-off commands.

## Merging back

Merge from the primary checkout, not from inside the worktree — a branch checked out in a worktree
cannot be merged into a checkout of the same branch elsewhere.

```
git -C <primary> fetch origin
git -C <primary> switch main
git -C <primary> merge --ff-only <branch>
```

`--ff-only` fails loudly when the branch has diverged, which is the signal to rebase it on
`origin/main` first rather than to record a merge commit nobody asked for. Use `--no-ff` only when
the history of the unit is worth preserving as a group.

## Cleanup

Order matters. `ExitWorktree` with `action: "remove"` deletes the branch along with the directory,
so merge first or the work is gone.

1. Merge the branch, per above.
2. Remove the worktree: `ExitWorktree` with `action: "remove"`, or
   `git worktree remove .claude/worktrees/<name>`.
3. Delete the branch if step 2 did not: `git branch -d <branch>`. `-d` refuses an unmerged branch;
   that refusal is a check, not an obstacle to force past.
4. `git worktree prune` to clear records of directories deleted by hand.

`ExitWorktree` only touches a worktree that `EnterWorktree` created in this session. Worktrees made
with `git worktree add`, or left over from an earlier session, need the `git` commands. It refuses to
remove a worktree holding uncommitted files or unmerged commits unless `discard_changes: true` —
report what it listed and confirm with the user before passing that flag.

Use `action: "keep"` when the work is unfinished and the user will return to it.

## Stale state

```
git worktree list          # what exists, and what each has checked out
git worktree prune         # drop records whose directories are gone
git branch --merged main   # branches safe to delete
```

Report stale worktrees and merged branches to the user. Do not delete either without being asked —
an unmerged branch in a stale worktree may be the only copy of that work.
