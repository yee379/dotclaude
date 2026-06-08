---
name: graphql-patterns
description: GraphQL schema design, resolver patterns, N+1 query prevention with DataLoader, pagination, mutations, subscriptions, schema federation, error handling, and performance for production APIs.
license: MIT
compatibility: opencode
---

# GraphQL Design

Patterns and conventions for building production-quality GraphQL APIs — schema first, resolver discipline, N+1 elimination, and federation.

## When to Use

- Designing or extending a GraphQL schema
- Writing resolvers (query, mutation, subscription)
- Fixing N+1 query problems
- Implementing cursor-based pagination
- Designing mutations with proper error handling
- Planning schema federation across services
- Reviewing GraphQL API performance

---

## Schema Design Principles

### 1. Design for the client, not the database

The schema is a product contract. Name fields after what they mean to consumers, not what they're called in your database.

```graphql
# BAD — leaks DB column names
type User {
  usr_id: ID!
  created_ts: String
  is_act: Boolean
}

# GOOD — clear, consumer-facing names
type User {
  id: ID!
  createdAt: DateTime!
  isActive: Boolean!
}
```

### 2. Non-null carefully

- Use `!` when the field can never be null for a valid object
- Do NOT make everything non-null — it forces clients to handle unexpected nulls as errors
- Nullable lists vs non-null items: `[Item!]` vs `[Item]!` vs `[Item!]!`

### 3. Use custom scalars for semantic types

### 4. Enums for finite sets

See `references/schema-design.md` for custom scalar definitions, enum examples, and non-null usage patterns.

---

## Query Design

### Nested resources

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

enum UserSortField {
  CREATED_AT
  NAME
  EMAIL
}
```

### Cursor-based pagination (Relay spec)

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

Usage:

```graphql
query {
  users(first: 20, after: "cursor123") {
    edges {
      node { id name email }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    totalCount
  }
}
```

---

## Mutation Design

Naming: verb + noun (`createUser`, `publishPost`). Always wrap args in an input type. Return the mutated object plus an `errors` array in the payload — never throw for validation failures.

Load `references/mutations.md` for input type, payload type, and client usage patterns.

---

## N+1 Prevention with DataLoader

The single biggest performance issue in GraphQL. Always batch per-request with one DataLoader instance per request (never singleton).

Load `references/dataloader.md` for DataLoader setup, resolver usage, and batching rules.

---

## Resolver Structure

Load `references/resolvers.md` for resolver map and centralised authorization patterns.

---

## Error Handling

Load `references/error-handling.md` for error category patterns and global error formatter.

---

## Subscriptions & Federation

Load `references/subscriptions.md` for subscription resolvers (graphql-ws) and Apollo Federation v2 patterns.

---

## Performance Checklist

Before shipping a GraphQL API:

- [ ] DataLoaders created per-request for all N+1-prone fields
- [ ] Query depth limiting configured (prevent deeply nested abuse)
- [ ] Query complexity limiting configured (prevent expensive queries)
- [ ] Persisted queries or operation allowlisting for public APIs
- [ ] Pagination required on all list fields (no unbounded lists)
- [ ] Introspection disabled in production
- [ ] Auth checks in resolvers, not just at the gateway
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
