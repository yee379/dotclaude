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
