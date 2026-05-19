---
name: system-troubleshooting
description: Disciplined diagnostic workflow for code bugs, performance regressions, and infrastructure incidents. Covers application code debugging (reproduce → hypothesise → instrument → fix) and physical node/service health via Loki, InfluxDB, and Prometheus MCP services.
triggers:
  - "diagnose"
  - "debug"
  - "bug"
  - "something is broken"
  - "performance regression"
  - "node is down"
  - "node issues"
  - "service is unhealthy"
  - "high load"
  - "memory pressure"
  - "disk full"
  - "troubleshoot"
  - "what's wrong with"
  - "check metrics"
  - "check logs"
---

# system-troubleshooting

Disciplined diagnostic workflow for hard bugs and infrastructure incidents. Skip phases only when explicitly justified.

**Mode** — detect upfront whether this is a **code bug** (wrong/slow behaviour in application code) or an **infra incident** (node/service health). Both follow the same phase structure; infra-specific steps are marked `[INFRA]`.

---

## Pre-flight

**Code bugs:** identify the repo, the failing path, and what "correct" looks like. Check ADRs and domain glossary in the area you're touching.

**Infra incidents** `[INFRA]`: confirm MCP availability and establish a time window.

```
MCPs:
  loki       → log aggregation (LogQL)
  influxdb   → time-series metrics (Flux / InfluxQL)
  prometheus → scrape metrics (PromQL)
```

