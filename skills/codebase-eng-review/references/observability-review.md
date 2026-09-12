# Observability Review

Loaded at §6 of `/codebase-eng-review`. **Trigger:** always — every change adds a codepath that
can fail.

Cognitive pattern #5 is "design for tired humans at 3am". This file is where that becomes a
check. The test to apply throughout:

> A page fires at 03:00. You have logs, metrics, and traces — no debugger, no `kubectl exec`, no
> ability to reproduce. Can the on-call localise the fault to a component in ten minutes?

`/platform-ops-review` owns SLOs, alert routing, and dashboards at the cluster level.
`/twelve-factor-standards` owns logs-as-event-streams. This file is about the instrumentation
**inside the diff**.

---

## 1. Signal per codepath

Every new codepath from the §3 test diagram gets a row. A path with no failure signal is a path
that can be broken for a week without anyone knowing.

| Codepath | Success signal | Failure signal | Latency recorded | Anyone paged? |
|---|---|---|---|---|
| `POST /orders` | `orders_created_total` | `orders_failed_total{reason}` | histogram | yes — SLO burn |
| `orders.created` consumer | — ← gap | log only, no metric | no | no ← gap |

Reasonable outcomes include "logged only, deliberately — low value path". An unstated outcome is
a finding.

## 2. Error context

The question is not "is the error logged" but "can the on-call act on the log line alone".

Every error log or raised exception should carry: **what operation**, **which entity** (the ID,
not "a record"), **which upstream** if one was involved, and the **correlation ID**.

Anti-patterns to flag on sight:

```python
except Exception:                      # what failed? nothing to go on
    logger.error("failed")

except Exception:                      # silent — the worst outcome
    pass

except ValueError as e:
    raise ProcessingError("bad input") # cause discarded; use `from e`

logger.error(f"user {user} failed")    # __repr__ of an ORM object, or a PII leak
```

- [ ] Error messages name the operation and the identifier that failed
- [ ] Causes chained (`raise … from e`), stack trace preserved
- [ ] Structured fields, not values interpolated into a message string — a string cannot be
      filtered by tenant in the aggregator
- [ ] Log level is honest: `error` means someone should look; a retryable blip is `warning`.
      A path that logs `error` on every normal 404 trains the team to ignore errors
- [ ] No secrets or PII in the context — see `/security-review` §4.8. The two requirements
      conflict at exactly one point: the *identifier* is what the on-call needs; the *payload*
      is what leaks. Log IDs, not bodies

## 3. Correlation and causality

- [ ] A request/trace ID is generated at the edge if absent, and accepted from upstream if present
- [ ] It survives **async boundaries** — background tasks, thread pools, queue messages (carried
      in message headers/attributes), and scheduled jobs triggered by an earlier request. This is
      where correlation always breaks; check it explicitly rather than assuming the framework does it
- [ ] A queue consumer's spans link back to the producer's trace
- [ ] Tenant/user identifier on every log line in a multi-tenant system — without it you cannot
      answer "is this one customer or everyone?", which is the first question on every incident
- [ ] New spans cover the actual suspects: the external call, the slow query, the serialisation

## 4. Metric hygiene

- **Cardinality.** Never label a metric with a user ID, request ID, email, session, raw URL path
  containing IDs, error message, or anything else unbounded. One such label can multiply series
  into the millions and take down the metrics backend — which means losing observability exactly
  when an incident is in progress. Bound every label's value set and say what bounds it.
- **RED for each new endpoint or consumer** — rate, errors, duration. **USE for each new resource
  pool** — utilisation, saturation, errors. Saturation (queue depth, pool waiters) is the leading
  indicator; it is also the one most often missing.
- **Type chosen correctly:** counter for things that only go up (never a gauge — gauges lose
  events between scrapes), histogram for latency, gauge for current state. Histogram buckets must
  bracket the actual range: default buckets topping out at 10 s tell you nothing about a p99 of 40 s.
- **Aggregation-safe:** averages of averages are wrong. Percentiles must be computed from
  histograms, not averaged across instances.
- **Dead metrics.** For each new metric: which dashboard panel shows it, and does anything alert
  on it? A metric with no consumer is cost with no benefit — either wire it up or drop it.

## 5. Silent failure hunt

Cross-reference the failure-modes output in `SKILL.md`. Walk the change and list every path where
failure produces **no signal at all**:

- Swallowed or broadly-caught exceptions
- An empty result treated as success — zero rows returned because the filter was wrong looks
  exactly like zero rows because there is no data
- A background task or consumer that dies and is never restarted, or is restarted silently
- A retry loop that exhausts its budget and gives up without emitting anything
- A feature flag left off, a cron that stopped firing, a webhook whose signature check now fails
- A fallback path that has silently become the only path

For each, state which of the three it is: **would fire an alert**, **a log line nobody reads**,
or **nothing at all**. Anything in the third category with user-visible impact is a critical gap.

## 6. Debuggability affordances

- [ ] Verbose logging can be enabled for one tenant, user, or request **without a redeploy**
- [ ] The readiness endpoint reports dependency state, not just "process alive" — so the on-call
      can tell "my dependency is down" from "I am broken"
- [ ] Effective configuration is discoverable at runtime (logged at boot with secrets redacted) —
      "which value is this pod actually running?" should not require reading three Helm layers
- [ ] Version/build SHA is exposed in a response header or metric, so you can tell which code is
      actually serving traffic mid-rollout

---

## Required output

- The signal table from §1, with no blank cells
- The silent-failure list from §5, each classified alert / log / nothing
- For each new metric: its label set and what bounds the cardinality

**STOP.** One AskUserQuestion per gap. For silent failures with user-visible impact, recommend
the signal explicitly — which metric, which label, which alert condition.
