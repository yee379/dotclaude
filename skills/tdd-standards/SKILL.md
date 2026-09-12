---
name: tdd-standards
description: Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with vertical slicing, behavior-focused tests, and 100%+ coverage including unit, integration, and E2E tests.
origin: ECC
---

# Test-Driven Development Workflow

For new features, bug fixes, refactors, new API endpoints, and new components.

## Philosophy

**Tests verify behaviour through public interfaces, not implementation details.** Code can change
entirely; tests shouldn't. Good tests are integration-style — they exercise real code paths
through public APIs and describe *what* the system does, not *how*. "User can checkout with valid
cart" names a capability and survives any internal refactor.

**Warning sign:** if renaming an internal function breaks tests without any change in observable
behaviour, those tests were testing implementation.

**Business logic is the highest-priority target.** Before coverage numbers, ask: have the domain
rules been tested? Pricing calculations, eligibility checks, state transitions, authorisation
rules, workflow invariants — these catch the regressions that matter. 95% coverage with no
business logic tests is more fragile than 75% that covers every domain rule.

## Core principles

### 1. Vertical slices, not horizontal

**Do not write all tests first, then all implementation.** Horizontal slicing produces tests for
imagined behaviour that are insensitive to real changes.

```
WRONG (horizontal):          RIGHT (vertical):
  RED:   test1..test5          RED→GREEN: test1→impl1
  GREEN: impl1..impl5          RED→GREEN: test2→impl2
                               RED→GREEN: test3→impl3
```

### 2. Coverage

**100% target** across unit + integration + E2E, and **extended, not just maintained** — when
touching existing code, ask what business rules in the area are untested and add them before
moving on. A PR that adds a feature but leaves adjacent untested domain logic is incomplete.

Pragmatic exceptions are allowed — generated code, third-party adapters, trivial boilerplate — but
every exclusion is explicit and justified in coverage config, never silent.

Business logic checklist, per feature or fix:

- [ ] The happy path through each domain rule
- [ ] State transitions and their guards — what's allowed, what's rejected
- [ ] Boundary values on any calculated or validated field
- [ ] Authorisation rules: who can do what, and what happens when they can't
- [ ] Any invariant the system must maintain (totals reconcile, status can't go backwards)

### 3. Test types

**Unit** — individual functions, component logic, pure functions, helpers.
**Integration** — API endpoints, database operations, service interactions, external API calls.
**E2E (Playwright)** — critical user flows, complete workflows, browser and UI interactions.

---

## Workflow

### Step 0: Plan before writing

- [ ] Confirm with the user what interface changes are needed
- [ ] Confirm which behaviours to test — critical paths before edge cases
- [ ] Write behaviours as user journeys: `As a [role], I want to [action], so that [benefit]`
- [ ] **Identify the business rules in scope** — domain constraints, calculations, state machines,
      authorisation checks. Test these even when they seem obvious
- [ ] **Scan existing tests for adjacent untested business logic** and add it to the list
- [ ] Get user sign-off on the list
- [ ] **If the plan calls for a version bump** — a behaviour or surface change, a removed
      endpoint, anything the project's version-history convention would log — confirm the exact
      version string with the user *now*, before writing code. **If they already named a version
      this session, that is the decision** — record it and move on. This checkpoint exists so the
      confirmation happens at the start of implementation rather than at closeout, where it is
      more expensive to fix. Full rule: `closeout-prd` Step 8.

Ask: "What should the public interface look like? Which behaviours matter most to test? Are there
business rules in this area that aren't currently tested?"

### Step 1: Tracer bullet

One test proving the end-to-end path works: `RED` (write test for the first behaviour, it fails) →
`GREEN` (minimal code, it passes). This confirms the wiring — runner works, framework configured,
structure holds.

### Step 2: Incremental loop

Then, **one behaviour at a time**: write the test, watch it fail, write only enough code to pass
it, watch it pass. Never anticipate future tests.

```typescript
describe('Keyword Search', () => {
  it('returns relevant items for query', async () => { })
  it('handles empty query gracefully', async () => { })
  it('falls back to exact match when search index unavailable', async () => { })
})
```

Per-cycle checklist, before the next test:

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

### Step 3: Refactor

Improve quality while tests stay green. **Never refactor while RED** — get to GREEN first.

Candidates: **duplication** → extract · **long methods** → private helpers, keeping tests on the
public interface · **shallow modules** → combine or deepen, so complexity lives behind simple
interfaces · **feature envy** → move logic to where the data lives · **primitive obsession** →
value objects · **existing code** the new code reveals as problematic.

### Step 4: Verify coverage

```bash
npm test -- --coverage                                       # JS/TS
pytest --cov=app --cov-report=term-missing --cov-fail-under=100   # Python
```

```json
{ "jest": { "coverageThresholds": { "global": {
  "branches": 100, "functions": 100, "lines": 100, "statements": 100 } } } }
```

```ini
# pyproject.toml
[tool.coverage.report]
fail_under = 100
```

Line coverage counts lines *executed*, not *asserted* — for judging whether the tests are worth
having (flakiness sources, over-mocking, the mutation question), see
`codebase-eng-review/references/test-adequacy-rubric.md`.

---

## Good vs bad tests

```typescript
// GOOD: observable behavior through the public API
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});

// BAD: asserts an internal collaborator was called — breaks on refactor, not on behavior change
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

**Red flags:** mocking internal collaborators · testing private methods · asserting call counts ·
a test name describing HOW not WHAT · direct DB queries instead of the interface.

More good/bad pairs (selectors, isolation, state vs behaviour) and per-framework boilerplate:
`references/examples.md`. Mock factory and database/cache/service mock patterns:
`references/mocking.md`.

## File organisation

```
src/
├── components/Button/
│   ├── Button.tsx
│   └── Button.test.tsx          # Unit
├── app/api/markets/
│   ├── route.ts
│   └── route.test.ts            # Integration
└── e2e/
    ├── markets.spec.ts          # E2E
    └── auth.spec.ts
```

Python projects follow the same Red → Green → Refactor cycle with pytest — see
`/python-patterns` for project structure, async fixtures, and `conftest.py` setup.

## Continuous testing

```bash
npm test -- --watch        # during development
npm test && npm run lint   # pre-commit
```

```yaml
# GitHub Actions
- name: Run Tests
  run: npm test -- --coverage
- name: Upload Coverage
  uses: codecov/codecov-action@v5
```

## Done when

- 100%+ coverage achieved and extended, with every exclusion justified
- All tests green; none skipped or disabled
- Unit tests run in under 30s; E2E covers the critical flows
- **Business logic explicitly covered** — domain rules, state transitions, authorisation checks,
  and invariants each have at least one test
- **Adjacent untested logic addressed** before the PR closes
