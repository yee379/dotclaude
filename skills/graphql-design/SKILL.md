---
name: graphql-design
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

```graphql
type Post {
  id: ID!            # always present
  title: String!     # always present
  body: String       # nullable — draft posts may have no body
  author: User!      # always present — post always has an author
  tags: [Tag!]!      # non-null list, non-null items — always returns array
  deletedAt: DateTime  # nullable — only set when deleted
}
```

### 3. Use custom scalars for semantic types

```graphql
scalar DateTime    # ISO-8601 string
scalar Date        # YYYY-MM-DD
scalar UUID        # validated UUID string
scalar JSON        # escape hatch for unstructured data (use sparingly)
scalar URL
scalar EmailAddress
scalar PositiveInt
```

### 4. Enums for finite sets

```graphql
enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}

enum SortDirection {
  ASC
  DESC
}
```

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

### Mutation naming: verb + noun

```graphql
type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
  updateUser(id: ID!, input: UpdateUserInput!): UpdateUserPayload!
  deleteUser(id: ID!): DeleteUserPayload!
  publishPost(id: ID!): PublishPostPayload!
  inviteTeamMember(input: InviteTeamMemberInput!): InviteTeamMemberPayload!
}
```

### Input types — always use an input wrapper

```graphql
input CreateUserInput {
  name: String!
  email: String!
  role: UserRole!
}

input UpdateUserInput {
  name: String
  email: String
  role: UserRole
  # All fields nullable — partial updates
}
```

### Payload types — return the mutated object + errors

```graphql
# Standard payload pattern
type CreateUserPayload {
  user: User            # null on failure
  errors: [UserError!]! # empty on success
}

type UserError {
  field: String         # null = global error
  message: String!
  code: UserErrorCode!
}

enum UserErrorCode {
  EMAIL_TAKEN
  INVALID_EMAIL
  INSUFFICIENT_PERMISSIONS
  NOT_FOUND
}
```

Client usage:

```graphql
mutation {
  createUser(input: { name: "Alice", email: "alice@example.com", role: ADMIN }) {
    user { id name email }
    errors { field message code }
  }
}
```

---

## N+1 Prevention with DataLoader

The single biggest performance issue in GraphQL. Always batch per-request.

### The problem

```
query {
  posts {          # 1 DB query → 100 posts
    author {       # 100 DB queries (1 per post) = N+1
      name
    }
  }
}
```

### The solution — DataLoader

```typescript
import DataLoader from "dataloader";

// One DataLoader per request (never singleton)
function createLoaders() {
  return {
    userById: new DataLoader<string, User>(async (ids) => {
      // Single batch query for all requested IDs
      const users = await db.users.findMany({
        where: { id: { in: ids as string[] } },
      });
      // Return in same order as input IDs
      const userMap = new Map(users.map((u) => [u.id, u]));
      return ids.map((id) => userMap.get(id) ?? new Error(`User ${id} not found`));
    }),

    postsByUserId: new DataLoader<string, Post[]>(async (userIds) => {
      const posts = await db.posts.findMany({
        where: { authorId: { in: userIds as string[] } },
      });
      const grouped = new Map<string, Post[]>();
      for (const post of posts) {
        const list = grouped.get(post.authorId) ?? [];
        list.push(post);
        grouped.set(post.authorId, list);
      }
      return userIds.map((id) => grouped.get(id) ?? []);
    }),
  };
}

// Attach loaders to context
const server = new ApolloServer({
  context: ({ req }) => ({
    loaders: createLoaders(),
    user: getAuthUser(req),
  }),
});

// Resolver uses loader
const resolvers = {
  Post: {
    author: (post, _, { loaders }) => loaders.userById.load(post.authorId),
  },
};
```

### DataLoader rules

- Create a new DataLoader instance **per request**, not per server start
- Key ordering must match — return results in same order as input keys
- Return `null` or an `Error` instance for missing keys, not `undefined`
- Use `.loadMany()` for optional batching, `.load()` for single items

---

## Resolver Structure

### Resolver map (TypeScript)