If an MCP is unavailable, fall back to [CLI Fallbacks](#cli-fallbacks).

Time window — start broad, narrow as evidence appears:
```
Last 15 min  →  acute incident, active failure
Last 1h      →  recent degradation
Last 6h      →  gradual trend (memory leak, slow disk fill)
Last 24h     →  daily pattern (cron job, traffic spike)
```

---

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a fast, deterministic, agent-runnable pass/fail signal, you will find the cause. Without one, no amount of staring at code or dashboards will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Code bugs — construct a loop (try in order)

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright/Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace** — save a real request/payload/event log to disk; replay in isolation.
6. **Throwaway harness** — minimal subset of the system, one function call, mocked deps.
7. **Property / fuzz loop** — if "sometimes wrong output", run 1000 random inputs, look for the failure mode.
8. **Bisection harness** — `git bisect run` if the bug appeared between two known states.
9. **Differential loop** — same input through old vs new version; diff outputs.
10. **HITL bash script** — last resort; if a human must click, drive them with a structured loop script.

Once you have a loop, sharpen it:
- **Faster** — cache setup, skip unrelated init, narrow test scope
- **Sharper signal** — assert on the specific symptom, not "didn't crash"
- **More deterministic** — pin time, seed RNG, isolate filesystem, freeze network

**Non-deterministic bugs:** aim for a higher reproduction rate, not a clean repro. Loop 100×, parallelise, inject sleeps. A 50%-flake is debuggable; 1% is not.

**If you genuinely cannot build a loop:** stop and say so. List what you tried. Ask for: (a) access to the reproducing environment, (b) a captured artifact (log dump, core dump, HAR file), or (c) permission to add temporary production instrumentation. Do NOT proceed without a loop.

### Infra incidents `[INFRA]` — establish the signal

Run the node vitals queries from [Node Vitals](#node-vitals) to confirm the symptom is real and measurable. This is your feedback loop — a concrete metric or log pattern you can re-query to verify improvement.

---

## Phase 2 — Reproduce

Run the loop. Watch the failure appear.

- [ ] The failure matches what the **user described** — not a nearby failure. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or at a high-enough rate for non-deterministic bugs).
- [ ] You have captured the exact symptom (error message, wrong output, metric value, slow timing) so later phases can verify the fix.

Do not proceed until reproduced.

---

## Phase 3 — Map dependencies

Before generating hypotheses, build a dependency map of the failing component. This prevents hypothesising about symptoms rather than causes, and reveals causal chains that span multiple components.

For each component in the failure path, identify:

**Upstream dependencies** — what does this component call or depend on?
- Code: modules, services, databases, caches, queues, external APIs
- Infra `[INFRA]`: other services on the node, shared storage, network paths, DNS, upstream load balancers

**Downstream dependents** — what calls or depends on this component?
- What breaks or degrades if this component is slow, wrong, or down?
- This defines the blast radius before you touch anything.

**Cause → effect for each dependency** — for every upstream, state what its failure would look like at the failing component:

```
Component: [failing thing]

Upstream:
  [dep A]  →  if A fails/degrades, this component shows [specific symptom]
  [dep B]  →  if B fails/degrades, this component shows [specific symptom]

Downstream:
  [dependent C]  ←  our failure appears there as [specific symptom]
  [dependent D]  ←  our failure appears there as [specific symptom]
```

**Key question:** Is the symptom you're seeing consistent with a failure in an upstream dependency? If yes, the root cause is likely higher in the chain — don't fix a downstream symptom when the upstream is broken.

**For infra** `[INFRA]`: check whether multiple services are failing simultaneously — shared upstream cause (same DB, same NFS mount, same network switch) is the most common explanation for correlated failures.

---

## Phase 4 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea. Use the dependency map from Phase 3 to ensure hypotheses target causes, not symptoms.

Each hypothesis must be **falsifiable** — state its prediction:

> "If **[X]** is the cause, then **[changing Y]** will make the problem disappear / **[doing Z]** will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly ("we just deployed a change to #3"). Don't block on a response — proceed with your ranking if AFK.

---

## Phase 5 — Instrument

Each probe must map to a specific prediction from Phase 4. **Change one variable at a time.**

### Code bugs

Tool preference:
1. **Debugger / REPL inspection** if the env supports it — one breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup later is a single grep. Untagged logs survive; tagged logs die.

**Performance regressions:** logs are usually wrong. Establish a baseline measurement first (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

### Infra incidents `[INFRA]`

When you see a metric spike, pivot to logs at the same timestamp:

```logql
{host="NODE"} | between <spike-start> and <spike-end>
```

Look for: OOM kills → check syslog for `oom_kill`; high CPU → top processes via `node_exporter`; disk fill → which service is writing at high rate.

See [Infra Query Reference](#infra-query-reference) for specific PromQL / LogQL / Flux queries.

---

## Phase 6 — Confirm root cause

**Do not apply a fix until you can state the root cause in one sentence.**

Format: *"The root cause is [specific thing] because [evidence from metrics/logs/code], not [ruled-out alternative]."*

Examples:
- ✅ "The root cause is a log-writing runaway in `worker` — Loki shows 50k lines/min from `app=worker` starting at 14:32, coinciding with the disk fill rate spike in InfluxDB."
- ✅ "The root cause is a memory leak, not undersized limits — InfluxDB shows `mem.used_percent` growing linearly at 2%/h for 18h before the OOM kill, within historical normal load."
- ✅ "The root cause is a nil pointer dereference in `parseResponse` because the error branch exits early without initialising the result struct, not a network timeout."
- ❌ "The node is running out of memory." (symptom, not cause)
- ❌ "Something is wrong with the service." (too vague)

**Root-cause checklist:**
- [ ] Evidence confirmed: I have a specific query output, log line, or code path that directly shows the cause.
- [ ] Timestamp correlated: metric anomaly and log anomaly (or code change and first failure) occur at the same time.
- [ ] Alternatives ruled out: I have checked and eliminated the next most likely cause.
- [ ] Blast radius known: one node/service/codepath or multiple?
- [ ] One-sentence root cause written above before applying any fix.

---

## Phase 7 — Fix

### Code bugs

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam exercises the real bug pattern at the call site. If the only available seam is too shallow (a unit test that can't replicate the chain that triggered the bug), a test there gives false confidence.

**If no correct seam exists, note it** — the architecture is preventing the bug from being locked down. Flag for an architectural review after the fix is in.

1. Turn the minimised repro into a failing test at the correct seam.
2. Watch it fail.
3. Apply the minimal fix.
4. Watch it pass.
5. Re-run the Phase 1 loop against the original (un-minimised) scenario.

### Infra incidents `[INFRA]`

See [Remediation Quick Reference](#remediation-quick-reference).

---

## Phase 8 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run Phase 1 loop or infra signal query)
- [ ] Regression test passes (or absence of a correct seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted or moved to a clearly-marked debug location
- [ ] The hypothesis that turned out correct is stated in the commit/PR message

**Then ask: what would have prevented this?** If the answer involves architecture (no good test seam, tangled callers, hidden coupling), raise it after the fix is in — you have more information now than when you started.

**Add this exemplar to the skill** (infra incidents especially):

```markdown
### Exemplar: <brief description> (<date>)
- **Symptom**: what was reported or alerted
- **Signal**: `<query or loop>` → `<key output>`
- **Alternatives ruled out**: what was checked and eliminated
- **Root cause**: "[specific thing] because [evidence], not [ruled-out]"
- **Fix**: what was changed
- **Prevention**: what would stop recurrence
```

---

## Infra Query Reference

### Label conventions

Different systems use different label names for the same concept. Verify before assuming.

**Node identity:**

| System     | Label key  | Example value        |
|------------|------------|----------------------|
| Loki       | `host`     | `n001.cluster.local` |
| Prometheus | `nodename` | `n001`               |
| Prometheus | `instance` | `n001:9100`          |
| InfluxDB   | `host`     | `n001`               |

Rule of thumb: Loki = `host=`, Prometheus node_exporter = `nodename=` or `instance=`, InfluxDB/Telegraf = `host=`. Always verify: `{job="node_exporter"} | label_names` or `SHOW TAG KEYS` before assuming.

**Service identity:**

| System     | Label key   | Example value   |
|------------|-------------|-----------------|
| Loki       | `app`       | `api`, `worker` |
| Loki       | `container` | `api`           |
| Prometheus | `job`       | `api`           |
| InfluxDB   | `service`   | `api`           |

---

### Node vitals

#### CPU

```promql
# Utilisation 5m avg
100 - (avg by (nodename) (rate(node_cpu_seconds_total{mode="idle", nodename="NODE"}[5m])) * 100)
```

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r.host == "NODE" and r._field == "usage_idle")
  |> map(fn: (r) => ({r with _value: 100.0 - r._value}))
  |> aggregateWindow(every: 1m, fn: mean)
```

#### Memory

```promql
100 * (1 - (node_memory_MemAvailable_bytes{nodename="NODE"} / node_memory_MemTotal_bytes{nodename="NODE"}))
```

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "mem" and r.host == "NODE" and r._field == "used_percent")
  |> aggregateWindow(every: 1m, fn: mean)
```

#### Disk

```promql
# Free % per mount
100 * (node_filesystem_avail_bytes{nodename="NODE", fstype!="tmpfs"} / node_filesystem_size_bytes{nodename="NODE", fstype!="tmpfs"})

# ETA to full (predict 24h ahead)
predict_linear(node_filesystem_avail_bytes{nodename="NODE"}[6h], 3600*24)
```

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "disk" and r.host == "NODE" and r._field == "used_percent")
```

#### Network

```promql
rate(node_network_receive_bytes_total{nodename="NODE", device!="lo"}[5m])
rate(node_network_transmit_bytes_total{nodename="NODE", device!="lo"}[5m])
rate(node_network_receive_errs_total{nodename="NODE"}[5m])
rate(node_network_receive_drop_total{nodename="NODE"}[5m])
```

#### Load average

```promql
# Load vs CPU count
node_load1{nodename="NODE"} / count by (nodename) (node_cpu_seconds_total{mode="idle", nodename="NODE"})
```

---

### Log triage (Loki)

```logql
# Kernel / OOM events
{host="NODE"} |~ "Out of memory|oom_kill|Killed process"

# Disk errors
{host="NODE"} |~ "I/O error|EXT4-fs error|blk_update_request|SCSI error"

# Service errors
{host="NODE", app="SERVICE"} |= "error" or "ERROR" or "FATAL" | last 50

# Structured JSON logs
{host="NODE", app="SERVICE"} | json | level="error" | last 50

# Log rate spike (anomaly detection)
sum by (app) (count_over_time({host="NODE"}[1m]))
```

---

### Service health

```promql
# Target up?
up{job="SERVICE", nodename="NODE"}

# HTTP 5xx rate
rate(http_requests_total{job="SERVICE", status=~"5.."}[5m]) / rate(http_requests_total{job="SERVICE"}[5m])

# Latency p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job="SERVICE"}[5m]))
```

---

### Exemplar scenarios

**A — High node load**
1. Check load vs CPU count (`node_load1`)
2. Check CPU mode breakdown — high `iowait` → disk bottleneck
3. Check memory pressure (`MemAvailable` trending down?)
4. Loki — OOM kills, process restarts at the same time window

**B — Service returning errors**
1. `up{job="SERVICE"}` = 0? → service is down
2. HTTP 5xx rate elevated?
3. Loki: `{app="SERVICE"} |= "error"` — what are the messages?
4. Loki: restart loop? `{app="SERVICE"} |= "started" or "Starting"` — frequency?

**C — Disk filling up**
1. Which mount? `node_filesystem_avail_bytes`
2. ETA: `predict_linear(...[6h], 3600*24)`
3. Chatty service? `sum(count_over_time({host="NODE"}[1m]))`
4. InfluxDB `disk.used_percent` trend over 24h

**D — Intermittent network issues**
1. `node_network_receive_errs_total`, `node_network_transmit_errs_total`
2. Packet drops: `node_network_receive_drop_total`
3. Loki: `{host="NODE"} |~ "connection refused|timeout|reset by peer"`

---

### CLI fallbacks

When MCP services are unavailable:

```bash
# CPU / memory / load
top -b -n1 | head -20
free -h && uptime

# Disk
df -h
iostat -x 1 5           # I/O wait, util%

# Network errors
ip -s link
netstat -s | grep -E "error|fail|drop"

# Kernel / OOM events
journalctl -k --since "1 hour ago" | grep -iE "oom|error|fail|killed"

# Service logs
journalctl -u SERVICE_NAME --since "1 hour ago" -n 200

# Top processes
ps aux --sort=-%cpu | head -15
ps aux --sort=-%mem | head -15

# File descriptor exhaustion
lsof | wc -l
```

---

### Remediation quick reference

| Symptom              | First action                                                   |
|----------------------|----------------------------------------------------------------|
| OOM kill             | `systemctl restart SERVICE` / increase memory limit           |
| Disk full            | `du -sh /* \| sort -rh \| head` — find large dirs; truncate logs |
| High I/O wait        | `iotop -o` — identify culprit; check for runaway log writing  |
| CPU runaway          | Restart service; `kill -9 PID` if truly runaway               |
| Service down (up=0)  | `systemctl status SERVICE`; check logs; restart               |
| Network errors       | Check NIC firmware/cable; `ip link set dev eth0 down/up`      |
| Load > 2× CPU count  | Check I/O wait first; identify blocking processes             |
