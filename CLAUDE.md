# Global Claude Code Instructions

## File Access Boundaries

- Files within the current working directory may be read and edited freely.
- Files in `~/.claude/` may be read freely (skills, settings, documentation).
- Do not read files outside the current working directory or `~/.claude/` unless explicitly asked to by the user.
- Do not edit files outside the current working directory unless explicitly asked to by the user.

## Terminal Commands

- NEVER use absolute paths in terminal commands — always use relative paths, even in complex or multi-part commands (e.g. `ls src/` not `ls /Users/ytl/project/src/`).
- Only use absolute paths when a command explicitly requires one, and only with user-provided paths.
