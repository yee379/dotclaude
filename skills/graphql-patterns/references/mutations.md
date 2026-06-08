## Input Types — Always Use an Input Wrapper

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

## Payload Types — Return Object + Errors

```graphql
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

## Client Usage

```graphql
mutation {
  createUser(input: { name: "Alice", email: "alice@example.com", role: ADMIN }) {
    user { id name email }
    errors { field message code }
  }
}
```
