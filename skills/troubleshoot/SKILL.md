---
name: troubleshoot
description: Disciplined diagnostic workflow for code bugs, performance regressions, Kubernetes issues, and infrastructure incidents. Reproduce → map dependencies → hypothesise → instrument → confirm → fix → post-mortem. Domain-specific commands in references/.
triggers:
  - "diagnose"
  - "debug"
  - "bug"
  - "something is broken"
  - "performance regression"
  - "troubleshoot"
  - "what's wrong with"
  - "node is down"
  - "service is unhealthy"
  - "high load"
  - "memory pressure"
  - "disk full"
  - "check metrics"
  - "check logs"
  - "pod is crashing"
  - "pod crashloop"
  - "pod not starting"
  - "pod pending"
  - "pod evicted"
  - "service not reachable"
  - "ingress not working"
  - "can't connect to database"
  - "pvc not bound"
  - "storage issue"
  - "network policy"
  - "cilium"
  - "troubleshoot kubernetes"
  - "troubleshoot k8s"
  - "k8s issue"
  - "deployment failing"
  - "OOMKilled"
  - "imagepullbackoff"
  - "diagnose cluster"
---

# troubleshooting

Disciplined diagnostic workflow for hard bugs and infrastructure incidents. Skip phases only when explicitly justified.

## Mode detection

Identify which domain applies — more than one can be active simultaneously:

| Mode | Indicators | Reference |
|------|-----------|-----------|
| **Code bug** | Wrong output, exception, test failing, regression | `references/code.md` |
| **Infra** | Node/service health, Loki/Prometheus/InfluxDB signals | `references/infra.md` |
| **Kubernetes** | Pod/Deployment/Service/Ingress/PVC issues | `references/k8s.md` |

Load the relevant reference file(s) now, then follow the shared workflow below.

---

## Pre-flight

**Code:** identify the failing path and what "correct" looks like. Check ADRs and domain glossary in the area you're touching.

**Infra:** confirm MCP availability (Loki, InfluxDB, Prometheus) and establish a time window. See `references/infra.md → Pre-flight`.

**Kubernetes:** check for `.claude/skills/k8s-access/SKILL.md` in the project and apply any env var / KUBECONFIG instructions before running kubectl. Confirm cluster context. See `references/k8s.md → Phase 0`.

---

## Phase 1 — Build a feedback loop

**This is the skill.** Without a fast, deterministic, agent-runnable pass/fail signal, no amount of reading code or dashboards will find the cause.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

- **Code:** construct a loop using one of 10 techniques — see `references/code.md → Feedback loops`. Once you have a loop, sharpen it: faster, sharper signal, more deterministic.
- **Infra:** run node vitals queries to confirm the symptom is measurable — see `references/infra.md → Node vitals`. That metric or log pattern is your feedback loop.
- **Kubernetes:** run the architecture scan to understand the data path before looking at anything else — see `references/k8s.md → Phase 1`. Use the 7-layer traffic path as your dependency map.

**Non-deterministic bugs:** aim for a higher reproduction rate, not a clean repro. Loop 100×, parallelise, inject sleeps. A 50%-flake is debuggable; 1% is not.

**If you genuinely cannot build a loop:** stop and say so. List what you tried. Ask for: (a) access to the reproducing environment, (b) a captured artifact (log dump, core dump, HAR file), or (c) permission to add temporary production instrumentation. Do NOT proceed without a loop.

---

## Phase 2 — Reproduce

Run the loop. Watch the failure appear.

- [ ] The failure matches what the **user described** — not a nearby failure. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or at a high-enough rate for non-deterministic bugs).
- [ ] You have captured the exact symptom (error message, wrong output, metric value, timing) so later phases can verify the fix.

Do not proceed until reproduced.

---

## Phase 3 — Map dependencies

Before hypothesising, build a dependency map of the failing component. This prevents hypothesising about symptoms rather than causes, and reveals causal chains that span multiple components.

**Upstream dependencies** — what does this component call or depend on?
- Code: modules, services, databases, caches, queues, external APIs
- Infra: shared storage, network paths, DNS, upstream load balancers
- Kubernetes: upstream services, PVCs, ConfigMaps/Secrets, init containers, the full 7-layer traffic path

**Downstream dependents** — what calls or depends on this component?
- What breaks or degrades if this component fails?
- This defines blast radius before you touch anything.

**Cause → effect for each dependency:**

