## Error Categories

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

// 3. Validation errors via mutation payload (see mutations.md)
// Do NOT throw for validation failures — return them in the payload

// 4. Internal errors — mask details from client
throw new GraphQLError("Internal server error", {
  extensions: { code: "INTERNAL_SERVER_ERROR" },
  // original error logged server-side only
});
```

## Global Error Formatter

```typescript
const server = new ApolloServer({
  formatError: (formattedError, error) => {
    if (formattedError.extensions?.code === "INTERNAL_SERVER_ERROR") {
      console.error("GraphQL internal error", error);
      return { message: "Internal server error", extensions: { code: "INTERNAL_SERVER_ERROR" } };
    }
    return formattedError;
  },
});
```
