# Code Bug & Performance Regression Reference

## Feedback loops

**Try in order — stop at the first one that works:**

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright/Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace** — save a real request/payload/event log to disk; replay in isolation.
6. **Throwaway harness** — minimal subset of the system, one function call, mocked deps.
7. **Property / fuzz loop** — if "sometimes wrong output", run 1000 random inputs, look for the failure mode.
8. **Bisection harness** — `git bisect run` if the bug appeared between two known states (commit, dataset, version).
9. **Differential loop** — same input through old vs new version (or two configs); diff outputs.
10. **HITL bash script** — last resort; if a human must click, drive them with a structured loop script so output feeds back into the session.

### Sharpen the loop

Once you have *a* loop, treat it as a product:
- **Faster** — cache setup, skip unrelated init, narrow test scope
- **Sharper signal** — assert on the specific symptom, not "didn't crash"
- **More deterministic** — pin time, seed RNG, isolate filesystem, freeze network

A 30-second flaky loop is barely better than no loop. A 2-second deterministic loop is a debugging superpower.

### Non-deterministic bugs

Don't aim for a clean repro — aim for a higher reproduction rate. Loop 100×, parallelise, add stress, inject sleeps, narrow timing windows. A 50%-flake is debuggable; 1% is not — keep raising the rate until it is.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for:
- (a) Access to whatever environment reproduces it
- (b) A captured artifact — HAR file, log dump, core dump, screen recording with timestamps
- (c) Permission to add temporary production instrumentation

Do NOT proceed to hypothesise without a loop.

---

## Instrumentation

Each probe must map to a specific prediction from Phase 4. **Change one variable at a time.**

Tool preference:
1. **Debugger / REPL inspection** if the env supports it — one breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end is a single grep. Untagged logs survive; tagged logs die.

### Performance regressions

Logs are usually the wrong tool. Instead:
1. Establish a baseline measurement first — timing harness, `performance.now()`, profiler, query plan
2. Bisect from there

Measure first, fix second. Never optimise a path you haven't measured.

---

## Fix

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the real bug pattern at the call site. If the only available seam is too shallow (a unit test that can't replicate the chain that triggered the bug), a test there gives false confidence.

**If no correct seam exists, note it** — the architecture is preventing the bug from being locked down. Flag for an architectural review after the fix is in, not before — you have more information now.

If a seam exists:
1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the minimal fix.
4. Watch it pass.
5. Re-run the Phase 1 loop against the original (un-minimised) scenario.

---

## Exemplars

<!-- Add exemplars here as you diagnose issues -->
