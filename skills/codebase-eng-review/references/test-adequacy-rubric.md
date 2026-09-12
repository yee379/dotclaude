# Test Adequacy Rubric — Codebase Changes

Loaded at §3 of `/codebase-eng-review`, after the test diagram. The diagram says **what** needs
testing; this file judges whether the proposed tests are **worth having**. `/tdd-standards` owns
how to write them during implementation — this is the gate on the plan.

The governing question is not "are there tests?" but:

> If the implementation were subtly wrong, would any of these tests fail?

---

## 1. The bar, per change type

| Change type | Required coverage |
|---|---|
| New behaviour | Unit test per branch · integration test across the real seam (DB, serialiser, client) · one E2E on the critical path |
| **Bug fix** | A test that **fails against the current code**, written first. Without it the bug is not fixed — it is moved |
| Refactor | The existing suite passes **unchanged**. If tests must be edited, this is a behaviour change mislabelled as a refactor |
| New external dependency | A test against a real or containerised instance, not only a mock (see §3) |
| New error path | A test that triggers the error, not just the happy path |
| Performance change | A benchmark or an assertion with a number in it |
| Security control | An automated **negative** test — the denied case returns denied. Cross-ref `/security-review` |
| Concurrency / idempotency | A test that runs the operation twice, or two workers concurrently, and asserts the invariant |
| Migration | Forward applied to realistic data, **and** rollback applied, both asserted |
| LLM / prompt change | Named eval suites, added cases, baseline to compare — per `SKILL.md` §3 |

A plan proposing less than its change type requires is **incomplete**, not "lightly tested".

## 2. Would the test catch the bug?

Apply the mutation question to each proposed test. If I were to:

- invert a condition,
- make the function return a constant,
- delete the line that performs the side effect,
- skip the authorisation check,

…which named test fails? If the answer is "none" or "unclear", the test is measuring coverage,
not correctness.

Flag these specifically:

- **Assertions on interactions instead of outcomes.** `assert mock_send.called` proves a call was
  made, not that the right thing happened. Assert the observable result
- **Tautological tests** — an expectation computed by the same logic under test, or a snapshot
  regenerated whenever it fails
- **Tests asserting implementation detail** — private method calls, internal ordering, log text.
  These break on every refactor and pass through every real bug, which is exactly backwards
- **A single test with fifteen assertions** — the first failure hides the rest, and the name tells
  you nothing about what broke

## 3. Over-mocking

The failure mode: the test suite is green, the code is broken, and the mock is the reason.

| Signal | Why it matters |
|---|---|
| Mocking your own modules | Mock at the process boundary, not at the neighbour. Internal mocks freeze the current internal design into the test |
| Hand-written mock return shapes | They drift from the real schema. The test passes; production returns a 500 on a missing field. Build fixtures from the real type/schema/response, not from memory |
| More setup lines than assertion lines | The test is describing the implementation back to itself |
| Everything mocked | The test exercises the mock framework |
| No test crosses the real seam | Nothing verifies the query is valid SQL, the serialiser round-trips, or the client speaks the right protocol. One integration test per seam catches more than fifty mocked units |

Preferred order: real object → in-memory/containerised substitute (sqlite, testcontainers, a fake
transport) → mock at the process boundary → mock internals (justify it).

## 4. Flakiness — check each source

A flaky test is worse than no test: it teaches the team that red means "run it again", and then
a real failure is ignored too.

| Source | Smell in the plan | Fix |
|---|---|---|
| Wall clock | `datetime.now()` in code under test, dates near midnight, "expires in 1 hour" | Inject or freeze the clock |
| `sleep` for coordination | `sleep(2)` then assert | Wait-for-condition with a timeout |
| Real network / DNS | Hitting a live URL, unpinned registry | Stub at the boundary, or mark as integration and gate it |
| Shared state between tests | One long-lived database or singleton, ordering assumptions | Per-test transaction rollback or fresh fixture |
| Test-order dependence | Passes alone, fails in the suite | Randomise order in CI so it surfaces immediately |
| Unordered results asserted as ordered | Comparing a query result or set to a list | Sort, or compare as sets |
| Parallel workers | Shared port, temp path, or fixture row | Per-worker isolation |
| Unseeded randomness | Faker, `random`, UUIDs in assertions | Seed, and print the seed on failure |
| Resource leak | Later tests fail after an earlier one exhausts connections | Guaranteed teardown |

## 5. What is worth more than another unit test

- **Property-based tests** (Hypothesis) wherever an invariant exists — encode/decode round-trips,
  idempotency (`f(f(x)) == f(x)`), ordering and monotonicity, "the total always equals the sum of
  parts", any parser. One property replaces dozens of examples and finds the case nobody imagined
- **Fuzzing** for any parser or deserialiser that touches untrusted input
- **Contract tests** at a service boundary, so the consumer's expectation and the provider's
  behaviour are verified against the same artefact
- **Golden/approval tests** for large stable outputs — worthwhile *only* with the discipline that
  a diff is reviewed rather than blessed; otherwise they decay into rubber stamps
- **One end-to-end test on the money path** is worth twenty more on the happy path

## 6. Coverage that lies

- Line coverage counts lines **executed**, not lines **asserted**. A test with no assertions
  still produces coverage
- The uncovered branches are systematically the dangerous ones: error handlers, retry paths,
  `finally`/cleanup, the flag-off path, migration rollback, timeout handling
- A high-coverage suite with no failure-path assertions is the common shape of "100% covered and
  broken in production"
- Ask for coverage **of the diff's error paths** specifically, not a global percentage

---

## Verdict

**Blocking** — any of:
- A bug fix with no test that fails against current code
- A new authorisation or security control with no automated negative test
- No test crosses a new external seam
- A new idempotent-by-requirement path with no double-execution test
- A named flakiness source with no mitigation

**Warning** — any of:
- Behaviour assertions absent but present elsewhere in the suite
- Over-mocking signals present but a real seam is covered elsewhere
- Property-based or fuzz testing clearly applicable and not proposed
- Error paths uncovered where the failure would be visible but not silent

Record the verdict as a table — dimension, adequate/inadequate, the plan's own step that covers
it or the gap. Do not soften a blocking finding into a warning.

**STOP.** One AskUserQuestion per gap. Never batch.
