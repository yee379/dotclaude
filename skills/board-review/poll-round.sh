#!/usr/bin/env bash
# poll-round.sh — renders the round dashboard for /board-review, and acts as the fallback
# check when a subagent completion notification never arrives. It is NOT the completion
# signal: the harness notification is. Do not call this on a timer.
#
# The notification says the agent's process exited. This says its output file carries a
# terminal verdict. An agent that runs out of context mid-write does the first without the
# second, which is the case this script exists to catch.
#
# Usage: poll-round.sh <review_dir> <round> [reviewer1 reviewer2 ...]
#
# Prints a GitHub-flavoured markdown table, header included, one row per reviewer. The
# renderer aligns the columns, so no padding is emitted here — emoji are variable width
# and space-padded columns drift the moment a name or a status is wider than the pad.
# Exits 0 only when EVERY active reviewer has a terminal status (PASS / WARN / FAIL);
# 1 if any is missing, in progress, truncated, or unparseable.
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

# shellcheck source=status-of.sh
. "$(dirname "${BASH_SOURCE[0]}")/status-of.sh"

REVIEW_DIR="$1"
ROUND="$2"
shift 2
REVIEWERS=("$@")

code_to_name() {
  case "$1" in
    dr) echo "research" ;;
    ar) echo "codebase-arch-review" ;;
    er) echo "codebase-eng-review" ;;
    dc) echo "doc-review" ;;
    sr) echo "security-review" ;;
    ux) echo "codebase-ux-review" ;;
    pa) echo "arch-review (platform)" ;;
    cr) echo "platform-capacity-review" ;;
    ps) echo "platform-security-review" ;;
    po) echo "platform-ops-review" ;;
    pe) echo "platform-eng-review" ;;
    *)  echo "$1" ;;
  esac
}

# A pipe or a newline in a preview line would break the row it sits in.
cell() { printf '%s' "$1" | tr -d '\n' | sed 's/|/\\|/g'; }

all_done=true

echo "| Reviewer | Status | Early signal |"
echo "|---|---|---|"

for code in "${REVIEWERS[@]}"; do
  file="$REVIEW_DIR/round-${ROUND}-${code}.md"
  display=$(code_to_name "$code")

  # Status comes from status-of.sh so this script and consolidate-round.sh cannot
  # disagree about what counts as terminal.
  case "$(status_of "$file")" in
    PASS)        status="✅ PASS" ;;
    WARN)        status="⚠️ WARN" ;;
    FAIL)        status="❌ FAIL" ;;
    IN_PROGRESS) status="⏳ running";    all_done=false ;;
    TRUNCATED)   status="✂️ truncated";  all_done=false ;;
    MISSING)     status="🔵 queued";     all_done=false ;;
    *)           status="❓ unknown";    all_done=false ;;
  esac

  if [[ ! -f "$file" ]]; then
    echo "| $display | $status | — |"
    continue
  fi

  # A reviewer that appends a second "## Status" heading instead of editing the first
  # in place leaves a stale IN PROGRESS trailing the real terminal status. status_of
  # already read the FIRST occurrence, which is correct; flag the duplicate here so it
  # gets fixed rather than silently tolerated round after round.
  dupe_note=""
  if [[ "$(status_heading_count "$file")" -gt 1 ]]; then
    dupe_note=" ✂️ duplicate \`## Status\` x$(status_heading_count "$file")"
  fi

  signal=$(grep -v "^$" "$file" | grep -v "^#" \
             | grep -vE '^(IN ?PROGRESS|PASS( WITH WARNINGS)?|FAIL)$' \
             | tail -1 | cut -c1-60)
  echo "| $display | $status | $(cell "${signal:-—}")$(cell "$dupe_note") |"
done

$all_done && exit 0 || exit 1
