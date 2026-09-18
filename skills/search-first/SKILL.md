---
name: search-first
description: Research-before-coding workflow. Search for existing tools, libraries, and patterns before writing custom code. Invokes the researcher agent.
origin: ECC
---

# /search-first — Research Before You Code

Systematises "search for existing solutions before implementing". Use when starting a feature that
likely has one, adding a dependency or integration, writing code for "add X functionality", before
creating any new utility, helper, or abstraction, and when troubleshooting.

## The loop

**Need analysis** (what functionality, what language/framework constraints) → **parallel search**
(package registry, MCP servers, installed skills, GitHub/web) → **evaluate** (functionality,
maintenance, community, docs, license, dependency weight) → **decide** → **implement**.

| Signal | Action |
|--------|--------|
| Exact match, well-maintained, MIT/Apache | **Adopt** — install and use directly |
| Partial match, good foundation | **Extend** — install + a thin wrapper |
| Multiple weak matches | **Compose** — combine 2–3 small packages |
| Nothing suitable | **Build** — custom, but informed by the research |

## Quick mode (inline)

Before writing a utility, run through:

0. **Does this already exist in the repo?** → `rg` through the relevant modules and tests first
1. Is this a common problem? → search npm / PyPI
2. Is there an MCP for it? → check `~/.claude/settings.json` and search
3. Is there a skill for it? → check `~/.claude/skills/`
4. Is there a maintained OSS implementation or template? → GitHub code search

## Full mode (agent)

For non-trivial functionality:

```
Task(subagent_type="general-purpose", prompt="
  Research existing tools for: [DESCRIPTION]
  Language/framework: [LANG]
  Constraints: [ANY]

  Search: npm/PyPI, MCP servers, Claude Code skills, GitHub
  Return: Structured comparison with recommendation
")
```

## Shortcuts by category

- **Dev tooling** — linting `eslint`/`ruff`/`markdownlint` · formatting `prettier`/`black`/`gofmt`
  · testing `jest`/`pytest`/`go test` · pre-commit `husky`/`lint-staged`/`pre-commit`
- **AI/LLM** — Claude SDK docs via Context7 · prompt management: check MCP servers · document
  processing `unstructured`/`pdfplumber`/`mammoth`
- **Data & APIs** — HTTP clients `httpx` (Python), `ky`/`got` (Node) · validation `zod` (TS),
  `pydantic` (Python) · databases: check for an MCP server first
- **Content** — markdown `remark`/`unified`/`markdown-it` · images `sharp`/`imagemin`

## Where it is invoked automatically

- **`/codebase-arch-review` §4 (Technology choices)** — for every novel technology or custom
  component, before accepting it as a plan decision. Boring-by-default requires knowing what
  already exists; you cannot spend an innovation token wisely without checking whether something
  off-the-shelf almost works. Also covers integration patterns and reference architectures.
- **`/codebase-eng-review` Step 0 (Scope Challenge)** — for any new custom utility, helper, or
  integration, before counting it as implementation work. If a library provides it, scope shrinks.
- **`/draft-prd`** — before Phase 1, so available tools land in the plan instead of being
  reinvented in it.

## Example

```
Need: Check markdown files for broken links
Search: npm "markdown dead link checker"
Found: textlint-rule-no-dead-link (score: 9/10)
Action: ADOPT — npm install textlint-rule-no-dead-link
Result: Zero custom code, battle-tested solution
```

## Anti-patterns

- **Jumping to code** — writing a utility without checking whether one exists
- **Ignoring MCP** — not checking whether a server already provides the capability
- **Over-customising** — wrapping a library so heavily it loses its benefits
- **Dependency bloat** — a massive package for one small feature
