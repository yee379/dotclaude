#!/usr/bin/env python3
"""
blast-radius.py — compute the blast radius and priority tier for a research topic.

Usage:
    python .claude/skills/research-workflow/scripts/blast-radius.py <keyword> [keyword2 ...]
    python .claude/skills/research-workflow/scripts/blast-radius.py --no-fuzzy <keyword> [keyword2 ...]

Run from the project root directory. Searches concepts/ and reports/ for each keyword
via three methods (most to least precise):

    [keyword tag]   matched via the **Keywords:** frontmatter field (exact, case-insensitive)
    [body]          matched via full-text body search (exact, case-insensitive)
    [fuzzy: N.NN]   matched via SequenceMatcher against Keywords field terms (score shown)

Fuzzy matching is on by default. It is skipped for search terms shorter than 3 characters
and only fires when no exact match already exists.
Pass --no-fuzzy to disable it.

Priority tiers:
    P1  ≥5 matching files, OR explicitly flagged as blocking a deployment path
    P2  2–4 matching files
    P3  0–1 matching files

Examples:
    python scripts/blast-radius.py Keycloak realm "LDAP sync"
    python scripts/blast-radius.py DPoP dpop
    python scripts/blast-radius.py "project context" amsc_project_context
    python scripts/blast-radius.py "token revocation"
"""

import sys
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path.cwd()
SEARCH_DIRS = [ROOT / "concepts", ROOT / "reports"]

KEYWORDS_RE = re.compile(r"^\*\*Keywords:\*\*\s*(.+)$", re.MULTILINE)
FUZZY_THRESHOLD = 0.80
FUZZY_MIN_LEN = 3


def parse_keywords_field(text: str) -> list[str]:
    """Extract terms from the **Keywords:** frontmatter line."""
    m = KEYWORDS_RE.search(text)
    if not m:
        return []
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


def fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def best_fuzzy_match(kw: str, tags: list[str]) -> tuple[float, str] | None:
    """Return (score, matched_tag) if any tag scores above threshold, else None."""
    if len(kw) < FUZZY_MIN_LEN:
        return None
    best = max(((fuzzy_score(kw, tag), tag) for tag in tags), default=(0, ""))
    if best[0] >= FUZZY_THRESHOLD:
        return best
    return None


def grep_files(keywords: list[str], fuzzy: bool) -> dict[Path, dict]:
    """
    Return {filepath: {"tag": [...], "body": [...], "fuzzy": [(score, kw, tag), ...]}}
    for all files matching any keyword.
    """
    results: dict[Path, dict] = {}
    for directory in SEARCH_DIRS:
        if not directory.exists():
            continue
        for filepath in sorted(directory.glob("*.md")):
            text = filepath.read_text(encoding="utf-8", errors="replace")
            file_tags = parse_keywords_field(text)

            tag_hits: set[str] = set()
            body_hits: set[str] = set()
            fuzzy_hits: list[tuple[float, str, str]] = []  # (score, kw, matched_tag)

            for kw in keywords:
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                kw_exact = any(pattern.search(tag) for tag in file_tags)
                body_exact = bool(pattern.search(text))

                if kw_exact:
                    tag_hits.add(kw)
                elif body_exact:
                    body_hits.add(kw)
                elif fuzzy and file_tags:
                    match = best_fuzzy_match(kw, file_tags)
                    if match:
                        fuzzy_hits.append((match[0], kw, match[1]))

            if tag_hits or body_hits or fuzzy_hits:
                results[filepath] = {
                    "tag": sorted(tag_hits),
                    "body": sorted(body_hits),
                    "fuzzy": sorted(fuzzy_hits, reverse=True),
                }
    return results


def priority_tier(count: int) -> tuple[str, str]:
    if count >= 5:
        return "🔺 P1", "referenced by ≥5 existing outputs"
    elif count >= 2:
        return "🔸 P2", f"referenced by {count} existing outputs"
    else:
        return "🔹 P3", f"referenced by {count} existing output(s)"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    fuzzy = True
    if "--no-fuzzy" in args:
        fuzzy = False
        args = [a for a in args if a != "--no-fuzzy"]

    if not args:
        print("Error: no keywords provided.")
        sys.exit(1)

    keywords = args
    matches = grep_files(keywords, fuzzy)
    count = len(matches)
    tier, reason = priority_tier(count)

    print(f"\nBlast-radius report")
    print(f"Keywords : {', '.join(repr(k) for k in keywords)}")
    print(f"Fuzzy    : {'on' if fuzzy else 'off'} (threshold={FUZZY_THRESHOLD}, min_len={FUZZY_MIN_LEN})")
    print(f"Matches  : {count} file(s)")
    print(f"Priority : {tier}  ({reason})")

    if matches:
        print(f"\nAffected files:")
        for filepath, info in sorted(matches.items()):
            rel = filepath.relative_to(ROOT)
            parts = []
            if info["tag"]:
                parts.append(f"keyword tag: {', '.join(info['tag'])}")
            if info["body"]:
                parts.append(f"body: {', '.join(info['body'])}")
            for score, kw, matched_tag in info["fuzzy"]:
                parts.append(f"fuzzy {score:.2f}: '{kw}' ~ '{matched_tag}'")
            print(f"  {rel}  [{'; '.join(parts)}]")
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
