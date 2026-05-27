#### Pre-change baseline (run before applying anything)

Document the current healthy state so regressions are detectable:

```
Dependency health pre-check:
  All upstream dependencies confirmed healthy before applying:
  - Database:       ___  (healthy / degraded / unknown)
  - Cache:          ___
  - External APIs:  ___
  - Message queues: ___
  - Other services: ___
  If any dependency is degraded: STOP — do not deploy into a degraded environment.
  Deploying into degraded dependencies causes misattributed incidents.

Metric baseline snapshot (record immediately before applying):
  Error rate:    ___  (e.g. 0.03%)
  p95 latency:   ___  (e.g. 42ms)
  RPS:           ___  (e.g. 1200 req/s)
  Pod count:     ___  (e.g. 4 running / 4 desired)
  CPU usage:     ___  (e.g. 34% of request)
  Memory usage:  ___  (e.g. 61% of request)
  Recorded at:   ___  (timestamp + where stored: task file / runbook / CI artifact)

Baseline smoke test:
  Script:  ___  (must be a repeatable script, not a manual step)
  Asserts: ___  (e.g. HTTP 200 on /healthz, pod count N, secret present)
  Result recorded at: ___

Existing integration/E2E tests that must still pass after the change:
  - ___  (test suite name / script path)
  - ___
```

#### Post-change verification (run immediately after each slice applies)

For each delivery slice, define what must pass before the next slice begins:

```
Slice N — smoke test:
  Script:  ___
  Asserts: ___  (what does "working" look like for this slice specifically?)
  Timing:  run immediately after apply, before proceeding

Metric delta comparison (compare against baseline snapshot, not absolute thresholds):
  Error rate:    before ___ / after ___  — delta acceptable?  Y / N
  p95 latency:   before ___ / after ___  — delta acceptable?  Y / N
  RPS:           before ___ / after ___  — unexpected drop?   Y / N
  Pod count:     before ___ / after ___  — all desired pods running?  Y / N
  CPU usage:     before ___ / after ___  — unexpected spike?  Y / N
  Memory usage:  before ___ / after ___  — unexpected spike?  Y / N
  Rollback if: error rate delta > +1%, latency delta > 2×, RPS drops > 20%, or any
               metric change cannot be explained by the change itself.

End-to-end test (full user/system flow, not just health checks):
  Script/suite:  ___
  Covers:  ___  (which user-visible or system-level behaviours are exercised?)
  Must pass before: production promotion / next slice / flag enable

Integration tests (cross-service or cross-namespace correctness):
  Script/suite:  ___
  Covers:  ___  (which service interactions does this verify?)
  Must pass before: ___
```

#### Negative-path tests (things that should be blocked)

For changes involving NetworkPolicy, RBAC, auth, or access controls:

```
What should be blocked after this change?
  - ___  (e.g. pod in namespace X cannot reach namespace Y)
Negative test script:  ___  (verifies the block is in place)
```

#### Rollback verification

```
Rollback smoke test:
  After rolling back, what must pass to confirm the cluster is back to baseline?
  Script:  ___
  Asserts: ___
```

#### Test ownership and execution

```
Who runs the tests?        ___  (platform team / CI pipeline / both)
When are they run?         ___  (automated on every apply / manual gate / both)
Where are results stored?  ___  (CI artifact / task file / runbook)
What happens on failure?   ___  (block promotion / alert on-call / rollback immediately)
```
