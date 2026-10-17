# Vulnerability Classes the Main Checklist Does Not Cover

Load at Step 3, after the hunt patterns. The verification sections in `SKILL.md` §4 cover the
classes that show up in code as a *bad pattern*. These classes show up as a *missing* pattern, an
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
- **Excessive autonomy:** does a high-impact or irreversible action — moving funds, modifying
  production, sending a communication — execute without a human-in-the-loop gate? Scoping the tool
  set (above) bounds *what* the model can reach; this bounds *whether it can act alone* once it
  reaches it. Both answers are required, not one or the other.
- If any tool is served by an MCP server, review the server itself against `mcp-security.md` — a
  vulnerable tool-serving process is a separate risk from a malicious prompt reaching a clean one.

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

## 12. Denial of service and denial of wallet

*Trigger:* any endpoint where a small request causes large work, or spends money.

- Unbounded pagination, unbounded query depth (GraphQL), unbounded upload size, unbounded
  regex backtracking, unbounded decompression.
- Is there a per-caller cost limit, or only a request-count rate limit? Rate limiting by count
  does not stop one expensive request.
- **Denial of wallet:** on autoscaling and metered infrastructure, the failure mode is a bill
  rather than an outage — and nothing alerts, because the system stays up. Which caller-triggered
  paths spend money per request: LLM tokens, a paid third-party API, egress, storage writes, a
  scale-out that the request load drives? Is there a per-tenant spend cap and an anomaly alert,
  or only a request-rate limit?
- Amplification outward: can a caller make the service issue many expensive requests to a
  third party — turning your credentials into their attack budget?

## 13. API shape abuse

*Trigger:* GraphQL, a batch or bulk endpoint, an export, or any endpoint that accepts a list.

- **Aliasing and batching:** can one HTTP request carry N logical operations? If so, every
  count-based control — rate limit, lockout counter, quota — is measuring the wrong unit, and
  1000 password attempts arrive as one request. Verify the limiter counts operations.
- **Nested resolvers:** is authorisation enforced on each resolver, or only at the top-level
  query? A field denied via one parent is often reachable via another.
- **Introspection** in production publishes the schema, including fields the UI never calls.
- **The bulk path beside the checked path:** a single-record endpoint with a correct ownership
  check, and an export/bulk/stream endpoint next to it that filters differently or not at all.
  Compare them directly — this is one of the highest-yield checks in the whole review.
- **Field selection as disclosure:** can a caller request a field the UI hides? Over-fetching is
  disclosure regardless of what the client renders.
- **Inventory management (OWASP API9):** does a deprecated or undocumented API version still
  respond? List every version reachable, not just the one the current client calls — a zombie
  endpoint often skipped the authz/validation fixes the current one received.
- **Unsafe consumption of APIs (OWASP API10):** does this service trust a downstream API's response
  without validating it — the inverse of SSRF, where the risk is in what your app *does* with a
  reply rather than where it sends the request? A malicious or compromised upstream can return data
  that drives an injection, a redirect, or a trust decision on your side.

## 14. Client-side trust boundary

*Trigger:* any browser-facing change. Full treatment in `client-side-security.md`.

- Does any validation, authorisation, or business rule exist **only** in the client? List them
  and confirm the server repeats each one.
- Is a hidden or disabled UI control treated as access control?
- Does the bundle carry a secret, an internal hostname, or an unreleased endpoint path?
- Is a stored XSS reachable by a lower-privileged user and rendered to a higher-privileged one?
  That is a privilege-boundary crossing, not a cosmetic bug.

## 15. RAG access-control inheritance

*Trigger:* any retrieval-augmented generation system over a multi-tenant or mixed-trust document
store.

- Does a document's access-control metadata propagate from ingestion to each individual retrieved
  chunk, or is access checked only at ingestion and assumed to hold at retrieval? The two are not
  the same system, and this is a confused-deputy-via-retrieval gap, not a tool-scoping problem.
- Can a document injected into the corpus by a lower-privileged source (a shared drive, a ticket, a
  support inbox) be retrieved into a higher-privileged user's context? That is corpus poisoning, a
  write-time attack distinct from runtime prompt injection.
- Are embeddings themselves treated as sensitive data? A compromised vector store can leak a
  meaningful fraction of the source text back out — embeddings need the access control and
  encryption of the documents they were derived from, not an afterthought.

