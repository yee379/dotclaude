#!/usr/bin/env bash
# consolidate-round.sh — called by /full-review after all reviewers complete
# Extracts the minimum content needed from each reviewer output file so the
# main session doesn't need to read full files or construct ad-hoc bash.
#
# Usage: consolidate-round.sh <review_dir> <round> [reviewer_codes...]
#
# Output per reviewer (to stdout):
#   === <reviewer> ===
#   STATUS: PASS | PASS WITH WARNINGS | FAIL | TRUNCATED | MISSING
#   AMENDED: YES | NO
#   DECISIONS: <count of ## Decision: entries>
#   SUMMARY:
#   <up to 10 lines from ## Summary section>
#   ---
#
# Example:
#   consolidate-round.sh todo/review/007-my-feature 1 dr ar er dc sr

REVIEW_DIR="$1"
ROUND="$2"
shift 2
REVIEWERS=("$@")

declare -A NAME=(
  [dr]="deep-research"
  [ar]="plan-arch-review"
  [er]="plan-eng-review"
  [dc]="plan-doc-review"
  [sr]="security-review"
)

for code in "${REVIEWERS[@]}"; do
  file="$REVIEW_DIR/round-${ROUND}-${code}.md"
  display="${NAME[$code]:-$code}"

  echo "=== $display ==="

  if [[ ! -f "$file" ]]; then
    echo "STATUS: MISSING"
    echo "---"
    continue
  fi

  # Status — look for ## Status section
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

  # Amended — look for non-empty ## Amendments section
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

  # Decision count
  decision_count=$(grep -c "^### Decision:" "$file" 2>/dev/null || echo 0)
  echo "DECISIONS: $decision_count"

  # Blocking decision count
  blocking_count=$(grep -c "blocking" "$file" 2>/dev/null || echo 0)
  echo "BLOCKING: $blocking_count"

  # Summary — extract ## Summary section, up to 10 lines
  echo "SUMMARY:"
  awk '/^## Summary/{found=1; next} found && /^##/{exit} found{print}' "$file" \
    | grep -v "^$" \
    | head -10
  echo "---"
done
