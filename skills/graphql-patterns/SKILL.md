---
name: graphql-patterns
description: GraphQL schema design, resolver patterns, N+1 query prevention with DataLoader, pagination, mutations, subscriptions, schema federation, error handling, and performance for production APIs.
license: MIT
compatibility: opencode
---

# GraphQL Design

Patterns for production-quality GraphQL APIs — schema first, resolver discipline, N+1
elimination, and federation. Use when designing or extending a schema, writing resolvers, fixing
N+1 problems, implementing cursor pagination, designing mutation error handling, planning
federation, or reviewing API performance.

## Schema design

**Design for the client, not the database.** The schema is a product contract — name fields for
what they mean to consumers, not what the DB calls them.

```graphql
# BAD — leaks DB column names        # GOOD — consumer-facing
type User {                          type User {
  usr_id: ID!                          id: ID!
  created_ts: String                   createdAt: DateTime!
  is_act: Boolean                      isActive: Boolean!
}                                    }
```

**Non-null carefully.** Use `!` only where the field can never be null for a valid object. Making
everything non-null forces clients to treat unexpected nulls as hard errors. Mind the difference
between `[Item!]`, `[Item]!`, and `[Item!]!`.

**Custom scalars for semantic types; enums for finite sets.** Definitions, enum examples, and
non-null usage patterns: `references/schema-design.md`.

## Query design

```graphql
type Query {
  # Fetch by ID — returns null if not found (not an error)
  user(id: ID!): User

  # List with filtering + pagination
  users(filter: UserFilter, sort: UserSort, first: Int, after: String): UserConnection!

  # Viewer pattern — current authenticated user
  viewer: User
}

input UserFilter {
  isActive: Boolean
  role: UserRole
  createdAfter: DateTime
  search: String
}

input UserSort {
  field: UserSortField!
  direction: SortDirection!
}

enum UserSortField { CREATED_AT  NAME  EMAIL }
```

Cursor-based pagination follows the Relay spec:

```graphql
type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type UserEdge {
  node: User!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

Clients page with `users(first: 20, after: "cursor123")`, reading `pageInfo.endCursor` for the
next call.

## Mutations

Naming is verb + noun (`createUser`, `publishPost`). Always wrap arguments in an input type.
Return the mutated object plus an `errors` array in the payload — **never throw for validation
failures**. Input type, payload type, and client usage: `references/mutations.md`.

## N+1 prevention

The single biggest performance issue in GraphQL. Batch per-request with **one DataLoader instance
per request** — never a singleton. Setup, resolver usage, and batching rules:
`references/dataloader.md`.

## Other references

| Topic | File |
|---|---|
| Resolver map and centralised authorisation | `references/resolvers.md` |
| Error category patterns and global error formatter | `references/error-handling.md` |
| Subscription resolvers (graphql-ws) and Apollo Federation v2 | `references/subscriptions.md` |

## Performance and safety checklist

- [ ] DataLoaders created per-request for all N+1-prone fields
- [ ] Query depth limiting configured
- [ ] Query complexity limiting configured
- [ ] **Rate limits count operations, not HTTP requests** — aliasing and batching let one request
      carry N operations, which walks straight through a request-count limiter (e.g. 1000 login
      attempts in one POST). See `/security-review` `references/vuln-classes.md` class 13
- [ ] Persisted queries or operation allowlisting for public APIs
- [ ] Pagination required on every list field — no unbounded lists
- [ ] Introspection disabled in production
- [ ] Auth checks **in every resolver**, not just at the gateway — a field denied via one parent
      is often reachable via another
- [ ] Subscription topics namespaced per resource ID
- [ ] Error details masked for internal errors
- [ ] Response caching (Apollo Cache-Control hints) on read-heavy queries

```typescript
// Depth + complexity limits (Apollo Server)
import depthLimit from "graphql-depth-limit";
import { createComplexityLimitRule } from "graphql-validation-complexity";

const server = new ApolloServer({
  validationRules: [
    depthLimit(7),
    createComplexityLimitRule(1000),
  ],
  introspection: process.env.NODE_ENV !== "production",
});
```
