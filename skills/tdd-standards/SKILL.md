---
name: tdd-standards
description: Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with vertical slicing, behavior-focused tests, and 80%+ coverage including unit, integration, and E2E tests.
origin: ECC
---

# Test-Driven Development Workflow

## When to Activate

- Writing new features or functionality
- Fixing bugs or issues
- Refactoring existing code
- Adding API endpoints
- Creating new components

## Philosophy

**Core principle**: Tests should verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

Good tests are integration-style: they exercise real code paths through public APIs. They describe *what* the system does, not *how* it does it. "User can checkout with valid cart" tells you exactly what capability exists and survives any internal refactor.

**Warning sign**: If you rename an internal function and tests fail without any change in observable behavior, those tests were testing implementation, not behavior.

## Core Principles

### 1. Vertical Slices, Not Horizontal

**DO NOT write all tests first, then all implementation.** This is horizontal slicing — it produces tests that test imagined behavior, not actual behavior, and become insensitive to real changes.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

### 2. Coverage Requirements

- Minimum 80% coverage (unit + integration + E2E) — a floor, not a goal
- **You can't test everything** — focus on critical paths and complex logic, not every edge case
- Error scenarios tested
- Boundary conditions verified

### 3. Test Types

#### Unit Tests
- Individual functions and utilities
- Component logic
- Pure functions
- Helpers and utilities

#### Integration Tests
- API endpoints
- Database operations
- Service interactions
- External API calls

#### E2E Tests (Playwright)
- Critical user flows
- Complete workflows
- Browser automation
- UI interactions

## TDD Workflow

### Step 0: Plan Before Writing

Before any tests:

- [ ] Confirm with user what interface changes are needed
- [ ] Confirm which behaviors to test — prioritise critical paths over edge cases
- [ ] Write behaviors as user journeys: `As a [role], I want to [action], so that [benefit]`
- [ ] List behaviors to test (not implementation steps)
- [ ] Get user sign-off on the list

Ask: "What should the public interface look like? Which behaviors are most important to test?"

### Step 1: Tracer Bullet

Write ONE test that proves the end-to-end path works:

```
RED:   Write test for first behavior → fails
GREEN: Write minimal code to pass → passes
```

This confirms the wiring — test runner works, framework is configured, basic structure holds.

### Step 2: Incremental Loop

For each remaining behavior, one at a time:

```typescript
describe('Keyword Search', () => {
  it('returns relevant items for query', async () => { })
  it('handles empty query gracefully', async () => { })
  it('falls back to exact match when search index unavailable', async () => { })
})
```

**Per-cycle checklist** — before moving to the next test:
```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

### Step 3: Run Tests (They Should Fail)

```bash
npm test
# Tests should fail — implementation doesn't exist yet
```

### Step 4: Implement (Minimal)

Write only enough code to pass the current test. Don't anticipate future tests.

### Step 5: Run Tests Again

```bash
npm test
# Tests should now pass
```

### Step 6: Refactor

Improve code quality while keeping tests green. **Never refactor while RED.** Get to GREEN first.

Refactor candidates:
- **Duplication** → Extract function/class
- **Long methods** → Break into private helpers (keep tests on public interface)
- **Shallow modules** → Combine or deepen — complexity should live behind simple interfaces
- **Feature envy** → Move logic to where data lives
- **Primitive obsession** → Introduce value objects
- **Existing code** the new code reveals as problematic

### Step 7: Verify Coverage

```bash
npm run test:coverage
# Verify 80%+ coverage achieved
```

## Good vs Bad Tests

### Good Tests

Test behavior through public interfaces. Survive internal refactors.

```typescript
// GOOD: Tests observable behavior
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});

// GOOD: Verifies through interface, not internal state
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

### Bad Tests

Coupled to implementation — they break on refactor without any behavior change.

```typescript
// BAD: Tests that an internal collaborator was called
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});

// BAD: Bypasses interface to query database directly
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});
```

**Red flags:**
- Mocking internal collaborators (your own classes/modules)
- Testing private methods
- Asserting on call counts or call order
- Test breaks when you refactor without changing behavior
- Test name describes HOW not WHAT
- Verifying through external means (direct DB query) instead of the interface

### Common Mistakes

#### ❌ WRONG: Testing Implementation Details
```typescript
expect(component.state.count).toBe(5)
```

#### ✅ CORRECT: Test User-Visible Behavior
```typescript
expect(screen.getByText('Count: 5')).toBeInTheDocument()
```

#### ❌ WRONG: Brittle Selectors
```typescript
await page.click('.css-class-xyz')
```

#### ✅ CORRECT: Semantic Selectors
```typescript
await page.click('button:has-text("Submit")')
await page.click('[data-testid="submit-button"]')
```

