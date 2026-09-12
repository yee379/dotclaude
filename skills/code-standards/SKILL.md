---
name: code-standards
description: TypeScript, JavaScript, React, and Next.js coding standards — naming conventions, immutability patterns, error handling, async/await, type safety, API design, file organisation, and testing structure.
origin: ECC
---

# Coding Standards & Best Practices

Universal standards for starting a project or module, reviewing for maintainability, refactoring
to convention, setting up lint/format/type-check rules, or onboarding contributors.

## Principles

**Readability first** — code is read more than written. Clear names, self-documenting over
commented, consistent formatting.

**KISS** — the simplest solution that works. No over-engineering, no premature optimisation.
Understandable beats clever.

**DRY** — extract common logic, reuse components, share utilities. No copy-paste programming.

**YAGNI** — don't build before it's needed. Avoid speculative generality; add complexity when
required, refactor when it arrives.

## Reference material

| Topic | File |
|---|---|
| Variable, function, and file naming | `references/naming-conventions.md` |
| Immutability, error handling, async/await, type safety | `references/patterns.md` |
| REST conventions, response format, Zod input validation | `references/api-design.md` |
| Next.js App Router layout and file naming | `references/project-structure.md` |
| When to comment, and JSDoc patterns | `references/comments-jsdoc.md` |
| Before/after examples of each anti-pattern | `references/code-smells.md` |

## Code smells

Watch for long functions (>50 lines), deep nesting (5+ levels), magic numbers, dead code, and
inconsistent naming. Examples in `references/code-smells.md`.

## Performance

Select only the columns you need — `select('id, name, status')`, not `select('*')` — and bound
every query with a `limit`.

```typescript
// ✅ GOOD                              // ❌ BAD
await db.from('users')                  await db.from('users')
  .select('id, name, status').limit(10)   .select('*')
```

React memoisation (`useMemo`, `useCallback`) and lazy loading (`lazy` + `Suspense`) are in
`/react-patterns`, along with component patterns, hooks, state management, Apollo/urql
integration, and RTL testing.

Testing standards are `/tdd-standards`.
