#!/usr/bin/env bash
# poll-round.sh — called by /full-review during the polling loop
# Usage: poll-round.sh <review_dir> <round> [reviewer1 reviewer2 ...]
#
# Prints a compact status block for each reviewer output file.
# Exits 0 if all active reviewers are complete/truncated, 1 if any are still running.
#
# Example:
#   poll-round.sh todo/review/007-my-feature 1 dr ar er dc sr

REVIEW_DIR="$1"
ROUND="$2"
shift 2
REVIEWERS=("$@")

code_to_name() {
  case "$1" in
    dr) echo "deep-research   " ;;
    ar) echo "plan-arch-review" ;;
    er) echo "plan-eng-review " ;;
    dc) echo "plan-doc-review " ;;
    sr) echo "security-review " ;;
    *)  echo "$1             " ;;
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

  # Check for a ## Status line — presence means the agent wrote its final section
  if grep -q "^## Status" "$file" 2>/dev/null; then
    status_line=$(grep -A1 "^## Status" "$file" | tail -1 | tr -d '[:space:]')
    case "$status_line" in
      *PASS*WITH*WARNINGS*) icon="⚠️  warn    " ;;
      *PASS*)               icon="✅ complete" ;;
      *FAIL*)               icon="❌ fail    " ;;
      *)                    icon="✅ complete" ;;
    esac
    signal=$(tail -5 "$file" | grep -v "^#" | grep -v "^$" | tail -1 | cut -c1-50)
    echo "  $icon  $display  ${signal:----}"
  else
    # File exists but no ## Status yet — still running; grab last non-empty line as signal
    signal=$(grep -v "^$" "$file" | tail -1 | cut -c1-50)
    echo "  ⏳ running     $display  ${signal:----}"
    all_done=false
  fi
done

# Exit code tells the caller whether to keep waiting
$all_done && exit 0 || exit 1
