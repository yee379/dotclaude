# Authorisation Model Review

Loaded at §4.3, after `rbac-patterns.md`. **Trigger:** the change adds or modifies a role,
permission, scope, ownership rule, sharing or invitation feature, admin capability, API token
type, or any place an authorisation decision is made.

Step 1 and §4.3 verify each entrypoint **has** a decision. This asks whether the **model those
decisions implement** is coherent. A system where every endpoint checks something, but the
somethings do not compose, fails in ways per-endpoint review cannot see — because each individual
check is correct.

---

## 1. Where are the decisions made?

- **Count the policy decision points.** One function answering "may actor A do X to object O", or
  logic inlined across N handlers?
- Scattered logic is not a vulnerability today; it **guarantees** one, because the next endpoint
  will implement the rule slightly differently. Report as `medium` with that reasoning, not as a
  style note
- Can the decision be **tested in isolation** and **enumerated** — "what can this user do?"
  without executing every route?
- Are there **two** authorities that can disagree (gateway policy vs in-service check,
  middleware vs decorator)? Which wins, is divergence detectable, and does a request satisfying
  one but not the other get through?
- Any decision made client-side only? (`client-side-security.md` §7)

## 2. Escalation inside the model

The most-missed class here. Every permission has a transitive closure; walk it looking for a path
to administrator.

- **Edit roles** ⇒ grant themselves or a colleague a higher role — admin in one step
- **Invite members** ⇒ invite with a role above their own, or into another tenant
- **Manage API tokens** ⇒ mint a token with broader scope than they hold. Scope must be bounded
  by the minter's *current* authority at **use** time; otherwise a demoted user's old token keeps
  its old power
- **Edit an integration, webhook, or CI config** ⇒ run code or use credentials they do not hold.
  The usual tenant-escape route
- **Group or team ownership** ⇒ add themselves to a more privileged group
- **Ownership transfer or object move** ⇒ acquire rights over another tenant's object
- **Modify their own audit trail** (`detection-audit.md`)

Write the closure explicitly; severity follows who can start the walk:

```
support_agent
  → may impersonate any user          (support.py:61)
  → impersonated user may rotate own API token
  → token inherits impersonated scope, no expiry
  ⇒ support_agent holds permanent credentials for any account   [high]
```

## 3. Confused deputy

- Does the service act **on its own credentials** against a caller-chosen target? Fetching a
  caller-supplied URL with the service token, reading a caller-supplied path as the service user,
  running a caller-supplied query through a privileged connection. The caller has borrowed the
  service's authority
- **Deferred work is where this hides:** a queued job, retry, scheduled export, or reconciliation
  loop typically runs with *service* authority and a decision made at enqueue time. Is the
  original actor's authority re-checked at execution, or has the user been demoted or offboarded
  since?
- **Impersonation and support tooling:** is the real actor recorded alongside the effective one,
  is access time-bounded, is it consented or notified, and can the impersonator reach anything
  the impersonated user cannot (an admin panel rendered inside their session)?

## 4. Default and failure direction

- For a **new** resource type, field, or route: deny or allow if no rule matches? Default-allow
  with a deny-list rots the day someone adds a resource. Only default-deny composes
- If the policy engine, role store, or introspection endpoint is **unavailable**, does the check
  fail closed? An availability-driven fail-open is a full bypass triggerable by making one
  dependency slow
- **Wildcards and inheritance:** does a parent grant silently cover children created later? Is
  that intended, and visible to whoever grants it?
- Are permissions additive only, or can a deny be shadowed by an allow?

## 5. Comprehensibility

- Can the model be stated in **one sentence per role**? If not, no reviewer and no administrator
  can verify it, so the effective policy is whatever the code happens to do
- **Role explosion** — a dozen roles differing by one permission each means the model should be
  attribute- or relationship-based, and that nobody knows what the middle roles grant
- Can "who in my organisation can see this?" be answered from the model rather than by reading
  handlers?
- [ ] **A role × operation matrix test exists** — each role against each sensitive operation,
      asserted automatically. The only artefact that catches the regression when someone adds a
      route later, and its absence is why "we checked every endpoint" does not stay true.
      Cross-ref `/codebase-eng-review`'s test adequacy rubric

---

## Required output

1. Number of policy decision points and where (`file:line`).
2. The §2 closure walk, with any path to elevated authority named.
3. Default direction for unmatched resources; failure direction of the policy dependency.
4. Whether the role × operation matrix test exists.

Anything undetermined goes to `## Unverified Leads` with what you searched.
