---
name: tdd-standards
description: Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with 80%+ coverage including unit, integration, and E2E tests.
origin: ECC
---

# Test-Driven Development Workflow

This skill ensures all code development follows TDD principles with comprehensive test coverage.

## When to Activate

- Writing new features or functionality
- Fixing bugs or issues
- Refactoring existing code
- Adding API endpoints
- Creating new components

## Core Principles

### 1. Tests BEFORE Code
ALWAYS write tests first, then implement code to make tests pass.

### 2. Coverage Requirements
- Minimum 80% coverage (unit + integration + E2E)
- All edge cases covered
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

## TDD Workflow Steps

### Step 1: Write User Journeys
```
As a [role], I want to [action], so that [benefit]

Example:
As a user, I want to search for items by keyword,
so that I can find relevant results even without exact matches.
```

### Step 2: Generate Test Cases
For each user journey, create comprehensive test cases:

```typescript
describe('Keyword Search', () => {
  it('returns relevant items for query', async () => {
    // Test implementation
  })

  it('handles empty query gracefully', async () => {
    // Test edge case
  })

  it('falls back to exact match when search index unavailable', async () => {
    // Test fallback behavior
  })

  it('sorts results by relevance score', async () => {
    // Test sorting logic
  })
})
```

### Step 3: Run Tests (They Should Fail)
```bash
npm test
# Tests should fail - we haven't implemented yet
```

### Step 4: Implement Code
Write minimal code to make tests pass:

```typescript
// Implementation guided by tests
export async function searchItems(query: string) {
  // Implementation here
}
```

### Step 5: Run Tests Again
```bash
npm test
# Tests should now pass
```

### Step 6: Refactor
Improve code quality while keeping tests green:
- Remove duplication
- Improve naming
- Optimize performance
- Enhance readability

### Step 7: Verify Coverage
```bash
npm run test:coverage
# Verify 80%+ coverage achieved
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

  // Verify page loaded
  await expect(page.locator('h1')).toContainText('Items')

  // Search
  await page.fill('input[placeholder="Search"]', 'widget')
  await page.waitForTimeout(400)  // debounce

  // Verify results
  const results = page.locator('[data-testid="item-card"]')
  await expect(results).toHaveCount(5, { timeout: 5000 })
  await expect(results.first()).toContainText('widget', { ignoreCase: true })

  // Apply a filter
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

## Mocking External Services

Mock at the module boundary — replace the internal adapter, not the third-party SDK directly.

### Database Mock (generic)
```typescript
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
```

### Cache / Vector Store Mock (generic)
```typescript
jest.mock('@/lib/cache', () => ({
  searchByVector: jest.fn(() => Promise.resolve([
    { id: 'item-1', score: 0.95 }
  ])),
  checkHealth: jest.fn(() => Promise.resolve({ connected: true }))
}))
```

### External API / Embedding Mock (generic)
```typescript
const EMBEDDING_DIMENSIONS = 1536  // match your model's output dimension (e.g. text-embedding-3-small)

jest.mock('@/lib/embeddings', () => ({
  generateEmbedding: jest.fn(() => Promise.resolve(
    new Array(EMBEDDING_DIMENSIONS).fill(0.1)  // fixed-dimension vector for test isolation
  ))
}))
```

**Rules:**
- Mock the internal adapter (`@/lib/db`), not the vendor SDK (`@supabase/supabase-js`)
- Return minimal, stable shapes — don't couple test data to production schema
- Always provide a failure path mock alongside the success path

## Test Coverage Verification

### Run Coverage Report
```bash
npm run test:coverage
```

### Coverage Thresholds
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

## Common Testing Mistakes to Avoid

### ❌ WRONG: Testing Implementation Details
```typescript
// Don't test internal state
expect(component.state.count).toBe(5)
```

### ✅ CORRECT: Test User-Visible Behavior
```typescript
// Test what users see
expect(screen.getByText('Count: 5')).toBeInTheDocument()
```

### ❌ WRONG: Brittle Selectors
```typescript
// Breaks easily
await page.click('.css-class-xyz')
```

### ✅ CORRECT: Semantic Selectors
```typescript
// Resilient to changes
await page.click('button:has-text("Submit")')
await page.click('[data-testid="submit-button"]')
```

### ❌ WRONG: No Test Isolation
```typescript
// Tests depend on each other
test('creates user', () => { /* ... */ })
test('updates same user', () => { /* depends on previous test */ })
```

### ✅ CORRECT: Independent Tests
```typescript
// Each test sets up its own data
test('creates user', () => {
  const user = createTestUser()
  // Test logic
})

test('updates user', () => {
  const user = createTestUser()
  // Update logic
})
```

## Python TDD (pytest)

For Python projects, follow the same Red → Green → Refactor cycle using pytest. See `/python-patterns` for full project structure and async fixture patterns.

### Unit Test Pattern (pytest)
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

### Integration Test Pattern (pytest + httpx)
```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_items_returns_200():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/items")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)

@pytest.mark.asyncio
async def test_invalid_query_param_returns_400():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/items?limit=bad")
    assert response.status_code == 400
```

### Mocking External Services (pytest)
```python
# Mock at the internal adapter boundary, not the vendor SDK
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_db(monkeypatch):
    mock = AsyncMock(return_value=[{"id": "1", "name": "Test Item"}])
    monkeypatch.setattr("app.db.fetch_items", mock)
    return mock

async def test_uses_db_result(mock_db):
    results = await search_items("test")
    mock_db.assert_called_once()
    assert results[0]["name"] == "Test Item"
```

### Coverage (pytest)
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

---

## Continuous Testing

### Watch Mode During Development
```bash
npm test -- --watch
# Tests run automatically on file changes
```

### Pre-Commit Hook
```bash
# Runs before every commit
npm test && npm run lint
```

### CI/CD Integration
```yaml
# GitHub Actions
- name: Run Tests
  run: npm test -- --coverage
- name: Upload Coverage
  uses: codecov/codecov-action@v4
```

## Best Practices

1. **Write Tests First** - Always TDD
2. **One Assert Per Test** - Focus on single behavior
3. **Descriptive Test Names** - Explain what's tested
4. **Arrange-Act-Assert** - Clear test structure
5. **Mock External Dependencies** - Isolate unit tests
6. **Test Edge Cases** - Null, undefined, empty, large
7. **Test Error Paths** - Not just happy paths
8. **Keep Tests Fast** - Unit tests < 50ms each
9. **Clean Up After Tests** - No side effects
10. **Review Coverage Reports** - Identify gaps

## Success Metrics

- 80%+ code coverage achieved
- All tests passing (green)
- No skipped or disabled tests
- Fast test execution (< 30s for unit tests)
- E2E tests cover critical user flows
- Tests catch bugs before production

---

**Remember**: Tests are not optional. They are the safety net that enables confident refactoring, rapid development, and production reliability.
