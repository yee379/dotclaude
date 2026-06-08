---
name: code-standards
description: TypeScript, JavaScript, React, and Next.js coding standards — naming conventions, immutability patterns, error handling, async/await, type safety, API design, file organisation, and testing structure.
origin: ECC
---

# Coding Standards & Best Practices

Universal coding standards applicable across all projects.

## When to Activate

- Starting a new project or module
- Reviewing code for quality and maintainability
- Refactoring existing code to follow conventions
- Enforcing naming, formatting, or structural consistency
- Setting up linting, formatting, or type-checking rules
- Onboarding new contributors to coding conventions

## Code Quality Principles

### 1. Readability First
- Code is read more than written
- Clear variable and function names
- Self-documenting code preferred over comments
- Consistent formatting

### 2. KISS (Keep It Simple, Stupid)
- Simplest solution that works
- Avoid over-engineering
- No premature optimization
- Easy to understand > clever code

### 3. DRY (Don't Repeat Yourself)
- Extract common logic into functions
- Create reusable components
- Share utilities across modules
- Avoid copy-paste programming

### 4. YAGNI (You Aren't Gonna Need It)
- Don't build features before they're needed
- Avoid speculative generality
- Add complexity only when required
- Start simple, refactor when needed

## TypeScript/JavaScript Standards

See `references/naming-conventions.md` for variable, function, and file naming examples.

See `references/patterns.md` for immutability, error handling, async/await, and type safety examples.

> See `/react-patterns` for comprehensive React component patterns, hooks, state management, Apollo/urql integration, and RTL testing.

## API Design Standards

See `references/api-design.md` for REST conventions, response format, and Zod input validation.

## File Organization

See `references/project-structure.md` for Next.js App Router layout and file naming conventions.

## Comments & Documentation

See `references/comments-jsdoc.md` for when-to-comment rules and JSDoc patterns.

## Performance Best Practices

### Memoization

```typescript
import { useMemo, useCallback } from 'react'

// ✅ GOOD: Memoize expensive computations
const sortedMarkets = useMemo(() => {
  return markets.sort((a, b) => b.volume - a.volume)
}, [markets])

// ✅ GOOD: Memoize callbacks
const handleSearch = useCallback((query: string) => {
  setSearchQuery(query)
}, [])
```

### Lazy Loading

```typescript
import { lazy, Suspense } from 'react'

// ✅ GOOD: Lazy load heavy components
const HeavyChart = lazy(() => import('./HeavyChart'))

export function Dashboard() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyChart />
    </Suspense>
  )
}
```

### Database Queries

```typescript
// ✅ GOOD: Select only needed columns
const users = await db
  .from('users')
  .select('id, name, status')
  .limit(10)

// ❌ BAD: Select everything
const users = await db
  .from('users')
  .select('*')
```

For testing standards, see /tdd-standards.

## Code Smell Detection

Watch for: long functions (>50 lines), deep nesting (5+ levels), magic numbers, dead code, inconsistent naming.

See `references/code-smells.md` for before/after examples of each anti-pattern.
