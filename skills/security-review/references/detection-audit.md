# Detection, Audit, and Forensic Readiness

Loaded at §4.13. **Trigger:** always.

Everything else in this skill is prevention. This asks: **if this were exploited, would we know —
and could we reconstruct it?** Breaches are usually reported by a third party weeks later, and
the reconstruction fails for want of audit data, not for want of a preventive control. Detection
is also the cheapest control available: a log line and an alert rule.

Same evidence standard — a box is ticked only with a `file:line` showing the event is emitted.

---

## 1. Security-relevant events

Required when the change introduces or modifies any of these:

| Event | Why |
|---|---|
| Authentication success **and** failure | Failures find brute force; successes are what you need after a credential leak |
| Authorisation denial | An account probing beyond its rights — see §2 |
| Role, permission, or group membership change | The escalation event itself |
| Credential/key/secret access | Answers "was the key read before it was used elsewhere?" |
| Credential creation, rotation, revocation | An attacker's minted token is a persistence mechanism |
| MFA enrolment, reset, disable | Standard account-takeover step |
| Session or token revocation | Proves containment happened |
| Impersonation / support access — start **and** end | Highest-risk action in most systems |
| Bulk read, export, report generation | The difference between "access was possible" and "data left" |
| Tenant-boundary crossing by an internal tool | The only trace a tenancy bug leaves |
| Configuration, policy, or feature-flag change | Attributes a posture change to an actor |
| Record deletion | Destruction is its own impact class |

Each event carries:

- [ ] **Actor** — authenticated identity, not only an IP. Where acting on someone's behalf,
      **both** the real and the effective actor
- [ ] **Action** and **target** — the object's identifier, not a type name
- [ ] **Outcome** — allowed or denied, explicitly. Successes-only logging cannot distinguish a
      quiet system from a blind one
- [ ] **Timestamp** (UTC, trusted source), source IP, user agent
- [ ] **Correlation ID**, joining the event to its request
- [ ] **Tenant**, in any multi-tenant system

## 2. Authorisation denials

One 403 is noise; thirty from one account in a minute is enumeration in progress. Highest-value
detection signal in an authenticated application, and usually absent — most frameworks reject
inside a dependency and emit nothing.

**Verify empirically: trigger a denied request and look for the log line.** If nothing appears,
the finding is "authorisation denials are not recorded at `deps.py:34`".

## 3. Audit trail integrity

- [ ] Separate from application logs; the application cannot rewrite or delete its own audit
      history. If app-level compromise means log-level compromise, the trail is worthless
      precisely when it matters
- [ ] Append-only, or shipped off-host immediately
- [ ] **Retention stated** and long enough — dwell time is measured in months; logs rolling at
      7 days make forensics impossible
- [ ] Queryable **both ways** — by actor ("what did this token touch?") and by object ("who read
      this record?"). One direction cannot scope an incident
- [ ] Clock integrity: events from different hosts are comparable

## 4. Signals worth alerting on

Each needs a firing location, a recipient, and a first runbook step. An alert with no recipient
is a log line.

- Authorisation-denial rate per actor over threshold
- Authentication failure rate per account and per source; impossible or first-seen geography
- Any grant of an administrative role, to anyone
- Secret or key accessed outside a deploy window, or by an unexpected identity
- Bulk read/export volume outside the normal envelope for that actor
- Outbound connection to a first-seen destination (the exfiltration signal)
- Unexpected process or file write inside a container (Falco) — cluster-level coverage is
  `/platform-security-review`

## 5. Forensic readiness

- Given a credential compromised at time *T*, can you **list everything it accessed** since *T*?
- Can you distinguish "data was exfiltrated" from "access was possible"? Writes are usually
  logged, reads usually are not — and disclosure obligations turn on reads
- Is there a **documented revocation path** (invalidate sessions, rotate, revoke derived tokens),
  and has it been exercised? `vuln-classes.md` class 8 asks whether revocation is possible at all
- **Blast radius:** what else authenticates with this credential, key, or service account? If the
  answer requires reading code, that is the gap

## 6. The tension with §4.8

Detection wants context; data protection forbids it. They resolve at one line: **log identifiers
and decisions, never payloads and secrets.** Where a body genuinely aids investigation, redact at
the emitter, not at the query.

---

## Findings

A missing audit event is a finding, not a recommendation. Typically **medium**. **High** where
the unlogged action is a privilege change, impersonation, bulk export, or credential mint — the
absence destroys the only evidence the attack would have left, so the impact is that of an
undetectable compromise. Absent detection never lowers the severity of a preventable flaw.
