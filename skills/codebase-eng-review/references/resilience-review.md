# Resilience and Idempotency Review

Loaded at §5 of `/codebase-eng-review`. **Trigger:** the change adds or modifies any outbound
network call, queue consumer, webhook handler, scheduled job, retry, or mutation that a client
can submit more than once. If none apply, state "no new delivery or failure surface" and skip.

`/codebase-arch-review` §3 asks *what happens when a dependency is down* at the architecture
level. This file checks that the **implementation** actually handles it — the timeout is set, the
retry is bounded, the handler survives a redelivery. `/security-review` owns TOCTOU as an attack;
this is the correctness view of the same shape.

---

## 1. Idempotency — "is it safe to run twice?"

This is the single highest-yield question in the review. Ask it of **every new mutating
codepath** and record the answer. "It shouldn't happen twice" is not an answer.

Enumerate how many times each path can actually execute:

| Delivery mechanism | Runs more than once when | Typical damage |
|---|---|---|
| Client HTTP retry / double-click / refresh | Network blips, impatient user, mobile reconnect | Duplicate order, double charge |
| Queue or stream consumer | At-least-once delivery, visibility timeout expiry, consumer restart mid-ack | Duplicate side effect per redelivery |
| Scheduled job / cron | Overlapping runs, missed-run catch-up, DST double hour | Two workers on the same rows |
| Kubernetes Job / pod restart | OOM kill, node drain, liveness restart mid-work | Partial work re-run from the start |
| Webhook from a third party | Provider retries until 2xx; many retry on timeout even after success | Same event applied N times |
| CI / GitOps re-apply | Re-run of the same pipeline or reconcile loop | Re-execution of a one-shot step |

For each mutating path, answer:

- **Is the operation naturally idempotent?** Assignment is (`status = 'paid'`); accumulation is
  not (`balance += x`, `append`, `INSERT` without a constraint, counter increments, emails sent).
- **If not, what is the idempotency key?** Where does it come from — client-supplied header,
  derived from the payload, or the upstream event ID? A key derived from a timestamp or a UUID
  generated inside the handler is not a key.
- **How long is the key retained**, and what happens on a repeat: return the original result, or
  error? Returning an error to a legitimate retry is its own bug.
- **Is the key checked atomically with the write** (unique constraint, conditional update), or
  is there a window between "have I seen this?" and the insert? See §6.
- **Partial idempotency trap:** a handler doing three things where two are idempotent and one is
  not (write row, update cache, send email) is **not** idempotent. Name which step breaks.

## 2. Timeouts and deadlines

**Most clients default to no timeout.** `requests.get(url)`, `httpx` without `timeout=`, a bare
`fetch()`, a DB driver with no `statement_timeout`, a `subprocess.run` with no `timeout` — each
one can hang until the process is restarted, holding a worker and a connection the whole time.
A hung worker pool is indistinguishable from an outage and much harder to diagnose.

- [ ] Every new outbound call has an **explicit** timeout, with the number stated in the plan
- [ ] Connect timeout and read timeout are set separately where the library allows it
- [ ] Long-running DB statements have a server-side `statement_timeout` / query timeout too —
      a client timeout abandons the request but the database keeps working
- [ ] The overall request has a budget, not just each hop

**Deadline propagation.** If the inbound request has a 30 s budget, the sum of the downstream
timeouts must fit inside it. Otherwise the caller gives up while your handler keeps burning
resources on a result nobody will read.

```
inbound 30s
  ├─ auth service      2s   ✓
  ├─ database          5s   ✓
  └─ pricing service  10s × 3 retries = 30s   ✗ exceeds the budget alone
```

State the arithmetic. Flag any chain where downstream timeouts × attempts ≥ the inbound timeout.

## 3. Retries

- [ ] **Only idempotent operations are retried** — or the retry carries an idempotency key (§1)
- [ ] **Exponential backoff with full jitter**, not a fixed `sleep(1)`. Fixed backoff
      synchronises every client into a thundering herd against a recovering dependency
- [ ] **Bounded** by both max attempts *and* a total elapsed budget
- [ ] **Only retryable errors retried** — timeout, connection reset, 429, 5xx. Never a 4xx,
      never a validation or auth error, never a deserialisation failure. Retrying a
      deterministic failure just multiplies the load
- [ ] `Retry-After` honoured when the response provides it

