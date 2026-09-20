#!/usr/bin/env bash
# consolidate-round.sh — called by /board-review after all reviewers complete
# Extracts the minimum content needed from each reviewer output file.
#
# Usage: consolidate-round.sh <review_dir> <round> [reviewer_codes...]
#
# Output per reviewer (to stdout):
#   === <reviewer> ===
#   STATUS: PASS | WARN | FAIL | IN_PROGRESS | UNKNOWN | TRUNCATED | MISSING
#   AMENDED: YES | NO
#   DECISIONS: <count of ## Decision: entries>
#   BLOCKING: <count>
#   OPPORTUNITIES: <count of ## Opportunities lines>
#   SUMMARY:
#   <up to 10 lines from ## Summary section>
#   ---
#
# STATUS comes from status-of.sh, the same parser poll-round.sh uses. Only PASS,
# WARN, and FAIL are terminal; anything else means this reviewer has no verdict and
# the round is not complete.
#
# Section content ignores the skeleton placeholders a reviewer writes as its first
# action — "_(in progress)_" and the like. Counting those as content reported an
# amendment for a reviewer that amended nothing.
#
# Reviewer codes:
#   Codebase: dr=research  ar=codebase-arch-review  er=codebase-eng-review
#             dc=doc-review  sr=security-review  ux=codebase-ux-review
#   Platform: pa=codebase-arch-review(platform)  cr=platform-capacity-review
#             ps=platform-security-review  po=platform-ops-review
#             pe=platform-eng-review  dc=doc-review
#
# Example:
#   consolidate-round.sh todo/review/007-my-feature 1 dr ar er dc sr

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

  status=$(status_of "$file")
  echo "STATUS: $status"

  if [[ "$status" == "MISSING" ]]; then
    echo "---"
    continue
  fi

  # A non-terminal status is a defect in the round, not a verdict. Say so here rather
  # than letting the digest read like a completed review.
  if ! status_is_terminal "$status"; then
    echo "NOT_TERMINAL: this reviewer has no verdict — do not consolidate it"
  fi

  # Drop blank lines and the italic skeleton placeholders, e.g. "_(in progress)_".
  section_content() {
    awk -v h="^## $2" '$0 ~ h {found=1; next} found && /^##/{exit} found{print}' "$1" \
      | grep -v '^[[:space:]]*$' \
      | grep -vE '^_\(.*\)_$'
  }

  if [[ -n "$(section_content "$file" Amendments | head -1)" ]]; then
    echo "AMENDED: YES"
  else
    echo "AMENDED: NO"
  fi

  # `grep -c` prints the count and exits 1 when it is zero. A `|| echo 0` fallback
  # therefore appended a SECOND zero on its own line and corrupted the digest.
  echo "DECISIONS: $(grep -c '^### Decision:' "$file")"
  echo "BLOCKING: $(grep -c 'Severity.*blocking' "$file")"

  opportunity_count=$(section_content "$file" Opportunities | wc -l | tr -d ' ')
  echo "OPPORTUNITIES: $opportunity_count"

  echo "SUMMARY:"
  section_content "$file" Summary | head -10
  echo "---"
done
