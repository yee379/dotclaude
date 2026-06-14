#!/usr/bin/env python3
"""
priority-audit.py — audit all TOPICS.md entries and flag priority mismatches.

Usage:
    python tools/priority-audit.py [--fix] [--recount]

Two audit modes:

1. Default (fast) — count backtick-quoted file references in each row's notes
   column and check the tier matches. This trusts the stored blast-radius data.
   Use for a quick consistency check.

2. --recount — re-grep concepts/ and reports/ live using the stored notes
   file stems as search terms. Detects topics that have drifted since the
   notes were last updated (e.g. new output files now reference this topic).
   Slower but authoritative.

Flags:
    --fix       Rewrite TOPICS.md with corrected priorities.
                A .bak backup is written before any modifications.
    --recount   Use live grep counts instead of stored notes counts.

Priority tiers (based on file reference count):
    P1  ≥5 references
    P2  2–4 references
    P3  0–1 references
"""

import re
import shutil
import sys
from pathlib import Path

ROOT = Path.cwd()
TOPICS_FILE = ROOT / "TOPICS.md"
SEARCH_DIRS = [ROOT / "concepts", ROOT / "reports"]

PRIORITY_EMOJIS = {
    "P1": "🔺 P1",
    "P2": "🔸 P2",
    "P3": "🔹 P3",
}


def live_grep_count(file_stems: list[str]) -> tuple[int, list[Path]]:
    """
    Count unique concepts/ and reports/ files that are referenced by any of
    the given stem names. Used by --recount to refresh beyond what notes record.
    """
    matched: set[Path] = set()
    for directory in SEARCH_DIRS:
        if not directory.exists():
            continue
        for filepath in directory.glob("*.md"):
            text = filepath.read_text(encoding="utf-8", errors="replace")
            for stem in file_stems:
                if stem and re.search(re.escape(stem), text, re.IGNORECASE):
                    matched.add(filepath)
                    break
    return len(matched), sorted(matched)


def count_from_notes(notes: str) -> tuple[int, list[str]]:
    """
    Count backtick-quoted kebab-case file references in the notes column.
    E.g. "referenced by `iam-services`, `jwt-jwks`, `rfc-compliance`" → (3, [...])
    Only matches lowercase-hyphen names (output file stems, not code values).
    """
    stems = list(dict.fromkeys(re.findall(r"`([a-z][a-z0-9-]+)`", notes)))
    return len(stems), stems


def computed_tier(count: int) -> str:
    if count >= 5:
        return "P1"
    elif count >= 2:
        return "P2"
    else:
        return "P3"


def parse_topics_rows(content: str) -> list[dict]:
    """
    Parse standard TOPICS.md table rows:
    | Priority | Status | Type | Topic | Researched | Notes |
    The notes column is captured greedily to the end of the line.
    """
    rows = []
    row_re = re.compile(
        r"^\|\s*(🔺 P1|🔸 P2|🔹 P3|🔺|🔸|🔹)\s*\|"
        r"\s*`?([^`|]+)`?\s*\|"   # status
        r"\s*([^|]*?)\s*\|"        # type
        r"\s*([^|]+?)\s*\|"        # topic
        r"\s*([^|]*?)\s*\|"        # researched
        r"\s*(.*?)\s*\|?\s*$"      # notes — greedy to end of line
    )
    for i, line in enumerate(content.splitlines()):
        m = row_re.match(line)
        if m:
            rows.append({
                "priority": m.group(1).strip(),
                "status":   m.group(2).strip(),
                "type":     m.group(3).strip(),
                "topic":    m.group(4).strip(),
                "researched": m.group(5).strip(),
                "notes":    m.group(6).strip(),
                "line_num": i + 1,
                "raw_line": line,
            })
    return rows


def tier_from_stored(priority_str: str) -> str:
    m = re.search(r"P([123])", priority_str)
    return f"P{m.group(1)}" if m else "??"


def main() -> None:
    fix_mode = "--fix" in sys.argv
    recount_mode = "--recount" in sys.argv

    if not TOPICS_FILE.exists():
        print(f"Error: {TOPICS_FILE} not found", file=sys.stderr)
        sys.exit(1)

    content = TOPICS_FILE.read_text(encoding="utf-8")
    rows = parse_topics_rows(content)

    if not rows:
        print("No priority rows found in TOPICS.md.")
        sys.exit(0)

    mode_label = "live grep (--recount)" if recount_mode else "stored notes"
    print(f"\npriority-audit — counting references from {mode_label}")
    print(f"Topics: {len(rows)}\n")

    results = []
    for row in rows:
        stored = tier_from_stored(row["priority"])
        note_count, note_stems = count_from_notes(row["notes"])

        if recount_mode and note_stems:
            count, files = live_grep_count(note_stems)
        else:
            count, files = note_count, []

        computed = computed_tier(count)
        results.append({
            **row,
            "stored": stored,
            "computed": computed,
            "count": count,
            "files": files,
            "match": stored == computed,
        })

    # Print table
    col_w = 44
    print(f"{'Topic':<{col_w}}  {'Stored':>6}  {'Computed':>8}  {'Refs':>4}  ")
    print("-" * (col_w + 30))
    for r in results:
        ok = "✅" if r["match"] else "❌"
        arrow = "" if r["match"] else f"  → {PRIORITY_EMOJIS[r['computed']]}"
        print(f"{r['topic'][:col_w]:<{col_w}}  {r['stored']:>6}  {r['computed']:>8}  {r['count']:>4}  {ok}{arrow}")

    mismatches = [r for r in results if not r["match"]]
    print()

    if not mismatches:
        print(f"✅ All {len(rows)} priorities correct.")
    else:
        print(f"❌ {len(mismatches)} mismatch(es) out of {len(rows)} topics.")

        if fix_mode:
            backup = TOPICS_FILE.with_suffix(".md.bak")
            shutil.copy(TOPICS_FILE, backup)
            print(f"\nBackup: {backup.name}")
            new_content = content
            for r in mismatches:
                old_line = r["raw_line"]
                new_line = old_line.replace(r["priority"], PRIORITY_EMOJIS[r["computed"]], 1)
                new_content = new_content.replace(old_line, new_line, 1)
                print(f"  {r['topic'][:50]}: {r['priority']} → {PRIORITY_EMOJIS[r['computed']]}")
            TOPICS_FILE.write_text(new_content, encoding="utf-8")
            print(f"\n✅ TOPICS.md updated.")
        else:
            print("\nOptions:")
            print("  --fix       apply corrections to TOPICS.md")
            print("  --recount   re-grep live files (catches drift since notes were written)")

    print()


if __name__ == "__main__":
    main()
