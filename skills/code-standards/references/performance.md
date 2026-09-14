# Performance

> Examples are TypeScript. The principles are language-agnostic.

## Fetch only what you need, and bound every result set

Select the columns you actually use, never the wildcard, and put an explicit limit on every
query. Unbounded reads are fine on a dev seed and fail in production, where the table is three
orders of magnitude larger. The cost lands on the database, the network, and the deserialiser at
once.

```typescript
// ✅ GOOD                                 // ❌ BAD
await db.from('users')                     await db.from('users')
  .select('id, name, status').limit(10)      .select('*')
```

The same rule holds outside SQL: name the fields in a GraphQL query, project in an aggregation
pipeline, page an API response. "Fetch everything and filter in app code" moves the work to the
slowest layer.

## Measure before optimising

Anything beyond the above is speculative until a profiler says otherwise. Premature optimisation
buys complexity with no evidence, and the ladder in `SKILL.md` applies: the fastest code is the
code never written.

Mark deliberate corners with their ceiling, so the next reader knows the bound rather than
rediscovering it: a global lock, an O(n²) scan over a list assumed small, a naive heuristic.

## Framework-specific

Memoisation (`useMemo`, `useCallback`) and lazy loading (`lazy` + `Suspense`) are in
`/react-patterns`, along with component patterns, hooks, state management, and Apollo/urql
integration.