## 16. Agent-to-agent trust boundaries

*Trigger:* the system orchestrates more than one agent, or an agent at one privilege level can
invoke another.

- A trust boundary exists wherever identity, data, authority, or state crosses into a component with
  a different policy owner — user to orchestrator, orchestrator to a specialist agent, agent to
  shared memory, agent to an external provider. Name each crossing in this change.
- Can a lower-privileged agent cause a higher-privileged one to act on its behalf (vertical
  escalation), or can one agent's output corrupt a peer's context or decision (horizontal
  propagation)? Prompt-level defenses on one agent do not stop propagation across the chain.
- Does shared memory or state between agents carry the same scoping as a direct API call would, or
  is it treated as an internal, implicitly trusted channel?

## 17. Application-layer security misconfiguration

*Trigger:* always — distinct from the Kubernetes pod-security checklist and the crypto key-lifecycle
checklist, which cover different layers.

- Are debug endpoints, admin panels, or verbose error pages reachable in production?
- Are default credentials still active on any component — a database, a cache, an admin console?
- Are standard security headers set (HSTS, CSP, X-Frame-Options, X-Content-Type-Options), or is the
  default framework response relied on?
- Is any feature or endpoint enabled that the application does not use — a default sample route, an
  unused API version, a management interface left on?

## 18. Mishandling of exceptional conditions

*Trigger:* always.

- Does an unhandled exception leak internal state — a stack trace, a query, a file path — into a
  response or a log a lower-privileged actor can read?
- Is there a code path that fails open — an authorization check, a validation step, or a feature
  flag that defaults to allow when its dependency errors?
- Do the error paths for authentication, validation, and business logic behave consistently, or can
  a caller distinguish "invalid input" from "not authorized" from "internal error" in a way that
  becomes an oracle?

## 19. The front door and the backend disagree

*Trigger:* a gateway, proxy, ingress or mesh makes a security decision for a backend —
authenticates, injects an identity header, denies a route, or rewrites headers.

- Identity asserted in a header: can anything other than the gateway reach the backend and set it —
  a neighbouring Pod, a sidecar, another tenant's workload? A NetworkPolicy in the manifests is not
  enforcement: some clusters accept and ignore it (vclusters, CNIs without policy support). Prove
  isolation with a probe from a neighbouring Pod.
- Does a path rule match every path the backend routes to the same handler? Gateways and backends
  decode differently: an encoded separator (`%2F`) kept by one and decoded by the other, encoded
  letters, and double encoding (`%252F`) that passes a check made after one decode. The rule must
  accept every spelling the backend serves.
- Rule precedence across match types (regex against prefix, header and method matches) is
  implementation-specific. A more specific *allow* rule can beat a general *deny*. Measure which
  component answered, per spelling, rather than reading the configuration.
- Fail closed: route guarded requests to a component that refuses everything it does not
  explicitly serve, so a pattern that matches too much denies rather than leaks.
- Before blocking an upstream route, list its callers from source and from access logs. Agents,
  hosts and CLIs often call through the same public gateway, with the same kind of token a hostile
  user holds, so a gateway cannot tell them apart.

## 20. Delegation that outlives or exceeds the grant

*Trigger:* sharing, collaboration roles, delegated administration, or any field a non-owner can
write on an object that later runs as its owner.

- Can a collaborator write something the owner's process consumes — launch arguments, config,
  hooks, environment, a tool allow-list, a schedule? It runs as the owner. Allow-list it at the
  consumer, and log rejected names, never values.
- Does what a grantee wrote survive the grant's revocation — a stored setting, a planted argument,
  a resource moved into the grantee's own object?
- Does revocation propagate? Removing someone from the source of truth (a roster, an IdP group)
  must clear every derived copy: a database flag, a cached role, an issued token. Turning a feature
  off must revoke what it granted, not only stop new grants.
- Can the requester answer its own approval? An approval or step-up whose response the same caller
  can supply in a retry is not an approval.
- Is redaction applied to every representation? A JSON view that redacts secrets beside a raw
  export or bundle download that does not, served at a lower permission level, is the leak.
- Does a report from a semi-trusted agent (a worker, a host, a runner) bind to resources that agent
  owns, or can one tenant's agent fail, close or relabel another tenant's resource by naming its ID?

