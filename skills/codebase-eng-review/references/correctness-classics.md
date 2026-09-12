# Correctness Classics

Loaded at §7 of `/codebase-eng-review`. These are the defects that are found in production and
almost never in review — not because they are subtle, but because nobody is looking for them.
Each section is cheap to check and expensive to miss.

**Work only the sections the change triggers.** State which ones you skipped and why.

---

## 1. Time and clocks

*Trigger:* any timestamp, duration, expiry, schedule, or date arithmetic.

- [ ] **Aware, not naive.** `datetime.now()` and `datetime.utcnow()` both produce naive objects;
      comparing one to an aware datetime raises, and comparing two naive datetimes from different
      sources silently compares wrong. Use `datetime.now(UTC)` everywhere
- [ ] **Store UTC, render local.** Database columns are `timestamptz`, not `timestamp` —
      a `timestamp` column silently discards the offset and there is no way to recover it later
- [ ] **Durations from a monotonic clock**, not wall clock. An NTP correction mid-measurement can
      make an elapsed time negative, which then fails a `> 0` assumption somewhere unrelated
- [ ] **DST.** A job at 02:30 local runs twice on one day a year and not at all on another.
      Recurring schedules are UTC, or the double-run is explicitly safe (see
      `resilience-review.md` §1)
- [ ] **"Today" is a timezone question.** Daily aggregates, report boundaries, and "expires
      today" must state whose midnight. Mismatched boundaries are an off-by-hours error that
      only shows up in month-end numbers
- [ ] **Precision round-trips.** Python holds microseconds, JavaScript milliseconds, some columns
      seconds. A value that round-trips through all three is not the value you stored — never
      use a truncated timestamp as an equality key or a cursor
- [ ] **Clock skew between services.** Expiry checks (`exp`, cache TTLs, lock leases) need a
      tolerance, or a token minted by one host is already expired at the next

## 2. Numbers and money

*Trigger:* any currency, quantity, percentage, or aggregate.

- [ ] **Never a float for money.** `0.1 + 0.2 != 0.3`, and the error compounds over a ledger.
      `Decimal`, or integer minor units. The database column is `numeric`, never `float`/`real`
- [ ] **Rounding mode is stated** (half-up vs banker's) and **identical in code and in the
      database**. Two different modes on the same figure is a reconciliation bug that takes days
- [ ] **Column type bounds the real range.** `int4` tops out at 2.1 billion — fine for a row
      count, not for cents on a large total or a monotonic event ID
- [ ] **Division guards** — zero denominators, averages of empty collections
- [ ] **Round then sum ≠ sum then round.** Percentage splits that each round will not total 100;
      allocate the remainder deliberately
- [ ] **Units are typed or named.** `timeout=30` (seconds or milliseconds?), `amount` (which
      currency?), `size` (bytes or MB?). Put the unit in the name if not in the type

## 3. Ordering and pagination

*Trigger:* any list endpoint, cursor, batch iteration, or `ORDER BY`.

- [ ] **A unique tiebreaker on every sort used for pagination.** `ORDER BY created_at` with ties
      plus `LIMIT/OFFSET` returns some rows twice and skips others entirely, with no error. Add
      the primary key as the final sort term. This is the single most common silent data bug in
      list APIs
- [ ] **Keyset/cursor pagination when the set mutates during traversal** — offset pagination over
      a changing table shifts rows under the reader. It matters most in the place it is least
      tested: a background job paging through everything
- [ ] **No reliance on unspecified order.** Without `ORDER BY` there is no guarantee, whatever
      the current plan happens to return
- [ ] **Collation awareness** — string ordering and case-insensitive uniqueness depend on the
      column's collation, not on the application's locale

## 4. Text and encoding

*Trigger:* any user-supplied identifier, name, filename, search term, or comparison of text.

- [ ] **Unicode normalisation at the boundary** (NFC). Two byte-different spellings of the same
      name compare unequal, which means a uniqueness constraint can be bypassed and a lookup can
      miss a row that visibly exists
- [ ] **Case folding is locale-dependent** — `casefold()`, not `lower()`, and beware
      Turkish dotless ı in an identifier path
- [ ] **Length is ambiguous.** Bytes vs codepoints vs grapheme clusters: truncating to 280
      "characters" can split an emoji into invalid bytes, and a `varchar(n)` counts differently
      from `len()`
- [ ] **Encoding declared on every read and write** — no reliance on the platform default, which
      differs between your laptop and the container
- [ ] **Trim and reject control characters** in identifiers; a trailing space makes two accounts
      that look identical

## 5. Collections and absence

- [ ] **Empty is not missing.** `if not x` treats `0`, `""`, `[]`, and `None` alike — which is
      wrong wherever zero or empty is a legitimate value. Use `is None`
- [ ] **No mutable default arguments** (`def f(items=[])`) — shared across every call
- [ ] **No reliance on set/dict iteration order** for anything that affects output or hashing
- [ ] **Chunking covers the final partial chunk**, and behaves on an empty input
- [ ] **Boundaries tested at 0, 1, n, and n+1** — not just the middle

## 6. Configuration and startup

- [ ] **All configuration validated at startup**, loudly, before the process reports ready.
      Config read lazily on first use turns a typo into a 3am incident under load instead of a
      failed deploy at 2pm
- [ ] **New knob's default is the production-safe value.** Ask what happens if someone forgets
      to set it: a safe default, or a silent behaviour change?
- [ ] **Types coerced explicitly.** `bool(os.environ["DEBUG"])` is `True` for the string
      `"false"`. Every env var is a string until proven otherwise
- [ ] **Required vs optional is explicit**, and a missing required value fails startup rather
      than defaulting to something plausible
- [ ] **Effective config logged at boot** with secrets redacted (see `observability-review.md` §6)
- [ ] Externalisation, precedence, and per-environment layering are `/twelve-factor-standards`

## 7. Resource lifecycle

- [ ] **Every acquire has a guaranteed release** — context manager, `defer`, or `finally`.
      Check the **error** path specifically; the happy path is usually fine
- [ ] **No unbounded reads.** Loading an entire upload, query result, or response body into
      memory is fine until the day the input is large. Stream, or cap and reject
- [ ] **Connections and file handles released on exception**, including inside retry loops
- [ ] **Shutdown drains in-flight work** — see `resilience-review.md` §4

---

## Required output

State which sections applied, which you skipped, and the findings. For anything found, give the
`file:line` and the concrete failure — "`ORDER BY created_at` at `repo.py:41` duplicates rows
across pages when two orders share a timestamp", not "consider pagination stability".
