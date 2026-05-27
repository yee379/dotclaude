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

See `references/examples.md` for unit, integration, and E2E test boilerplate examples by framework.

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

See `references/mocking.md` for mock factory patterns and database/cache/service mock implementations.

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

## Success Metrics

- 80%+ code coverage achieved
- All tests passing (green)
- No skipped or disabled tests
- Fast test execution (< 30s for unit tests)
- E2E tests cover critical user flows
- Tests catch bugs before production
