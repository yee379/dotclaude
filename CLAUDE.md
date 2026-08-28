# Global Claude Code Instructions

## File Access Boundaries

- Files within the current working directory may be read and edited freely.
- Files in `~/.claude/` may be read freely (skills, settings, documentation).
- Do not read files outside the current working directory or `~/.claude/` unless explicitly asked to by the user.
- Do not edit files outside the current working directory unless explicitly asked to by the user.

## Terminal Commands

- NEVER use absolute paths in terminal commands — always use relative paths, even in complex or multi-part commands (e.g. `ls src/` not `ls /Users/ytl/project/src/`).
- Only use absolute paths when a command explicitly requires one, and only with user-provided paths.
- NEVER change the working directory — do not use `cd` in any Bash command, not even as part of a chained command (e.g. `cd foo && make`). The working directory is the directory Claude was started in and must remain constant for the entire session.
- When a command must run in a subdirectory, pass the path inline instead (e.g. `make -C src/`, `npm --prefix src/ install`, or `(cd src/ && make)` only as a last resort when the tool provides no alternative).

## Working Discipline

- Don't assume or guess silently: stop and ask clarifying questions if anything is ambiguous instead of running with wrong assumptions.
- Don't overcomplicate: write the absolute minimum amount of code needed; avoid speculative features, config systems, or single-use abstractions.
- Don't touch adjacent code: never "improve" neighboring formatting, comments, or clean up adjacent code that wasn't part of the direct request.
- Don't refactor unbroken things: leave working code alone unless it is directly tied to the assigned task.
- Don't delete pre-existing dead code: if you spot unrelated dead code, mention it to the user, but do not delete it on your own.

## Skill Routing

When the user's intent matches a pattern below, invoke the listed skill via the Skill tool **before** responding. Apply judgment — these are intent patterns, not rigid keyword triggers. For platform/infra intents (k8s, cluster, Helm, namespace, workload), prefer the platform-* variant; for software/feature intents, prefer the codebase-* variant.

| Intent | Skill / Tool |
|---|---|
| Plan a feature, design a system, draft a PRD, "what should we build", "how should we approach" | `draft-prd` |
| Stress-test a plan, "grill me", relentless design interview | `draft-prd` (Grill Mode) |
| Review a plan, gate a design, "is this ready", "board review this" | `board-review` |
| Write code for a new feature, fix a bug, refactor — any implementation task | `tdd-standards` |
| Debug an issue, diagnose a failure, "why is X broken", "help me troubleshoot" | `troubleshoot` |
| Research a topic, "deep dive", "what's the current state of", competitive analysis | `research` |
| Search for existing libraries/tools before writing custom code | `search-first` |
| Challenge or reframe a research question, steelman an approach | `research-scout` |
| Track tasks, "what's outstanding", "pick up where we left off", show status | `prd-workflow` |
| Discover tech debt, generate backlog ideas, "what should we improve" | `codebase-scout` |
| Review a PR or code diff | `code-review` |
| Security concerns, "is this safe", audit for vulnerabilities | `security-review` |
| Deploy to Kubernetes, apply Helm charts, `make apply` | `k8s-deploy` |
| Ship a release, promote to production, tag a version | `prod-release` |
| Close out a task, update docs/CHANGELOG after merging | `closeout-prd` |
| Audit or improve skills, "skill stocktake" | `skill-stocktake` |
| "what did we decide", "last time", "do you remember", prior decisions or context, session start on a known project | `mcp__mempalace__mempalace_search` (keywords only, not a sentence) |
| Save an insight, decision, or key finding to memory | `mcp__mempalace__mempalace_add_drawer` |
