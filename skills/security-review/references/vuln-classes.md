# Vulnerability Classes the Main Checklist Does Not Cover

Load at Step 3, after the hunt patterns. The ten sections in `SKILL.md` cover the classes that
show up in code as a *bad pattern*. These classes show up as a *missing* pattern, an
interaction, or a logic error — grep alone will not surface them, so each one below is a
question you must actively answer for this change.

For each class: if the change touches the trigger, answer the questions and record the answer.
"Not considered" is itself a finding.

---

## 1. IDOR / Broken Object Level Authorisation

*Trigger:* any endpoint that accepts an identifier the caller supplies.

- For each such endpoint, is the object fetched **and then** ownership-checked, or is the query
  itself scoped to the caller? (Scoped query is safer — a separate check can be forgotten.)
- Are identifiers sequential integers? If so, enumeration is trivial — is that acceptable?
- Does the *error* differ between "does not exist" and "not yours"? That difference is an oracle.
- Nested resources: is the parent-child relationship verified, or only the child?
  `/orgs/1/projects/99` where project 99 belongs to org 2.

## 2. Broken object property level authorisation (mass assignment)

*Trigger:* any handler that spreads a request body into a model or update call.

- Which fields can the caller set? List them. Is there a field they should not reach —
  `role`, `is_admin`, `owner_id`, `tenant_id`, `price`, `balance`, `verified`?
- Is the write schema **separate** from the read schema, or is one model used for both?
- On update, does the code allow-list fields, or block-list them? Block-lists rot.

## 3. SSRF

*Trigger:* the service fetches any URL, hostname, or file path influenced by input.

- Is the destination host validated against an allowlist *after* DNS resolution, or only the
  string checked before?
- Are redirects followed? A permitted host can redirect to `169.254.169.254`.
- Are link-local, loopback, and private ranges blocked? Is the cloud metadata endpoint blocked?
- Can the response body or its timing be observed by the caller? That turns blind SSRF into a
  port scanner.

## 4. Race conditions and TOCTOU

*Trigger:* any check-then-act on shared state — balances, quotas, one-time tokens, uniqueness.

- Two concurrent requests: can a coupon be redeemed twice, a balance go negative, a unique
  constraint be bypassed?
- Is the invariant enforced in the database (constraint, `SELECT ... FOR UPDATE`, atomic
  decrement) or only in application code between two statements?
- Idempotency: does a retried request re-apply the side effect?

## 5. Business-logic abuse

*Trigger:* anything involving quantity, price, state transitions, or limits.

- Negative or zero quantities. Very large quantities (integer overflow, memory).
- Can a state machine be entered out of order — refund before payment, ship before pay,
  verify-email skipped?
- Are limits enforced server-side, or is the client trusted to send the price/total/discount?
- Can a workflow step be replayed?

## 6. Multi-tenant data isolation (application layer)

*Trigger:* any shared-schema table holding more than one tenant's rows.

- Is tenant scoping enforced structurally — row-level security, a mandatory query filter, a
  session-scoped connection — or by remembering to add `WHERE tenant_id = ?` each time?
- Do background jobs, exports, admin tools, and cache keys carry the tenant boundary too?
  These are where bleed usually happens, not the main request path.
- Cluster-level tenancy is `/platform-security-review`'s lane; this is the data layer.

## 7. Cache and key confusion

*Trigger:* any caching of a response that varies by identity.

- Does the cache key include the user/tenant/role? A cached authorised response served to an
  anonymous caller is a data breach with no exploit code.
- CDN or reverse proxy: is `Cache-Control: private` set on authenticated responses?
- Is any unkeyed header reflected into the cached response (cache poisoning)?

## 8. Authentication edge cases

*Trigger:* any change to login, session, or token handling.

- Is there a second way in — API token, legacy endpoint, service account, impersonation,
  password reset, SSO fallback? Each is an auth path and must be reviewed as one.
- Password reset: is the token single-use, expiring, and unguessable? Is the account enumerable
  from the response?
- Session fixation: is the session identifier rotated on privilege change (login, role switch)?
- Logout / revocation: can a stolen token be invalidated before its expiry, or is it valid until
  it expires no matter what?
- MFA: can it be skipped by hitting the post-MFA endpoint directly?

## 9. Untrusted content reaching an LLM with tools

*Trigger:* any prompt assembled from data the user or a third party controls, where the model
can call tools.

- Indirect injection: content fetched from a page, file, or ticket enters the prompt — can it
  instruct a tool call? Assume it will try.
- Is the tool set scoped to the least privilege needed for the task, or is it the full set?
- Is model output that becomes a command, query, path, or URL validated the same way user input
  would be? Model output is untrusted input.
- Can the model reach a secret, an internal endpoint, or another tenant's data through a tool?

## 10. Supply chain beyond CVEs

*Trigger:* any new dependency, action, or base image.

- Is the package name a typosquat of a popular one? Was it published recently with few
  downloads? Does it run code at install time (`postinstall`, `setup.py`)?
- Dependency confusion: does every internal package resolve only from the private index?
- Are GitHub Actions pinned to a commit SHA, not a tag?
- Does CI expose secrets to workflows triggered by forks (`pull_request_target`, `workflow_run`)?
- Is any third-party script loaded from a CDN without an SRI hash?

## 11. Secrets already leaked

*Trigger:* always. Independent of whether this change adds a secret.

- Was a credential ever committed? `.gitignore` does not un-leak history — the only remedy is
  rotation, and the review should say so explicitly.
- Are credentials sitting untracked in the working tree that a `git add -A` would capture?
- Do any secrets appear in CI logs, build artefacts, image layers, or error reports?

## 12. Denial of service through resource asymmetry

*Trigger:* any endpoint where a small request causes large work.

- Unbounded pagination, unbounded query depth (GraphQL), unbounded upload size, unbounded
  regex backtracking, unbounded decompression.
- Is there a per-caller cost limit, or only a request-count rate limit? Rate limiting by count
  does not stop one expensive request.
