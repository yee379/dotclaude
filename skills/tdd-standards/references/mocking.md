## Mocking Guidelines

### Mock at system boundaries only

**Do mock:**
- External APIs (payment, email, third-party services)
- Databases — but prefer a real test database over mocking
- Time and randomness
- File system when I/O is the bottleneck

**Don't mock** your own classes, modules, or internal collaborators. If you feel the urge to mock something you control, that's a signal the interface needs redesigning, not a testing problem.

### Design for mockability

**Use dependency injection** — pass external dependencies in rather than creating them internally:

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock — creates its own dependency
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**Prefer SDK-style interfaces over generic fetchers** — one function per operation, not one function with conditional logic:

```typescript
// GOOD: each function is independently mockable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: mocking requires conditional logic inside the mock
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

SDK-style means each mock returns one specific shape, no conditional logic in test setup, and it's immediately clear which endpoints a test exercises.

### Mock implementations

Mock the internal adapter (`@/lib/db`), not the vendor SDK (`@supabase/supabase-js`). Return minimal stable shapes. Always provide a failure path mock alongside the success path.

```typescript
// Database mock
jest.mock('@/lib/db', () => ({
  db: {
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        eq: jest.fn(() => Promise.resolve({
          data: [{ id: '1', name: 'Test Item' }],
          error: null
        }))
      }))
    }))
  }
}))

// Cache / Vector Store mock
jest.mock('@/lib/cache', () => ({
  searchByVector: jest.fn(() => Promise.resolve([
    { id: 'item-1', score: 0.95 }
  ])),
  checkHealth: jest.fn(() => Promise.resolve({ connected: true }))
}))

// External API / Embedding mock
const EMBEDDING_DIMENSIONS = 1536  // match your model's output dimension

jest.mock('@/lib/embeddings', () => ({
  generateEmbedding: jest.fn(() => Promise.resolve(
    new Array(EMBEDDING_DIMENSIONS).fill(0.1)
  ))
}))
```
