# Interface, Contract, and Coupling Review

Loaded at §2 of `/codebase-eng-review`, after the DRY and module-split checks. **Trigger:** the
change adds or modifies any public function, method, class, schema, or module boundary.

`/codebase-arch-review` §1 checks whether the *service* boundaries are in the right place. This
file checks the boundaries inside them — the signatures, error contracts, and types that decide
whether the code is pleasant or miserable to change in a year. It is the highest-leverage section
for long-term maintainability and the one most often skipped, because nothing here is *broken*.

---

## 1. Signature design

| Anti-pattern | Example | Why it costs | Fix |
|---|---|---|---|
| Boolean trap | `render(doc, True, False)` | Unreadable at the call site; every reader opens the definition | Enum, or keyword-only args |
| Flag that switches behaviour | `sync(dry_run=True)` branching the whole body | Two functions wearing one name; tests must cover both through one door | Split them |
| Primitive obsession | `transfer(str, str, float)` | Nothing stops `transfer(to, from, …)`; money as float (see `correctness-classics.md`) | `NewType`/dataclass for IDs, `Decimal` for money |
| Too many parameters | 6+ positional args | Call sites become unreadable and mis-ordered | A parameter object, or the function does two things |
| Optional arg that changes the return shape | `fetch(id, expand=True)` returning a different type | Callers must branch on what they passed | Two functions, or one shape |
| Out-params / arg mutation | `def process(items, results)` | Aliasing bugs; caller cannot tell it was modified | Return a new value |
| Union returns | `-> User \| None \| ErrorDict` | Every caller writes the same three-way branch, and one forgets | Pick one contract (§2) |

Also check: does the parameter order match the sibling functions in the module? Inconsistent
argument order across a family of functions is a permanent low-grade bug source.

## 2. Error contract

**One module, one convention.** A module where some functions raise, some return `None`, and one
returns a `(result, error)` tuple forces every caller to remember which — and they will not.

- [ ] The convention is stated and consistent within the module
- [ ] Exceptions are **domain-typed**, not bare `Exception`/`ValueError`. A caller that must
      inspect the message string to decide what to do has no contract at all
- [ ] Exception names describe the **caller's decision**, not the implementation:
      `PaymentDeclined` (retry pointless) vs `PaymentGatewayUnavailable` (retry sensible) —
      the distinction is exactly what the retry logic in `resilience-review.md` needs
- [ ] `None` does not mean three different things (not found / not permitted / not yet computed)
- [ ] Batch APIs report **per-item** outcomes; a batch call that raises on the first bad item
      makes partial success impossible to handle
- [ ] Exceptions crossing a module boundary are wrapped in that boundary's vocabulary —
      a `psycopg.IntegrityError` escaping into the HTTP layer is a leaked abstraction

**Define errors out of existence** (Ousterhout). The best error handling is an API where the
error cannot occur: `unset(key)` as a no-op instead of raising `KeyError`; a `get` that returns
an empty collection rather than `None`; an idempotent `ensure_x` instead of `create_x` plus an
exists-check. For each new error path, ask whether the interface could make it unreachable — this
removes handling code at every call site, not just one.

## 3. Make illegal states unrepresentable

- **Conditionally-required fields** are a type smell: if `status == 'shipped'` requires
  `shipped_at` to be set, a single struct with both optional lets every consumer forget the
  invariant. Use a tagged union / separate types per state.
- **Parse, don't validate.** Convert untrusted input into a validated type **once**, at the
  boundary, and have the interior accept only that type. Validation scattered through the
  interior means every new call site is a chance to miss it — and you can never prove it is done.
- **Stringly-typed** enums, statuses, and units. If a typo is a valid value, the compiler and
  the reviewer are both out of the loop.
- **Optional that is never `None` in practice** — it forces defensive checks forever. Either it
  is genuinely optional or it is not.

## 4. Boundary normalisation

Everything ambiguous should be resolved once, at the edge, and never again:

- [ ] Timestamps parsed to timezone-aware UTC at the boundary (`correctness-classics.md` §1)
- [ ] Money parsed to `Decimal` / minor units at the boundary
- [ ] IDs parsed to their newtype, not passed as `str` through ten frames
- [ ] Text normalised (NFC) and trimmed at the boundary
- [ ] **Absent vs null vs empty** distinguished where it matters — a PATCH that cannot tell
      "field omitted" from "field set to null" cannot express "clear this field", and will
      eventually wipe data it did not mean to

## 5. Depth over breadth

- **Interface complexity vs implementation complexity.** A module earns its existence by hiding
  more than it exposes. If the interface is nearly as complicated as what it wraps, it is a
  shallow wrapper with negative value — delete it and call through.
- **Pull complexity downward.** Given a choice between a fiddly implementation and a fiddly
  interface, take the fiddly implementation: it is paid once, the interface is paid at every
  call site. Flag any change that exports a new sequencing requirement, a new flag, or a new
  "remember to also call…" to its callers.
- **Pass-through methods and pass-through parameters** — a method that only forwards to another
  object, or an argument threaded through five frames untouched, both signal a boundary in the
  wrong place.
- **Knob proliferation.** Every new configuration option is complexity exported to whoever runs
  the thing. Is the default right for production? If the option exists only because the right
  default was not decided, decide it instead.

## 6. Coupling hygiene

- [ ] **No import cycles** introduced (`import-linter`, `madge`, or `python -c "import x"` on a
      cold interpreter). A cycle broken by a function-local import is a cycle that will bite
      during initialisation ordering
- [ ] **No layering violation** — domain/core importing infrastructure, framework, or HTTP types.
      If the core needs the web framework's `Request`, the dependency points the wrong way
- [ ] **No new global mutable state**, module-level singleton, or import-time side effect
      (connections opened, config read, clients constructed at import). These make tests
      order-dependent (see `test-adequacy-rubric.md` §4) and startup failures untraceable
- [ ] **Temporal coupling** — anything that must be called in a specific order (`init()` before
      use, `connect()` before `query()`). Can the type system make the wrong order impossible
      (a constructor returning the connected object, a context manager)?
- [ ] **Feature envy** — a new function that only reads another object's fields belongs on that
      object; leaving it outside means the invariant it enforces can be bypassed

---

## Required output

For each new or modified public interface, one line: **what it hides**, **what it exposes**, and
**what a caller can still get wrong**. That third column is the review's real product.

**STOP.** One AskUserQuestion per issue. Map each recommendation to a stated preference —
"explicit over clever" for boolean traps, "engineered enough" for knob proliferation, "minimal
diff" when declining to restructure something that merely offends.
