# OBSOLETE — do not file. Both bugs are already fixed in mempalace 3.9.0.

This file previously held a draft GitHub issue for MemPalace/mempalace describing two
bugs found while debugging the Stop hook on 2026-09-13. Both were diagnosed against
**3.3.3**, which was stale — the local marketplace checkout is pinned to a May 3 commit,
while PyPI was already at 3.9.0.

After upgrading to 3.9.0, both were confirmed fixed upstream. Filing either would be a
duplicate. Kept only as a record of what was investigated.

---

## Bug 1 — Stop hook mined `dirname(transcript_path)` — FIXED in 3.9.0

**Was:** `hooks_cli._get_mine_dir()` returned `str(path.parent)` for the transcript, with
no allowlist of permitted roots. A transcript under a shared directory therefore caused
the hook to ingest that entire directory. Observed: `mempalace mine /tmp --mode convos`
ran ~22 minutes and filed 17,551 drawers of unrelated `/tmp` scratch files into a wing
named `tmp`. Aggravating detail: `_validate_transcript_path`'s docstring claimed it
rejected "paths outside expected roots", but it only checked the file suffix and `..`,
and `_get_mine_dir` never called it anyway.

**Now:** `_get_mine_dir` is gone. `_get_mine_targets()` returns only a `MEMPAL_DIR`
"projects" target, and its docstring records that transcript ingestion moved out
deliberately:

> Transcript ingestion is handled separately by `_ingest_transcript` — emitting it here
> too would double-mine the same JSONL into a different wing on every hook fire
> (#1231 review).

`_ingest_transcript()` submits `{"source": str(path), "mode": "convos", "wing": "sessions"}`
— the transcript **file**, not its parent directory. No parent-directory expansion remains
in either `hooks_cli.py` or `hook_shell.py`.

## Bug 2 — shell hook bypassed the `mine.pid` guard — FIXED in 3.9.0

**Was:** 3.3.3 added `_mine_already_running()` guarding on a single global
`~/.mempalace/hook_state/mine.pid`, but the shipped `hooks/mempal_save_hook.sh` spawned
`mempalace mine ... &` directly without consulting it. With both the plugin's `hooks.json`
and the shell hook registered, the guard was silently defeated. Observed: five concurrent
mines against one palace, and `quarantine_stale_hnsw()` firing 8 times over four months
(5 in a single day), accumulating 1.1 GB of orphaned HNSW segment directories.

**Now:** the single global PID file was replaced with a directory of per-target slots
(`hook_state/mine_pids/`) claimed atomically via `O_CREAT | O_EXCL`. Upstream's own
comment describes precisely this failure mode, including the corruption consequence:

> The single `mine.pid` global file used previously failed both ways: the guard was
> rebuilt every spawn (so two near-simultaneous fires both passed the check before either
> wrote), and the file was unconditionally overwritten (so the second spawn lost the first
> PID, orphaning it). [...] multiple concurrent mines against the same source corrupt the
> HNSW index and exhaust disk via duplicate upserts (#1212, #1206)

Also added: `MEMPALACE_MINE_TIMEOUT_HOURS` (default 2.0) to reclaim slots held by wedged
mines, and an opt-in `mempalace daemon` (3.5.0) that serializes all palace writes through
one local process, with hook write-routing through it in 3.8.0.

---

## Local lesson worth keeping

The root cause of this whole investigation was **version drift**, not any single bug:
the pip package (3.1.0, then 3.3.3) and the plugin marketplace checkout (3.3.3, pinned to
a May 3 commit) were both far behind PyPI (3.9.0). The original symptom — a Stop hook that
appeared broken — was a missing `mempalace-mcp` console script caused by that drift.

Check `pip index`/PyPI against the marketplace checkout before diagnosing hook behaviour.
The marketplace checkout does not update itself, and a plugin's `plugin.json` can reference
binaries that the installed wheel never provided.
