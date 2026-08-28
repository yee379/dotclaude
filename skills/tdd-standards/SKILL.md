---
name: tdd-standards
description: Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with vertical slicing, behavior-focused tests, and 100%+ coverage including unit, integration, and E2E tests.
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

**Business logic is the highest-priority test target.** Before thinking about coverage numbers, ask: have the domain rules been tested? Pricing calculations, eligibility checks, state transitions, authorization rules, workflow invariants — these are the tests that catch regressions that matter. A codebase with 95% coverage but no business logic tests is more fragile than one at 75% that covers every domain rule.

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

- **100% coverage target** (unit + integration + E2E)
- Pragmatic exceptions are allowed — generated code, third-party adapters, and trivial boilerplate may be excluded via coverage config — but every exclusion must be explicit and justified, never silent
- Focus on critical paths, complex logic, and business rules first; fill remaining gaps to reach 100%
- Error scenarios tested
- Boundary conditions verified

**Coverage must be extended, not just maintained.** When touching existing code, look at the surrounding test suite and ask: what business rules in this area are untested? Add tests for them before moving on. A PR that adds a feature but leaves adjacent untested domain logic is incomplete.

**Business logic coverage checklist** — for every feature or fix, verify tests exist for:
- [ ] The happy path through each domain rule
- [ ] State transitions and their guards (what's allowed, what's rejected)
- [ ] Boundary values on any calculated or validated field
- [ ] Authorization rules (who can do what, and what happens when they can't)
- [ ] Any invariant the system must maintain (e.g. totals always reconcile, status can't go backwards)

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
- [ ] **Identify the business rules in scope** — domain constraints, calculations, state machines, authorization checks. These must be tested even if they seem obvious.
- [ ] **Scan existing tests for adjacent untested business logic** — any domain rules in the area being changed that currently have no test coverage should be added to the list
- [ ] List behaviors to test (not implementation steps)
- [ ] Get user sign-off on the list
- [ ] **If the plan calls for a version bump** (a behavior/surface change, a removed
      endpoint, anything the project's own version-history convention would log) —
      confirm the exact version string with the user before writing any code. Never bump
      a version file without asking, even mid-implementation when it's easy to forget in
      the flow of writing tests. See `closeout-prd`'s "NEVER BUMP VERSION WITHOUT
      ASKING" for the full rule — this checkpoint exists so the confirmation happens at
      the start of implementation, not only at closeout when it's more expensive to fix.

Ask: "What should the public interface look like? Which behaviors are most important to test? Are there business rules in this area that aren't currently tested?"

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
# Verify 100%+ coverage achieved
```

## Good vs Bad Tests

Test behavior through public interfaces. Survive internal refactors.

```typescript
// GOOD: Tests observable behavior through the public API
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});

// BAD: Tests that an internal collaborator was called (breaks on refactor, not behavior change)
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

**Red flags:** mocking internal collaborators, testing private methods, asserting call counts, test name describes HOW not WHAT, direct DB queries instead of using the interface.

See `references/examples.md` for additional good/bad pairs (selectors, isolation, state vs behavior).

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
        "branches": 100,
        "functions": 100,
        "lines": 100,
        "statements": 100
      }
    }
  }
}
```

## Python TDD (pytest)

For Python projects, follow the same Red → Green → Refactor cycle using pytest. See `/python-patterns` for full project structure, async fixture patterns, and `conftest.py` setup.

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=100
```

```ini
# pyproject.toml
[tool.coverage.report]
fail_under = 100
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
  uses: codecov/codecov-action@v5
```

## Success Metrics

- 100%+ code coverage achieved — and extended, not just maintained
- All tests passing (green)
- No skipped or disabled tests
- Fast test execution (< 30s for unit tests)
- E2E tests cover critical user flows
- **Business logic is explicitly covered** — domain rules, state transitions, authorization checks, and invariants each have at least one test
- **Adjacent untested logic addressed** — any business logic near changed code that lacked tests has been covered before the PR closes
- Tests catch bugs before production