```
Component: [failing thing]

Upstream:
  [dep A]  →  if A fails/degrades, this component shows [specific symptom]
  [dep B]  →  if B fails/degrades, this component shows [specific symptom]

Downstream:
  [dependent C]  ←  our failure appears there as [specific symptom]
  [dependent D]  ←  our failure appears there as [specific symptom]
```

**Key question:** Is the symptom consistent with a failure in an upstream dependency? If yes, the root cause is higher in the chain — don't fix a downstream symptom when the upstream is broken.

**Multiple simultaneous failures** (infra/k8s) → look for a shared upstream cause first: same node, same DB, same network switch, same StorageClass provisioner.

---

## Phase 4 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any. Use the dependency map from Phase 3 to ensure hypotheses target causes, not symptoms.

Each hypothesis must be **falsifiable**:
> "If **[X]** is the cause, then **[changing Y]** will make the problem disappear / **[doing Z]** will make it worse."

If you cannot state the prediction, it's a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often re-rank instantly. Don't block — proceed with your ranking if AFK.

**Kubernetes:** check the root-cause traps table in `references/k8s.md → Root-cause traps` before finalising your hypotheses.

---

## Phase 5 — Instrument

Each probe must map to a specific prediction from Phase 4. **Change one variable at a time.**

- **Code:** debugger/REPL first (one breakpoint beats ten logs); targeted logs at hypothesis boundaries; tag every debug log `[DEBUG-a4f2]` for easy cleanup; for perf regressions, establish a baseline measurement before changing anything. See `references/code.md → Instrumentation`.
- **Infra:** correlate metrics and logs at the same timestamp — metric spike → pivot to logs in that window. See `references/infra.md → Correlate`.
- **Kubernetes:** drill from architecture → pod-level → storage → network in order. See `references/k8s.md → Phase 2–5`.

Never "log everything and grep".

---

## Phase 6 — Confirm root cause

**Do not apply a fix until you can state the root cause in one sentence.**

Format: *"The root cause is [specific thing] because [evidence], not [ruled-out alternative]."*

- ✅ "The root cause is a label selector mismatch on the `api` Service — the Service selects `app=api` but pods are labelled `app=api-v2`, confirmed by empty Endpoints."
- ✅ "The root cause is a log-writing runaway in `worker` — Loki shows 50k lines/min from `app=worker` starting at 14:32, coinciding with the disk fill spike in InfluxDB."
- ✅ "The root cause is a nil pointer in `parseResponse` because the error branch exits without initialising the result struct, not a network timeout."
- ❌ "The pod is crashing." / "The node is running out of memory." (symptoms, not causes)

**Root-cause checklist:**
- [ ] Evidence confirmed: a specific command output, log line, or code path directly shows the cause.
- [ ] Timestamp correlated: anomaly in metrics/logs/behaviour coincides in time.
- [ ] Alternatives ruled out: the next most likely cause has been checked and eliminated.
- [ ] Blast radius known: isolated to one component or affecting multiple?
- [ ] One-sentence root cause written above before applying any fix.

---

## Phase 7 — Fix

**Code:** write the regression test before the fix, but only at a correct seam. See `references/code.md → Fix`.

**Infra:** see `references/infra.md → Remediation`.

**Kubernetes:** see `references/k8s.md → Emergency rollback` and remediation steps in Phases 2–5.

For code fixes:
1. Turn the minimised repro into a failing test at the correct seam.
2. Watch it fail.
3. Apply the minimal fix.
4. Watch it pass.
5. Re-run the Phase 1 loop against the original (un-minimised) scenario.

---

## Phase 8 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run Phase 1 loop or signal query)
- [ ] Regression test passes (or absence of correct seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted or moved to a clearly-marked debug location
- [ ] The hypothesis that turned out correct is stated in the commit/PR message

**Then ask: what would have prevented this?** If the answer involves architecture (no good test seam, tangled callers, hidden coupling), raise it after the fix is in.

**Add the exemplar** to the relevant reference file:

```markdown
### Exemplar: <brief description> (<date>)
- **Symptom**: what was reported or alerted
- **Signal**: `<query or loop>` → `<key output>`
- **Alternatives ruled out**: what was checked and eliminated
- **Root cause**: "[specific thing] because [evidence], not [ruled-out]"
- **Fix**: what was changed
- **Prevention**: what would stop recurrence
```
