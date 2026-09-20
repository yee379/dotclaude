#!/usr/bin/env bash
# status-of.sh — the single definition of a reviewer's status.
#
# Sourced by poll-round.sh and consolidate-round.sh. Both used to parse the
# `## Status` section themselves and disagreed on three cases: a duplicate
# heading, a blank line after the heading, and a reviewer still IN PROGRESS.
# consolidate-round.sh reported all three as PASS, so a FAIL and a reviewer
# that died mid-write both read as a pass.
#
# status_of <file>  echoes exactly one of:
#   PASS | WARN | FAIL | IN_PROGRESS | UNKNOWN | TRUNCATED | MISSING
#
# Rules, and why each one exists:
#   - The FIRST `## Status` heading wins. A reviewer that appends a second
#     heading instead of editing the first leaves a stale IN PROGRESS behind
#     the real verdict; reading the last one inverts the result.
#   - Blank lines after the heading are skipped. The status is the first
#     non-blank line, not the literally-next line.
#   - IN_PROGRESS is not terminal. A reviewer writes the skeleton (which
#     contains `## Status` / IN PROGRESS) as its first action, so the heading
#     being present means started, never finished.
#   - There is no catch-all to PASS. An unrecognised string is UNKNOWN and
#     must block, because a status nobody can parse is not a passing review.

status_of() {
  local file="$1"

  [[ -f "$file" ]] || { echo "MISSING"; return; }
  grep -q '^## Status' "$file" 2>/dev/null || { echo "TRUNCATED"; return; }

  local line
  line=$(sed -n '/^## Status/,$p' "$file" | tail -n +2 \
           | grep -v '^[[:space:]]*$' | head -1 \
           | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')

  case "$line" in
    *PASSWITHWARNINGS*) echo "WARN" ;;
    *PASS*)             echo "PASS" ;;
    *FAIL*)             echo "FAIL" ;;
    *INPROGRESS*|"")    echo "IN_PROGRESS" ;;
    *)                  echo "UNKNOWN" ;;
  esac
}

# status_is_terminal <status> — true only for a status that may be consolidated.
status_is_terminal() {
  case "$1" in
    PASS|WARN|FAIL) return 0 ;;
    *)              return 1 ;;
  esac
}

# Count of `## Status` headings. More than one means a reviewer appended
# instead of editing; the verdict above is still correct, but the file needs
# fixing rather than tolerating round after round.
status_heading_count() {
  grep -c '^## Status' "$1" 2>/dev/null || echo 0
}
