# Infrastructure & System Diagnostics Reference

Covers physical node and service health using Loki (logs), InfluxDB (metrics), and Prometheus (scrape metrics).

## Pre-flight

Confirm MCP availability at session start:

```
MCPs:
  loki       → log aggregation (LogQL)
  influxdb   → time-series metrics (Flux / InfluxQL)
  prometheus → scrape metrics (PromQL)
```

If an MCP is unavailable, fall back to [CLI Fallbacks](#cli-fallbacks).

**Time window** — start broad, narrow as evidence appears:
```
Last 15 min  →  acute incident, active failure
Last 1h      →  recent degradation
Last 6h      →  gradual trend (memory leak, slow disk fill)
Last 24h     →  daily pattern (cron job, traffic spike)
```

---

## Label conventions

Different systems use different label names for the same concept. Verify before assuming.

**Node identity:**

| System     | Label key  | Example value        |
|------------|------------|----------------------|
| Loki       | `host`     | `n001.cluster.local` |
| Prometheus | `nodename` | `n001`               |
| Prometheus | `instance` | `n001:9100`          |
| InfluxDB   | `host`     | `n001`               |

Rule: Loki = `host=`, Prometheus node_exporter = `nodename=` or `instance=`, InfluxDB/Telegraf = `host=`. Always verify: `{job="node_exporter"} | label_names` or `SHOW TAG KEYS`.

**Service identity:**

| System     | Label key   | Example value   |
|------------|-------------|-----------------|
| Loki       | `app`       | `api`, `worker` |
| Loki       | `container` | `api`           |
| Prometheus | `job`       | `api`           |
| InfluxDB   | `service`   | `api`           |

---

## Node vitals

### CPU

```promql
100 - (avg by (nodename) (rate(node_cpu_seconds_total{mode="idle", nodename="NODE"}[5m])) * 100)
```

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r.host == "NODE" and r._field == "usage_idle")
  |> map(fn: (r) => ({r with _value: 100.0 - r._value}))
  |> aggregateWindow(every: 1m, fn: mean)
```

### Memory

```promql
100 * (1 - (node_memory_MemAvailable_bytes{nodename="NODE"} / node_memory_MemTotal_bytes{nodename="NODE"}))
```

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "mem" and r.host == "NODE" and r._field == "used_percent")
  |> aggregateWindow(every: 1m, fn: mean)
```

### Disk

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

### Network

```promql
rate(node_network_receive_bytes_total{nodename="NODE", device!="lo"}[5m])
rate(node_network_transmit_bytes_total{nodename="NODE", device!="lo"}[5m])
rate(node_network_receive_errs_total{nodename="NODE"}[5m])
rate(node_network_receive_drop_total{nodename="NODE"}[5m])
```

### Load average

```promql
node_load1{nodename="NODE"} / count by (nodename) (node_cpu_seconds_total{mode="idle", nodename="NODE"})
```

---

## Correlate

When you see a metric spike, pivot to logs at the same timestamp:

```logql
{host="NODE"} | between <spike-start> and <spike-end>
```

Look for: OOM kills → check syslog for `oom_kill`; high CPU → top processes via `node_exporter`; disk fill → which service is writing at high rate.

---

## Log triage (Loki)

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

## Service health

```promql
# Target up?
up{job="SERVICE", nodename="NODE"}

# HTTP 5xx rate
rate(http_requests_total{job="SERVICE", status=~"5.."}[5m]) / rate(http_requests_total{job="SERVICE"}[5m])

# Latency p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job="SERVICE"}[5m]))
```

---

## Exemplar scenarios

**A — High node load**
1. Check load vs CPU count (`node_load1`)
2. CPU mode breakdown — high `iowait` → disk bottleneck
3. Memory pressure — `MemAvailable` trending down?
4. Loki — OOM kills, process restarts at the same time window

**B — Service returning errors**
1. `up{job="SERVICE"}` = 0? → service is down
2. HTTP 5xx rate elevated?
3. Loki: `{app="SERVICE"} |= "error"` — what are the messages?
4. Loki: restart loop? `{app="SERVICE"} |= "started" or "Starting"` — how frequent?

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

## CLI fallbacks

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

## Remediation

| Symptom              | First action                                                      |
|----------------------|-------------------------------------------------------------------|
| OOM kill             | `systemctl restart SERVICE` / increase memory limit              |
| Disk full            | `du -sh /* \| sort -rh \| head` — find large dirs; truncate logs |
| High I/O wait        | `iotop -o` — identify culprit; check for runaway log writing     |
| CPU runaway          | Restart service; `kill -9 PID` if truly runaway                  |
| Service down (up=0)  | `systemctl status SERVICE`; check logs; restart                  |
| Network errors       | Check NIC firmware/cable; `ip link set dev eth0 down/up`         |
| Load > 2× CPU count  | Check I/O wait first; identify blocking processes                |

---

## Exemplars

<!-- Add exemplars here as you diagnose issues -->