**Retry amplification.** Retries multiply through layers. Three tiers each retrying three times
is up to 27 calls at the bottom for one user request — the dependency that was merely slow is now
down, and the retries keep it down. Count the layers in this change and state the multiplier.
Retry at one layer, preferably the outermost that can still act on the failure.

## 4. Degradation, shedding, and blast containment

- **Fail fast vs queue:** when a dependency is down, is failing immediately better than piling
  up work? A circuit breaker is worth its complexity only where retrying is actively harmful.
- **Bulkheads:** does one slow dependency exhaust the shared worker/connection pool and take the
  rest of the service with it? Separate pools or concurrency caps per dependency.
- **Bounded queues and backpressure:** any unbounded in-memory queue is an OOM waiting for a
  traffic spike. What happens when it is full — shed, block, or spill?
- **Graceful degradation:** which features can be served in reduced form when this dependency is
  unavailable (stale cache, omitted section, default value)? Is the degraded state **visible in
  telemetry**, or does the system quietly serve worse results forever? A fallback nobody can see
  firing is how a two-week outage becomes a surprise.
- **Shutdown:** on `SIGTERM`, is in-flight work drained and the readiness probe failed *before*
  the listener closes? Killed mid-write is where partial state comes from.

## 5. Partial failure

For every new multi-step operation, state what is left behind when step *k* of *n* fails:

```
create order  ✓   →   charge card  ✓   →   queue fulfilment  ✗
                                            └─ customer charged, nothing ships, no alert
```

- Which steps are in the same transaction, and which are not? A transaction spanning an HTTP
  call is a transaction held open for the duration of someone else's outage.
- **Dual-write smell:** writing to the database and then publishing an event, without a
  transactional outbox or CDC. The two will diverge — it is a question of when, not whether.
- Is there a compensating action (refund, cancel, tombstone), or a reconciliation job that
  detects the orphan? "We'd notice" is not a mechanism.
- Orphan shapes to look for specifically: uploaded object with no DB row, DB row pointing at a
  missing object, external resource created with the local record rolled back.

## 6. Concurrency correctness

- **Check-then-act on shared state** must be enforced by the datastore, not by two application
  statements: a unique constraint, `SELECT … FOR UPDATE`, an atomic `UPDATE … WHERE version = $n`,
  or a conditional write. Flag any `if not exists: create` and any read-modify-write.
- **Lost update:** two concurrent readers of the same row both writing back their whole object —
  the second silently discards the first's change. Optimistic locking or column-scoped updates.
- **Distributed locks:** is the lease longer than the worst-case work time? If not, two holders
  run simultaneously and neither knows. Is the lock **fenced** (a token the write path checks),
  or does an expired holder still get to write?
- **Async-specific:** unawaited coroutines, fire-and-forget tasks that swallow exceptions, a
  task holding a reference nobody keeps (garbage-collected mid-flight), mutable state read across
  an `await` point, a blocking call on the event loop.
- **Cron overlap:** can run *N+1* start before *N* finishes? Either a lock or a guarantee it
  cannot matter.

## 7. Rollout containment

`references/migration-checklist.md` covers flags for migrations. Every other new codepath needs
an answer to the same question: **when this misbehaves in production, how do we stop it without
a deploy?**

- [ ] A kill switch or flag exists for any new codepath that writes data, calls a paid API, sends
      a message, or changes what users see — or the plan states why a revert is fast enough
- [ ] The flag's **off** state is the old behaviour, and that path is tested (see
      `test-adequacy-rubric.md` §6 — the flag-off path is a systematically untested branch)
- [ ] Flag evaluation cannot itself fail open into the new behaviour — a flag service timeout
      must fall back to the safe side
- [ ] **Flag debt:** a removal ticket exists with an owner. A flag that outlives its rollout is
      permanent branching complexity and a permanent untested path

---

## Required output

One row per new mutating or outbound codepath. An empty cell is a finding.

| Codepath | Max executions | Idempotent? | Key | Timeout | Retry policy | State if it fails midway |
|---|---|---|---|---|---|---|
| `POST /orders` | client retry ×N | no | `Idempotency-Key` header | 5 s | none | order row, no charge |

**STOP.** One AskUserQuestion per gap, never batched. For each, state the concrete failure —
"a queue redelivery double-charges at `billing.py:88`" — not "consider idempotency".