#### ❌ WRONG: No Test Isolation
```typescript
test('creates user', () => { /* ... */ })
test('updates same user', () => { /* depends on previous test */ })
```

#### ✅ CORRECT: Independent Tests
```typescript
test('creates user', () => {
  const user = createTestUser()
  // Test logic
})

test('updates user', () => {
  const user = createTestUser()
  // Update logic
})
```

## Testing Patterns

### Unit Test Pattern (Jest/Vitest)
```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from './Button'

describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
```

### API Integration Test Pattern
```typescript
import { NextRequest } from 'next/server'
import { GET } from './route'

describe('GET /api/items', () => {
  it('returns items successfully', async () => {
    const request = new NextRequest('http://localhost/api/items')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(Array.isArray(data.data)).toBe(true)
  })

  it('validates query parameters', async () => {
    const request = new NextRequest('http://localhost/api/items?limit=invalid')
    const response = await GET(request)
    expect(response.status).toBe(400)
  })

  it('handles database errors gracefully', async () => {
    const request = new NextRequest('http://localhost/api/items')
    // Mock db failure and assert 500 + error shape
  })
})
```

### E2E Test Pattern (Playwright)
```typescript
import { test, expect } from '@playwright/test'

test('user can search and filter items', async ({ page }) => {
  await page.goto('/items')
  await expect(page.locator('h1')).toContainText('Items')

  await page.fill('input[placeholder="Search"]', 'widget')
  await page.waitForResponse(resp => resp.url().includes('/api') && resp.status() === 200)

  const results = page.locator('[data-testid="item-card"]')
  await expect(results).toHaveCount(5, { timeout: 5000 })
  await expect(results.first()).toContainText('widget', { ignoreCase: true })

  await page.click('button:has-text("Active")')
  await expect(results).toHaveCount(3)
})

test('user can create a new item', async ({ page }) => {
  await page.goto('/dashboard')

  await page.fill('input[name="name"]', 'Test Item')
  await page.fill('textarea[name="description"]', 'Test description')
  await page.click('button[type="submit"]')

  await expect(page.locator('[data-testid="success-message"]')).toBeVisible()
  await expect(page).toHaveURL(/\/items\/test-item/)
})
```

## Test File Organization

```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx          # Unit tests
│   │   └── Button.stories.tsx       # Storybook
│   └── MarketCard/
│       ├── MarketCard.tsx
│       └── MarketCard.test.tsx
├── app/
│   └── api/
│       └── markets/
│           ├── route.ts
│           └── route.test.ts         # Integration tests
└── e2e/
    ├── markets.spec.ts               # E2E tests
    ├── trading.spec.ts
    └── auth.spec.ts
```

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

## Test Coverage Verification

```bash
npm run test:coverage
```

```json
{
  "jest": {
    "coverageThresholds": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

## Python TDD (pytest)

For Python projects, follow the same Red → Green → Refactor cycle using pytest. See `/python-patterns` for full project structure and async fixture patterns.

```python
# tests/unit/test_search.py
import pytest
from app.search import search_items

def test_returns_results_for_valid_query():
    results = search_items("widget")
    assert len(results) > 0
    assert all("widget" in r["name"].lower() for r in results)

def test_returns_empty_list_for_no_matches():
    results = search_items("xyzzy_nonexistent")
    assert results == []

def test_raises_on_invalid_input():
    with pytest.raises(ValueError):
        search_items(None)
```

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

```ini
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.coverage.report]
fail_under = 80
```

## Continuous Testing

```bash
npm test -- --watch        # watch mode during development
npm test && npm run lint   # pre-commit
```

```yaml
# GitHub Actions
- name: Run Tests
  run: npm test -- --coverage
- name: Upload Coverage
  uses: codecov/codecov-action@v4
```

## Best Practices

1. **Vertical slices** — one test → one implementation, never bulk RED then bulk GREEN
2. **Behavior not implementation** — test what it does, not how it does it
3. **One assertion per test** — focus on a single observable outcome
4. **Descriptive names** — describe WHAT, not HOW
5. **Mock system boundaries only** — never mock what you control
6. **Dependency injection** — design interfaces to be testable from the start
7. **Test error paths** — not just happy paths
8. **Keep tests fast** — unit tests < 50ms each
9. **Independent tests** — each test sets up its own data
10. **Review coverage reports** — identify gaps, not just hit the number

## Success Metrics

- 80%+ code coverage achieved
- All tests passing (green)
- No skipped or disabled tests
- Fast test execution (< 30s for unit tests)
- E2E tests cover critical user flows
- Tests catch bugs before production
