#!/usr/bin/env python3
"""
blast-radius.py — compute the blast radius and priority tier for a research topic.

Usage:
    python .claude/skills/research-workflow/tools/blast-radius.py <keyword> [keyword2 ...]

Run from the project root directory. Greps concepts/ and reports/ for each keyword (case-insensitive), counts unique
matching files, and outputs the priority tier + affected file list.

Priority tiers:
    P1  ≥5 matching files, OR explicitly flagged as blocking a deployment path
    P2  2–4 matching files
    P3  0–1 matching files

Examples:
    python tools/blast-radius.py Keycloak realm "LDAP sync"
    python tools/blast-radius.py DPoP dpop
    python tools/blast-radius.py "project context" amsc_project_context
"""

import sys
import re
from pathlib import Path

ROOT = Path.cwd()
SEARCH_DIRS = [ROOT / "concepts", ROOT / "reports"]


def grep_files(keywords: list[str]) -> dict[Path, list[str]]:
    """Return {filepath: [matched keywords]} for all files matching any keyword."""
    matches: dict[Path, set[str]] = {}
    for directory in SEARCH_DIRS:
        if not directory.exists():
            continue
        for filepath in sorted(directory.glob("*.md")):
            text = filepath.read_text(encoding="utf-8", errors="replace")
            for kw in keywords:
                if re.search(re.escape(kw), text, re.IGNORECASE):
                    matches.setdefault(filepath, set()).add(kw)
    return {k: sorted(v) for k, v in matches.items()}


def priority_tier(count: int) -> tuple[str, str]:
    if count >= 5:
        return "🔺 P1", "referenced by ≥5 existing outputs"
    elif count >= 2:
        return "🔸 P2", f"referenced by {count} existing outputs"
    else:
        return "🔹 P3", f"referenced by {count} existing output(s)"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    keywords = sys.argv[1:]
    matches = grep_files(keywords)
    count = len(matches)
    tier, reason = priority_tier(count)

    print(f"\nBlast-radius report")
    print(f"Keywords : {', '.join(repr(k) for k in keywords)}")
    print(f"Matches  : {count} file(s)")
    print(f"Priority : {tier}  ({reason})")

    if matches:
        print(f"\nAffected files:")
        for filepath, kws in sorted(matches.items()):
            rel = filepath.relative_to(ROOT)
            print(f"  {rel}  [matched: {', '.join(kws)}]")
    else:
        print("\nNo matching files found.")

    print()
    print("TOPICS.md notes column snippet:")
    if matches:
        file_list = ", ".join(
            f"`{p.relative_to(ROOT).stem}`" for p in sorted(matches)
        )
        print(f"  referenced by {count} files: {file_list}")
    else:
        print("  no existing outputs reference this topic")


if __name__ == "__main__":
    main()
