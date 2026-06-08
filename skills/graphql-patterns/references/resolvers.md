## Resolver Map (TypeScript)

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

## Authorization Pattern

Centralise auth checks — never rely on field-level security alone.

```typescript
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
