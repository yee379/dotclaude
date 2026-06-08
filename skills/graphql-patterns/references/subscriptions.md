## Subscription Schema

```graphql
type Subscription {
  postPublished(authorId: ID): Post!
  orderStatusChanged(orderId: ID!): Order!
  messageReceived(conversationId: ID!): Message!
}
```

## Subscription Resolver (graphql-ws)

Use graphql-ws — preferred over the deprecated subscriptions-transport-ws.

```typescript
Subscription: {
  messageReceived: {
    subscribe: async (_, { conversationId }, { pubsub, user }) => {
      if (!user) throw new GraphQLError("Not authenticated");
      await assertConversationAccess(conversationId, user.id);
      return pubsub.asyncIterator(`MESSAGE:${conversationId}`);
    },
    resolve: (payload) => payload.message,
  },
},

// Publishing
await pubsub.publish(`MESSAGE:${conversationId}`, { message: newMessage });
```

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

## Federation Reference Resolver

```typescript
// posts service
User: {
  __resolveReference: async ({ id }, { loaders }) => {
    return loaders.userById.load(id);
  },
  posts: async (user, _, { db }) => {
    return db.posts.findMany({ where: { authorId: user.id } });
  },
},
```
