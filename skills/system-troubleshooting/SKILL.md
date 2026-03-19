---
name: system-troubleshooting
description: Physical node and service diagnostics using Loki (logs), InfluxDB (metrics/time-series), and Prometheus (scrape metrics) MCP services. Covers label conventions, exemplar queries, and a structured workflow for identifying and remediating node and service issues.
triggers:
  - "node is down"
  - "node issues"
  - "service is unhealthy"
  - "high load"
  - "memory pressure"
  - "disk full"
  - "troubleshoot node"
  - "diagnose"
  - "what's wrong with"
  - "check metrics"
  - "check logs"
---

# system-troubleshooting

Structured workflow for diagnosing physical node and service health using observability MCPs — **triage, correlate, then confirm root cause before remediating**.

## MCP Availability Check

At the start of any troubleshooting session, confirm which MCPs are available:

```
Available MCPs (check at session start):
  - loki      → log aggregation (LogQL queries)
  - influxdb  → time-series metrics (Flux / InfluxQL queries)
  - prometheus → scrape metrics (PromQL queries)
```

If an MCP is not connected, fall back to CLI equivalents (see [CLI Fallbacks](#cli-fallbacks)).

---

## Label Conventions

Different systems use different label names for the same concept. Always check which convention applies.

### Node identity

| System     | Label key    | Example value        | Notes                          |
|------------|--------------|----------------------|--------------------------------|
| Loki       | `host`       | `n001.cluster.local` | Set by Promtail / alloy agent  |
| Prometheus | `nodename`   | `n001`               | Set by node_exporter           |
| Prometheus | `instance`   | `n001:9100`          | `host:port` of the exporter    |
| InfluxDB   | `host`       | `n001`               | Tag set by Telegraf            |
| InfluxDB   | `nodename`   | `n001`               | Alternative tag (check schema) |

> **Rule of thumb:** Loki uses `host=`, Prometheus node_exporter uses `nodename=` or `instance=`, InfluxDB/Telegraf uses `host=`.
> Always verify: `{job="node_exporter"} | label_names` or `SHOW TAG KEYS` before assuming.

### Service identity

| System     | Label key  | Example value     |
|------------|------------|-------------------|
| Loki       | `app`      | `api`, `worker`   |
| Loki       | `container`| `api`             |
| Prometheus | `job`      | `api`             |
| Prometheus | `service`  | `api-svc`         |
| InfluxDB   | `service`  | `api`             |

---

## Troubleshooting Workflow

### Step 1 — Establish the time window

Always bound queries to a relevant window. Start broad (last 1h) then narrow.

```
Last 15 min  →  acute incident, active failure
Last 1h      →  recent degradation
Last 6h      →  gradual trend (memory leak, slow disk fill)
Last 24h     →  daily pattern (cron job, traffic spike)
```

### Step 2 — Node vitals (Prometheus / InfluxDB)

#### CPU

```promql
# Prometheus — node CPU utilisation (5m avg)
100 - (avg by (nodename) (rate(node_cpu_seconds_total{mode="idle", nodename="NODE"}[5m])) * 100)

# Or using instance label
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle", instance=~"NODE.*"}[5m])) * 100)
```

```flux
// InfluxDB (Flux) — CPU usage %
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r.host == "NODE" and r._field == "usage_idle")
  |> map(fn: (r) => ({r with _value: 100.0 - r._value}))
  |> aggregateWindow(every: 1m, fn: mean)
```

#### Memory

```promql
# Prometheus — memory used %
100 * (1 - (node_memory_MemAvailable_bytes{nodename="NODE"} / node_memory_MemTotal_bytes{nodename="NODE"}))
```

```flux
// InfluxDB — memory used bytes
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "mem" and r.host == "NODE" and r._field == "used_percent")
  |> aggregateWindow(every: 1m, fn: mean)
```

#### Disk

```promql
# Prometheus — disk free % per mount
100 * (node_filesystem_avail_bytes{nodename="NODE", fstype!="tmpfs"} / node_filesystem_size_bytes{nodename="NODE", fstype!="tmpfs"})
```

```flux
// InfluxDB — disk usage %
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "disk" and r.host == "NODE" and r._field == "used_percent")
```

#### Network

```promql
# Prometheus — receive/transmit bytes/sec
rate(node_network_receive_bytes_total{nodename="NODE", device!="lo"}[5m])
rate(node_network_transmit_bytes_total{nodename="NODE", device!="lo"}[5m])
```

#### Load average

```promql
# Prometheus — 1m load vs CPU count
node_load1{nodename="NODE"} / count by (nodename) (node_cpu_seconds_total{mode="idle", nodename="NODE"})
```

---

### Step 3 — Log triage (Loki)

#### Kernel / system errors

```logql
# Recent errors from syslog / journal
{host="NODE", job="syslog"} |= "error" or "Error" or "OOM" or "killed" | last 50

# OOM killer events
{host="NODE"} |~ "Out of memory|oom_kill|Killed process"

# Disk errors
{host="NODE"} |~ "I/O error|EXT4-fs error|blk_update_request|SCSI error"
```

#### Service logs

```logql
# Tail a specific service
{host="NODE", app="SERVICE"} | last 100

# Errors only
{host="NODE", app="SERVICE"} |= "error" or "ERROR" or "FATAL" | last 50

# Structured log — JSON error field
{host="NODE", app="SERVICE"} | json | level="error" | last 50
```

#### Log rate spike (anomaly detection)

```logql
# Count log lines per minute — spike = incident marker
sum by (app) (count_over_time({host="NODE"}[1m]))
```

---

### Step 4 — Correlate metrics + logs

When you see a CPU/memory spike in metrics, pivot to logs at the same timestamp:

```logql
# Logs at spike time (replace timestamps)
{host="NODE"} | ... | between 2026-01-15T14:30:00Z and 2026-01-15T14:35:00Z
```

Look for:
- OOM kills → check `dmesg` equivalent in syslog
- High CPU → check which process (`node_exporter` top processes if available)
- Disk fill → check which mount, which service writing logs

---

### Step 4.5 — Confirm root cause before remediating

**Do not apply a fix until you can state the root cause in one sentence.**

The format: _"The root cause is [specific thing] because [evidence from metrics/logs], not [ruled-out alternative]."_

Examples:
- ✅ "The root cause is a log-writing runaway in the `worker` service — Loki shows 50k lines/min from `app=worker` starting at 14:32, coinciding with the disk fill rate spike in InfluxDB."
- ✅ "The root cause is a memory leak, not undersized limits — InfluxDB shows `mem.used_percent` growing linearly at 2%/h for 18h before the OOM kill, well within historical normal load."
- ❌ "The node is running out of memory." (symptom, not cause)
- ❌ "Something is wrong with the service." (too vague)

**Root-cause checklist — before fixing:**

- [ ] **Evidence confirmed:** I have a specific query output or log line that directly shows the cause.
- [ ] **Timestamp correlated:** the metric anomaly and log anomaly occur at the same time.
- [ ] **Alternatives ruled out:** I have checked and eliminated the next most likely cause.
- [ ] **Blast radius known:** is this one node/service or multiple?
- [ ] **One-sentence root cause written:** stated above before applying any fix.

---

### Step 5 — Service health check

```promql
# Prometheus — is the target up?
up{job="SERVICE", nodename="NODE"}

# HTTP error rate
rate(http_requests_total{job="SERVICE", status=~"5.."}[5m]) / rate(http_requests_total{job="SERVICE"}[5m])

# Latency p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job="SERVICE"}[5m]))
```

```flux
// InfluxDB — service metric
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "SERVICE_metric" and r.host == "NODE")
```

---

## Exemplar Scenarios

### Scenario A — Node reporting high load

1. **Check load vs CPU count** (Prometheus `node_load1`)
2. **Identify busy CPUs** — `node_cpu_seconds_total` broken by `mode`
3. **Check memory pressure** — `MemAvailable` trending down?
4. **Check disk I/O wait** — `node_cpu_seconds_total{mode="iowait"}` high → disk bottleneck
5. **Loki** — search for OOM kills, process restarts, application errors at the same time window

### Scenario B — Service returning errors

1. **Prometheus** — `up{job="SERVICE"}` = 0? → exporter/service is down
2. **Prometheus** — HTTP 5xx rate elevated?
3. **Loki** — `{app="SERVICE", host="NODE"} |= "error"` — what are the error messages?
4. **Loki** — check for restart loops: `{app="SERVICE"} |= "started" or "Starting"` — frequency?
5. **InfluxDB** — any custom application metrics showing queue depth, DB latency, etc.?

### Scenario C — Disk filling up

1. **Prometheus** — `node_filesystem_avail_bytes` — which mount is filling?
2. **Prometheus** — rate of fill: `predict_linear(node_filesystem_avail_bytes[6h], 3600*24)` → ETA
3. **Loki** — high log write rate? `sum(count_over_time({host="NODE"}[1m]))` — chatty service?
4. **InfluxDB** — `disk` measurement, `used_percent` trend over 24h

### Scenario D — Intermittent network issues

1. **Prometheus** — `node_network_receive_errs_total`, `node_network_transmit_errs_total`
2. **Prometheus** — packet drops: `node_network_receive_drop_total`
3. **Loki** — `{host="NODE"} |~ "connection refused|timeout|reset by peer"`
4. **InfluxDB** — `net` measurement, `err_in` / `err_out` tags

---

## CLI Fallbacks

When MCP services are unavailable, use these equivalent commands on the node:

```bash
# CPU / memory / load
top -b -n1 | head -20
free -h
uptime

# Disk
df -h
iostat -x 1 5          # I/O wait, util%

# Network errors
ip -s link
netstat -s | grep -E "error|fail|drop"

# Kernel / OOM events (last hour)
journalctl -k --since "1 hour ago" | grep -iE "oom|error|fail|killed"

# Service logs
journalctl -u SERVICE_NAME --since "1 hour ago" -n 200

# Top processes by CPU
ps aux --sort=-%cpu | head -15

# Top processes by memory
ps aux --sort=-%mem | head -15

# Open files / fd exhaustion
lsof | wc -l
cat /proc/sys/fs/file-nr
```

---

## Remediation Quick Reference

| Symptom                  | First action                                  |
|--------------------------|-----------------------------------------------|
| OOM kill                 | `systemctl restart SERVICE` / increase memory limit |
| Disk full                | Find large files: `du -sh /* | sort -rh | head`; truncate logs |
| High I/O wait            | Identify culprit: `iotop -o`; check for runaway logging |
| CPU runaway              | `kill -9 PID` if runaway; or restart service  |
| Service down (`up=0`)    | `systemctl status SERVICE`; check logs; restart |
| Network errors           | Check NIC firmware, cable; `ip link set dev eth0 down/up` |
| Load > 2× CPU count      | Identify blocking processes; check disk I/O wait first |

---

## Updating This Skill with Exemplars

When you successfully diagnose an issue, add the query pattern to this skill:

```markdown
### Exemplar: <brief description> (<date>)
- **Symptom**: what was reported or alerted
- **Signal found**: `<query>` on `<system>` → `<key output>`
- **Alternatives ruled out**: what else was checked and eliminated
- **Root cause**: one sentence — "[specific thing] because [evidence], not [ruled-out alternative]"
- **Fix**: what was changed
- **Recurrence prevention**: what would prevent this happening again
```

This builds a local playbook tuned to the actual label schema and service names in this environment.
