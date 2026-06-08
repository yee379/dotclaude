## DataLoader Setup

One DataLoader instance per request — never singleton.

```typescript
import DataLoader from "dataloader";

function createLoaders() {
  return {
    userById: new DataLoader<string, User>(async (ids) => {
      const users = await db.users.findMany({
        where: { id: { in: ids as string[] } },
      });
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

// Attach to context
const server = new ApolloServer({
  context: ({ req }) => ({
    loaders: createLoaders(),
    user: getAuthUser(req),
  }),
});
```

## Resolver Usage

```typescript
const resolvers = {
  Post: {
    author: (post, _, { loaders }) => loaders.userById.load(post.authorId),
  },
};
```

## Rules

- Create a new DataLoader instance **per request**, not per server start
- Key ordering must match — return results in same order as input keys
- Return `null` or an `Error` instance for missing keys, not `undefined`
- Use `.loadMany()` for optional batching, `.load()` for single items
