## Custom Scalars

```graphql
scalar DateTime    # ISO-8601 string
scalar Date        # YYYY-MM-DD
scalar UUID        # validated UUID string
scalar JSON        # escape hatch for unstructured data (use sparingly)
scalar URL
scalar EmailAddress
scalar PositiveInt
```

## Enums for Finite Sets

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

## Non-Null Usage

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
