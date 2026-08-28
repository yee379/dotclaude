#!/usr/bin/env bash
# poll-round.sh — renders the round dashboard for /board-review, and acts as the fallback
# check when a subagent completion notification never arrives. It is NOT the completion
# signal: the harness notification is. Do not call this on a timer.
#
# Usage: poll-round.sh <review_dir> <round> [reviewer1 reviewer2 ...]
#
# Prints a compact status block for each reviewer output file.
# Exits 0 only when EVERY active reviewer has a terminal ## Status (PASS / PASS WITH
# WARNINGS / FAIL); 1 if any is missing, IN PROGRESS, or truncated without a status.
#
# Reviewer codes:
#   Codebase: dr=research  ar=codebase-arch-review  er=codebase-eng-review
#             dc=doc-review  sr=security-review  ux=codebase-ux-review
#   Platform: pa=codebase-arch-review(platform)  cr=platform-capacity-review
#             ps=platform-security-review  po=platform-ops-review
#             pe=platform-eng-review  dc=doc-review
#
# Example:
#   poll-round.sh todo/review/007-my-feature 1 dr ar er dc sr

REVIEW_DIR="$1"
ROUND="$2"
shift 2
REVIEWERS=("$@")

code_to_name() {
  case "$1" in
    dr) echo "research       " ;;
    ar) echo "codebase-arch-review    " ;;
    er) echo "codebase-eng-review     " ;;
    dc) echo "doc-review              " ;;
    sr) echo "security-review         " ;;
    ux) echo "codebase-ux-review      " ;;
    pa) echo "arch-review(platform)   " ;;
    cr) echo "platform-capacity-review" ;;
    ps) echo "platform-security-review" ;;
    po) echo "platform-ops-review     " ;;
    pe) echo "platform-eng-review     " ;;
    *)  echo "$1                      " ;;
  esac
}

all_done=true

for code in "${REVIEWERS[@]}"; do
  file="$REVIEW_DIR/round-${ROUND}-${code}.md"
  display=$(code_to_name "$code")

  if [[ ! -f "$file" ]]; then
    echo "  🔵 queued      $display  —"
    all_done=false
    continue
  fi

  # Only a TERMINAL status counts as finished. A reviewer's first action is writing the
  # skeleton, which contains "## Status / IN PROGRESS" — so the heading's presence means
  # "started", never "finished". Treat anything non-terminal as still running.
  status_line=$(sed -n '/^## Status/,$p' "$file" | tail -n +2 \
                | grep -v '^[[:space:]]*$' | head -1 \
                | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')

  case "$status_line" in
    *PASSWITHWARNINGS*) icon="⚠️  warn    " ;;
    *PASS*)             icon="✅ complete" ;;
    *FAIL*)             icon="❌ fail    " ;;
    *INPROGRESS*|"")    icon="⏳ running "; all_done=false ;;
    *)                  icon="❓ unknown "; all_done=false ;;
  esac

  # A reviewer that appends a second "## Status" heading instead of editing the first
  # in place leaves a stale IN PROGRESS trailing the real terminal status. The icon
  # above already used the FIRST occurrence (correct); flag the duplicate here so it
  # gets fixed rather than silently tolerated round after round.
  status_heading_count=$(grep -c '^## Status' "$file")
  dupe_note=""
  if [[ "$status_heading_count" -gt 1 ]]; then
    dupe_note=" ⚠️duplicate-status-heading(x${status_heading_count})"
  fi

  signal=$(grep -v "^$" "$file" | grep -v "^#" \
             | grep -vE '^(IN ?PROGRESS|PASS( WITH WARNINGS)?|FAIL)$' \
             | tail -1 | cut -c1-50)
  echo "  $icon  $display  ${signal:----}${dupe_note}"
done

$all_done && exit 0 || exit 1
