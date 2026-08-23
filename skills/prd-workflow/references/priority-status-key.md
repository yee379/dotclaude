## Priority Key
- 🔴 P0 Critical — blocking, do immediately
- 🟠 P1 High — high value, do soon
- 🟡 P2 Medium — worth doing, schedule it
- 🔵 P3 Low — nice to have

## Status Key

| Status | Codebase | Platform |
|--------|----------|----------|
| 📋 Preparing | `draft-prd` not yet run | `draft-prd` not yet run |
| ⬜ Open | draft-prd complete, awaiting `/board-review` | draft-prd complete, awaiting `/board-review` |
| 🔎 In Review | board-review actively running | board-review actively running |
| 🔍 Reviewed | plan approved, ready to implement | plan approved, ready to apply |
| 🔄 In Progress | active development | active work |
| 🏁 Implementation Done | code complete, PR not yet raised | complete, PR not yet raised |
| 👀 PR Open | PR raised, awaiting merge | PR raised, awaiting merge |
| ✅ Merged | merged to main, not yet deployed | merged to main, not yet applied |
| 🚀 Deployed / Applied | live in production | live in cluster |
| ❌ Won't Do | cancelled, reason noted in task file | cancelled, reason noted in task file |

### Terminal statuses carry a release

Every terminal status — `✅ Merged`, `🚀 Deployed`, `🚀 Applied`, `✅ Complete` — is written with
the release the task's own work shipped under, in backticks:

```
🚀 Deployed `0.14.0`
✅ Merged `1.2.0`
🚀 Applied (no release)
```

`(no release)` is mandatory rather than optional for terminal tasks with no versioned artefact —
cluster config, manifests, or docs only. A blank version cell is ambiguous between "there wasn't
one" and "nobody recorded it"; `(no release)` removes the ambiguity, and its absence is then a
real defect you can grep for.

Non-terminal statuses carry no version.

**Derive the version, never guess it:**

```bash
git log -p -- <path/to/VERSION>      # every version → the commit that set it
git log --grep="#<number>"           # the task → its commits
git show <sha>:<path/to/VERSION>     # the version in force at that commit
```

Attribute the release the task's *own* work shipped in — not a later one that merely touched the
same area. This check is worth running even on rows that already carry a version: mis-attribution
to a neighbouring release is the common error, and it is invisible until someone derives it.
