## Good vs Bad Tests — Additional Examples

These illustrate the same behavior-over-implementation principle as the two canonical pairs in SKILL.md.

```typescript
// BAD: Brittle selectors
await page.click('.css-class-xyz')

// GOOD: Semantic selectors
await page.click('button:has-text("Submit")')
await page.click('[data-testid="submit-button"]')

// BAD: No test isolation (test 2 depends on test 1's side effects)
test('creates user', () => { /* ... */ })
test('updates same user', () => { /* depends on previous test */ })

// GOOD: Independent tests
test('creates user', () => {
  const user = createTestUser()
  // Test logic
})
test('updates user', () => {
  const user = createTestUser()
  // Update logic
})

// BAD: Tests implementation detail (internal state)
expect(component.state.count).toBe(5)

// GOOD: Test user-visible behavior
expect(screen.getByText('Count: 5')).toBeInTheDocument()

// BAD: Bypasses interface to query database directly
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// GOOD: Verify through the interface
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

---

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
