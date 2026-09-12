# Threat Model Framing

Loaded at **Step 0**, before the attack-surface table. **Trigger:** always. Five minutes, not a
document.

Step 1 enumerates *entrypoints*. This states *who is attacking* and *what is worth taking*.
Without it a review allocates attention by how easy each control is to check rather than by what
is at risk — which is how a thorough checklist walk misses the one thing that mattered.

---

## 1. Assets

Three to five is enough.

| Asset | Where it lives | Worst case |
|---|---|---|
| Signing / encryption key | KMS, pod env | Forge any token; decrypt everything historical |
| Customer personal data | primary DB, warehouse copy | Disclosure plus notification obligation |
| Tenant isolation itself | query layer, cache keys | One customer reads another's data |
| Money movement | payment handlers | Direct loss, chargebacks |
| Record integrity | ledger, audit tables | Silent alteration — often worse than disclosure, because nothing is trustworthy afterwards |
| Availability of the core flow | the request path | Users cannot work |

Integrity is the most-omitted row. A leaked record is bad; a **quietly altered** one means
nothing in the system can be trusted.

## 2. Adversaries

The stance already assumes a hostile authenticated caller. Broaden it — each has a different
starting position and therefore a different likely path.

| Adversary | Starts with | Wants | Likely route |
|---|---|---|---|
| Unauthenticated internet | Rate-limited edge access | Any foothold | Unauth route, known CVE, exposed debug surface |
| Legitimate customer | Valid account, own tenant | Other tenants' data, free usage | IDOR, business-logic abuse, tenancy bleed |
| Malicious tenant admin | Full rights within their tenant | To escape the tenant | Webhook/integration config, file upload, template injection, SSO settings |
| Compromised account | A real user's full authority | Whatever that user reaches, quietly | Everything the user may legitimately do — no control fires |
| Compromised dependency or CI | Execution in build or runtime | Secrets, persistence | Supply chain, `pull_request_target`, unpinned action |
| Insider or support staff | Privileged tooling | Specific records | Impersonation, direct DB access, export |
| Neighbouring workload | Network position in-cluster | Lateral movement | Missing NetworkPolicy, shared service account, unauthenticated internal endpoint |

State which apply to **this change** and which you are deprioritising, with the reason. "All of
them" is the absence of a model.

## 3. Trust zones

A Step 5 trace follows one path; this shows the shape, which is what reveals the edge nobody
considered.

```
┌─ untrusted ────┐   ┌─ authenticated ──────────────────┐   ┌─ trusted ──┐
│  browser       │──▶│  gateway ──▶ api ⇢ queue ──▶ job │──▶│  postgres  │
│  webhook src   │──▶│         ↘ admin ui               │   │  object st │
└────────────────┘   └──────────────────────────────────┘   └────────────┘
                          ▲ edge: what authenticates the job's DB access?
```

Per edge, four things: what **authenticates** it, what **authorises** it, what **validates** the
data crossing it, what **logs** it. An internal edge answered with "nothing — it's internal" is
exactly the assumption this review exists to challenge.

## 4. What this change does to the model

The value is the diff, not the inventory:

- A new entrypoint reachable from a less-trusted zone?
- Existing data moving into a new zone — a field added to a public response, a new export, a new
  replica, a new third-party destination (`data-governance.md` §3)?
- A new credential holder, or a new credential for an existing component?
- A **trust assumption inherited rather than verified** — "the gateway already validated it",
  "only internal services can reach this", "the queue is trusted"? Name each; these become the
  highest-value Step 1 items

## 5. Output

Three to eight lines, before the entrypoint table:

```
Assets at risk:     tenant isolation (shared orders table), customer PII (new export)
Adversaries:        legitimate customer (primary), malicious tenant admin (webhook config)
                    deprioritised: unauth internet — no new unauthenticated route
Zone crossings:     new — worker ⇢ customer-supplied webhook URL (untrusted destination)
Inherited trust:    consumer assumes producer validated tenant_id (unverified)
Implied priority:   authorisation model + tenancy + SSRF over supply chain this round
```

A later section skipped with a reason grounded here is a judgement; one skipped without it is an
omission.