```typescript
const resolvers: Resolvers = {
  Query: {
    user: async (_, { id }, { loaders }) => loaders.userById.load(id),
    users: async (_, { filter, sort, first, after }, { db }) => {
      return paginateUsers({ db, filter, sort, first, after });
    },
    viewer: async (_, __, { user }) => {
      if (!user) return null;
      return user;
    },
  },

  Mutation: {
    createUser: async (_, { input }, { db, user: viewer }) => {
      if (!viewer || viewer.role !== "ADMIN") {
        return { user: null, errors: [{ field: null, message: "Insufficient permissions", code: "INSUFFICIENT_PERMISSIONS" }] };
      }
      const existing = await db.users.findUnique({ where: { email: input.email } });
      if (existing) {
        return { user: null, errors: [{ field: "email", message: "Email already taken", code: "EMAIL_TAKEN" }] };
      }
      const newUser = await db.users.create({ data: input });
      return { user: newUser, errors: [] };
    },
  },

  User: {
    posts: (user, _, { loaders }) => loaders.postsByUserId.load(user.id),
  },
};
```

### Authorization pattern

```typescript
// Centralise auth checks — never rely on field-level security alone
function requireAuth(context: Context) {
  if (!context.user) throw new GraphQLError("Not authenticated", {
    extensions: { code: "UNAUTHENTICATED" },
  });
  return context.user;
}

function requireRole(context: Context, role: UserRole) {
  const user = requireAuth(context);
  if (user.role !== role) throw new GraphQLError("Insufficient permissions", {
    extensions: { code: "FORBIDDEN" },
  });
  return user;
}

// Usage in resolver
Query: {
  adminStats: (_, __, ctx) => {
    requireRole(ctx, "ADMIN");
    return getAdminStats();
  },
}
```

---

## Error Handling

### Error categories

```typescript
import { GraphQLError } from "graphql";

// 1. Client errors — expose to consumer
throw new GraphQLError("User not found", {
  extensions: { code: "NOT_FOUND", id },
});

// 2. Auth errors
throw new GraphQLError("Not authenticated", {
  extensions: { code: "UNAUTHENTICATED" },
});

throw new GraphQLError("Forbidden", {
  extensions: { code: "FORBIDDEN" },
});

// 3. Validation errors via mutation payload (see Mutation Design above)
// Do NOT throw for validation failures — return them in the payload

// 4. Internal errors — mask details from client
throw new GraphQLError("Internal server error", {
  extensions: { code: "INTERNAL_SERVER_ERROR" },
  // original error logged server-side only
});
```

### Global error formatter

```typescript
const server = new ApolloServer({
  formatError: (formattedError, error) => {
    // Log internal errors with full details
    if (formattedError.extensions?.code === "INTERNAL_SERVER_ERROR") {
      console.error("GraphQL internal error", error);
      return { message: "Internal server error", extensions: { code: "INTERNAL_SERVER_ERROR" } };
    }
    // Return client errors as-is
    return formattedError;
  },
});
```

---

## Subscriptions

```graphql
type Subscription {
  postPublished(authorId: ID): Post!
  orderStatusChanged(orderId: ID!): Order!
  messageReceived(conversationId: ID!): Message!
}
```

```typescript
// Using graphql-ws (preferred over subscriptions-transport-ws)
Subscription: {
  messageReceived: {
    subscribe: async (_, { conversationId }, { pubsub, user }) => {
      if (!user) throw new GraphQLError("Not authenticated");
      // Verify user has access to conversation before subscribing
      await assertConversationAccess(conversationId, user.id);
      return pubsub.asyncIterator(`MESSAGE:${conversationId}`);
    },
    resolve: (payload) => payload.message,
  },
},

// Publishing
await pubsub.publish(`MESSAGE:${conversationId}`, { message: newMessage });
```

---

## Schema Federation (Apollo Federation v2)

```graphql
# users service
type User @key(fields: "id") {
  id: ID!
  name: String!
  email: String!
}

# posts service — extends User from users service
type User @key(fields: "id") {
  id: ID! @external
  posts: [Post!]!
}

type Post @key(fields: "id") {
  id: ID!
  title: String!
  author: User!
}
```

### Federation resolver

```typescript
// posts service reference resolver
User: {
  __resolveReference: async ({ id }, { loaders }) => {
    return loaders.userById.load(id);
  },
  posts: async (user, _, { db }) => {
    return db.posts.findMany({ where: { authorId: user.id } });
  },
},
```

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
