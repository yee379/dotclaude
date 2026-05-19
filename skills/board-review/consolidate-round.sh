#!/usr/bin/env bash
# consolidate-round.sh — called by /board-review after all reviewers complete
# Extracts the minimum content needed from each reviewer output file.
#
# Usage: consolidate-round.sh <review_dir> <round> [reviewer_codes...]
#
# Output per reviewer (to stdout):
#   === <reviewer> ===
#   STATUS: PASS | PASS WITH WARNINGS | FAIL | TRUNCATED | MISSING
#   AMENDED: YES | NO
#   DECISIONS: <count of ## Decision: entries>
#   BLOCKING: <count>
#   SUMMARY:
#   <up to 10 lines from ## Summary section>
#   ---
#
# Reviewer codes:
#   Codebase: dr=research-handbook  ar=codebase-arch-review  er=codebase-eng-review
#             dc=doc-review  sr=security-review  ux=codebase-ux-review
#   Platform: pa=codebase-arch-review(platform)  cr=platform-capacity-review
#             ps=platform-security-review  po=platform-ops-review
#             pe=platform-eng-review  dc=doc-review
#
# Example:
#   consolidate-round.sh todo/review/007-my-feature 1 dr ar er dc sr

REVIEW_DIR="$1"
ROUND="$2"
shift 2
REVIEWERS=("$@")

code_to_name() {
  case "$1" in
    dr) echo "research-handbook" ;;
    ar) echo "codebase-arch-review" ;;
    er) echo "codebase-eng-review" ;;
    dc) echo "doc-review" ;;
    sr) echo "security-review" ;;
    ux) echo "codebase-ux-review" ;;
    pa) echo "codebase-arch-review(platform)" ;;
    cr) echo "platform-capacity-review" ;;
    ps) echo "platform-security-review" ;;
    po) echo "platform-ops-review" ;;
    pe) echo "platform-eng-review" ;;
    *)  echo "$1" ;;
  esac
}

for code in "${REVIEWERS[@]}"; do
  file="$REVIEW_DIR/round-${ROUND}-${code}.md"
  display=$(code_to_name "$code")

  echo "=== $display ==="

  if [[ ! -f "$file" ]]; then
    echo "STATUS: MISSING"
    echo "---"
    continue
  fi

  if grep -q "^## Status" "$file" 2>/dev/null; then
    status_line=$(grep -A1 "^## Status" "$file" | tail -1 | tr -d '[:space:]')
    case "$status_line" in
      *PASS*WITH*WARNINGS*) echo "STATUS: PASS WITH WARNINGS" ;;
      *PASS*)               echo "STATUS: PASS" ;;
      *FAIL*)               echo "STATUS: FAIL" ;;
      *)                    echo "STATUS: PASS" ;;
    esac
  else
    echo "STATUS: TRUNCATED"
  fi

  if grep -q "^## Amendments" "$file" 2>/dev/null; then
    amended_content=$(awk '/^## Amendments/{found=1; next} found && /^##/{exit} found{print}' "$file" | grep -v "^$" | head -1)
    if [[ -n "$amended_content" ]]; then
      echo "AMENDED: YES"
    else
      echo "AMENDED: NO"
    fi
  else
    echo "AMENDED: NO"
  fi

  decision_count=$(grep -c "^### Decision:" "$file" 2>/dev/null || echo 0)
  echo "DECISIONS: $decision_count"

  blocking_count=$(grep -c "Severity.*blocking" "$file" 2>/dev/null || echo 0)
  echo "BLOCKING: $blocking_count"

  echo "SUMMARY:"
  awk '/^## Summary/{found=1; next} found && /^##/{exit} found{print}' "$file" \
    | grep -v "^$" \
    | head -10
  echo "---"
done
