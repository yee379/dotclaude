---
name: security-review
description: Adversarial security review for backend APIs, web frontends, Kubernetes workloads, GraphQL endpoints, Python services, MCP and agentic infrastructure, and infrastructure. Threat-models the change, enumerates the attack surface, actively hunts for vulnerable code, and reports findings with an attack path and severity — covering auth bypass, the authorisation model itself, OAuth/OIDC and SAML flow misconfiguration, WebAuthn/passkeys, IDOR, injection, XSS and client-side sinks, SSRF, secrets, cryptographic design, data classification and egress, supply chain, open CVEs, zero trust, and whether an exploit would even be detected. Use when asked to review security, "is this safe", audit for vulnerabilities, or as part of /board-review.
license: MIT
compatibility: opencode
---

# Security Review

## Workflow position

```
/draft-prd → /board-review (parallel with codebase-arch-review, codebase-eng-review, doc-review)
      │
      ▼
/security-review   ← YOU ARE HERE: attack surface, auth, injection, secrets, supply chain
      │
      ▼
implementation → /closeout-prd → /prod-release
```

Runs after `/codebase-eng-review`, before production. Any finding here blocks `prod-release`
until resolved.

**Model routing: `opus`.** Adversarial reasoning, trust boundaries across the full stack, and
auth logic flaws that pattern-matching misses. Not Sonnet, not Haiku.

---

## Stance

**You are not confirming the author followed good practice. You are trying to break this
change.** A review that walks the checklists and finds nothing has usually failed to look.

1. **Enumerate before you check.** You cannot review an entrypoint you never listed. Step 1 is
   not skippable for a "small" change.
2. **Absence of evidence is a finding.** Not "please confirm ownership is checked" but "no
   ownership check found at `orders.py:88`". A box is ticked only with a `file:line` citation.
3. **Hunt suspiciously, report precisely.** Chase every lead; promote only what you can trace.
   Unconfirmed suspicions go to `## Unverified Leads` — never deleted, never inflated.
4. **Assume the caller is hostile and already authenticated.** Most breaches are a valid account
   reaching data that is not theirs, not an anonymous attacker breaking crypto.

Load `references/severity-rubric.md` before writing any finding — severity table, evidence
standard, the two output channels, and the `PASS` gate.

---

## Subagent mode

When run inside `/board-review`, the orchestrator provides `Plan file:` and `Output file:`
(e.g. `todo/review/<slug>/round-N-sr.md`). If given an output path, load
`references/subagent-protocol.md` (in the `board-review` skill directory) and follow it, plus:

- Add `## Unverified Leads` to the skeleton, after `## Issues`.
- Issue format: `SEVERITY | area | file:line | description`. Findings unresolvable without user
  input get `blocking`.

Checkpoints: threat model, attack surface, hunt sweep, vulnerability classes, secrets, auth,
authorisation, authorisation model, OAuth/OIDC, SAML/SSO, WebAuthn, input validation, API security,
client-side, MCP and agentic infrastructure, Kubernetes, supply chain, data protection, data
governance, CVE scan, crypto design, detection and audit, defense in depth, trust boundary trace.

## Priority hierarchy

Low on context: Step 0 → Step 1 → Step 2 → auth/authz and the authorisation model → injection
(server-side, then client-side) → secrets → Step 3 classes → detection and audit → Kubernetes →
supply chain and CVE scan → data protection and governance → crypto design → defense in depth.
**Never skip Step 0, Step 1, Step 2, or auth/authz.** A partial review that enumerated the
surface beats a complete checklist walk that did not.

Supply chain and CVE scan moved up from last-but-one: exploited vulnerabilities in internet-facing
infrastructure are a real, rising initial-access vector per current breach-telemetry reporting,
contested by survey-based reporting that ranks phishing first instead. Treat this as a deliberate
increase in attention, not a claim that injection or auth/authz matter less.

---

## Step 0 — Frame the threat model

Load `references/threat-model.md` and produce its output block: **assets at risk**, **adversaries
in scope** (and which you are deprioritising, with the reason), **zone crossings this change adds
or widens**, **trust assumptions it inherits rather than verifies**.

Five minutes. It is what makes a later deprioritisation a judgement rather than an omission.

---

## Step 1 — Enumerate the attack surface

Before any checklist. Every way data or control enters the system in this change. Missing an
entrypoint invalidates everything downstream.

```bash
git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~5)...HEAD --stat
```

| # | Entrypoint | Type | Reachable by | Auth required | Authz decision at |
|---|---|---|---|---|---|
| 1 | `POST /api/orders/{id}` | HTTP route | any authenticated user | JWT | `deps.py:34` |
| 2 | `orders.created` consumer | queue | any producer on the topic | none | — ← gap |

Sweep beyond HTTP routes: HTTP/GraphQL/gRPC endpoints, queue and stream consumers, webhook
receivers, scheduled jobs, CLI commands and flags, environment variables and config files, file
and object-storage uploads, template render inputs, deserialisation sites, inter-service calls,
admin and debug surfaces, MCP servers and other tool-serving infrastructure, and anything an LLM
tool call can reach.

Per entrypoint: **who reaches it without credentials, and what is the worst they can do if the
authorisation decision is wrong?** A row with no authorisation decision, or one that happens only
at a gateway, is a finding — not a question.

State the count. `Attack surface: N entrypoints enumerated, M without an authorisation decision.`

---

## Step 2 — Hunt

Load `references/hunt-patterns.md` and run every table — `rg` commands per vulnerability class:
injection sinks, authorisation gaps, secret shapes and git history, TLS and crypto misuse, SSRF,
logging disclosure, client-side sinks, GraphQL and API shape, pod security, CI/CD injection.

A hit is a lead: read it in context, then dismiss with a reason or promote it. Record which
tables ran; an omission needs a justification grounded in the code.

---

## Step 3 — Answer the classes grep cannot see

Load `references/vuln-classes.md` — the 20 classes that appear as a *missing* pattern, an
interaction, or a logic error rather than a bad line. For each class the change triggers, answer
its questions and record the answer. **"Not considered" is itself a finding.**

---

## Step 4 — Verify the controls

Verification, not discovery — Steps 1–3 do the finding. **Every box needs a `file:line` citation
or it is reported as unverified.** Ticking rules: `references/severity-rubric.md`.

### 4.1 Secrets management

Fix shapes: `references/remediation-examples.md`.

- [ ] No hardcoded secrets in source, config, or image layers (`docker history` clean)
- [ ] No secret ever committed — checked with `gitleaks` / `git log -S`, not just `.gitignore`
- [ ] Any historically committed credential is **rotated**, not merely removed
- [ ] Production secrets in Vault / Secrets Manager; Kubernetes secrets encrypted at rest
- [ ] Secret rotation plan exists for API keys and DB credentials
- [ ] Secret comparisons are constant-time

### 4.2 Authentication

Load `references/jwt-authentication.md` for JWT verification and secure cookie patterns. Then
enumerate **every** authentication path, not just the one this change touches — class 8 in
`vuln-classes.md`.

If the change touches OAuth or OIDC, load `references/oauth-oidc-security.md` — `redirect_uri`
exact matching, PKCE, issuer binding, and CI/CD OIDC federation trust policy are common gaps a
JWT-only review misses. If it touches SAML or SSO, load `references/saml-sso-security.md` — XML
Signature Wrapping is live in 2025-era CVEs, not a legacy concern. If it touches WebAuthn or
passkeys, load `references/webauthn-passkey-security.md`, and check the account-recovery flow with
the same scrutiny as the passkey flow itself — it is usually the weaker path.

### 4.3 Authorisation

**Checked on every request, at the service layer — not only at the gateway.** Load
`references/rbac-patterns.md` for ownership checks and role dependencies. Cross-check against the
Step 1 table: every entrypoint maps to an authorisation decision.

Then load `references/authz-model.md` for the model those decisions implement — decision point
count, permission closure, confused deputy in deferred work, default direction for unmatched
resources, failure direction when the policy dependency is down, role × operation matrix test.
A system where every endpoint checks something but the somethings do not compose fails in ways
per-endpoint review cannot see.

### 4.4 Input validation and injection prevention

Load `references/injection-prevention.md` for SQL, command, path traversal, and Pydantic
patterns. Validation must allow-list; a block-list is a finding on its own.

### 4.5 API security

Load `references/api-security.md` for rate limiting and security headers. Request-count rate
limiting does not bound cost — check for one expensive request, and confirm the limiter counts
**operations** so GraphQL aliasing and batch endpoints cannot bypass it.

### 4.6 Kubernetes (application deployment)

Platform layer — RBAC topology, NetworkPolicy, multi-tenancy, service mesh — is
`/platform-security-review`. Application deployment:

- [ ] Non-root (`runAsNonRoot: true`, `runAsUser` set), read-only root filesystem
- [ ] `privileged: false`, `allowPrivilegeEscalation: false`, capabilities dropped
- [ ] No `hostNetwork` / `hostPID` / `hostPath` without written justification
- [ ] NetworkPolicy applied — default-deny plus explicit ingress *and* egress
- [ ] ServiceAccount least-privilege; no wildcard verbs or resources; token not auto-mounted if unused
- [ ] Secrets via mounted volume or external-secrets, not environment variables
- [ ] Image referenced by digest, not a mutable tag
- [ ] Image scan passes in CI (trivy/grype); no CISA KEV matches in base image or deps
- [ ] Container runtime and kernel patch level tracked as its own item, not assumed covered by
      application dependency scanning — a workload can pass every check above and still be
      exploitable through the runtime underneath it (e.g. a runc symlink-race escape)
- [ ] No mount of the Docker or CRI-O socket into a workload — the single most-cited real-world
      container-escape path

### 4.7 Dependency and supply chain

```bash
pip-audit                          # Python CVEs
npm audit --audit-level=high       # Node CVEs
trivy image ghcr.io/org/api:1.4.2  # container image
```

- [ ] Vulnerability scan in CI, blocking on high/critical
- [ ] Lock files committed (`uv.lock`, `package-lock.json`) **and honoured by the image build** —
      a build that resolves afresh ships versions the lock never allowed, and its scan results
      describe a different tree
- [ ] Base image pinned to digest; GitHub Actions pinned to commit SHA
- [ ] Automated dependency update PRs (Dependabot / Renovate)
- [ ] No CDN-loaded third-party script without an SRI hash
- [ ] New dependencies checked for typosquatting, install-time scripts, and dependency confusion
- [ ] CI cannot leak secrets to fork-triggered workflows (`pull_request_target`, `workflow_run`)
- [ ] Secrets rotated on a stated cadence, not left valid indefinitely — this is a separate check
      from the fork-PR leakage check above, since a secret can be handled correctly in CI and still
      sit unrotated for years
- [ ] CI runners named explicitly as a compromise target in the threat model, not only developer
      machines — a compromised runner reaches the same secrets a compromised laptop would
- [ ] Third-party SaaS and AI-tool integrations with repo or credential access reviewed as a supply
      chain entrypoint, not assumed safe because they are not a code dependency
- [ ] If an SBOM is generated, something consumes it — re-matched against newly disclosed CVEs after
      release, not only scanned once against the source tree at build time
- [ ] If build provenance (SLSA) is generated, something verifies it before deploy — generation
      without verification satisfies no threat model

### 4.8 Data protection

Fix shapes: `references/remediation-examples.md`.

- [ ] No passwords, tokens, or full card numbers in logs; PII masked in logs and error reports
- [ ] User-controlled values stripped of newlines before logging (log forging)
- [ ] Sensitive fields excluded from API responses (password hash, internal IDs, other tenants' data)
- [ ] Production error handler returns a generic message — no stack traces or SQL in responses
- [ ] Data retention enforced; PII encrypted at rest where compliance requires
- [ ] GDPR/CCPA user data deletion flow implemented

Then load `references/data-governance.md` for the prior question — **should we hold this at all,
and where does it go?** Field classification (including IRB/DUA/export-controlled research data),
minimisation, the egress inventory, production data in non-production, and whether the deletion
flow above reaches every copy. An unenumerated destination is an unreviewed one.

### 4.9 Open CVE and vulnerability intelligence

**Active CVEs are threat intel, not CI hygiene.** Per critical/high finding:

1. Is it **reachable** given how this app uses the package? Document the reasoning either way.
2. **EPSS** — prioritise > 0.5 regardless of CVSS.
3. **CISA KEV match** — an immediate blocker.
4. Newly disclosed CVEs in frameworks used, since the last review.
5. **The upstream project's own tracker** for the version you run: security issues, fix PRs and
   GitHub security advisories (GHSA). Fixes are often public as issues or PRs long before any CVE,
   and a PR closed unmerged leaves the flaw in place.

```bash
trivy image --severity CRITICAL,HIGH ghcr.io/org/api:1.4.2
grype ghcr.io/org/api:1.4.2 --fail-on high
# https://osv.dev/list  ·  https://nvd.nist.gov/
```

- [ ] Scans run and output reviewed
- [ ] All CRITICAL patched, mitigated, or documented as accepted risk with rationale
- [ ] HIGH triaged for exploitability in context
- [ ] CISA KEV checked; CI blocks merge on CRITICAL
- [ ] Suppression/allowlist file reviewed — no stale suppression hiding real risk

### 4.10 Defense in depth and zero trust

**Assume breach at every layer.** Load `references/zero-trust.md` for mTLS,
AuthorizationPolicy, workload identity, and the defense-in-depth checklists. Answer: **when this
service is compromised, what else falls?** Name the blast radius.

### 4.11 Client-side and browser security

*Skip only if the change touches no template, no client bundle, and no browser-facing response —
and say so.* Load `references/client-side-security.md`.

**An XSS in an authenticated application is account takeover** — the attacker executes as the
user, so every control verified in §4.3 is satisfied and no server-side check detects it.

### 4.12 Cryptographic design

*Trigger: the change encrypts, signs, verifies, hashes a password, generates a token or ID, or
introduces a key.* Load `references/crypto-design.md`.

The hunt tables catch bad primitives; this catches correct primitives assembled wrongly — reused
nonce, signature verified after parsing, and a key lifecycle that makes rotation operationally
impossible.

### 4.13 Detection, audit, and forensic readiness

*Trigger: always.* Load `references/detection-audit.md`.

Everything above is prevention. This answers: **if this were exploited, would we know, and could
we reconstruct it?** Absent detection never reduces the severity of a preventable flaw — report
both.

### 4.14 MCP and agentic infrastructure

*Trigger: the change adds, configures, or depends on an MCP server, or orchestrates more than one
agent.* Load `references/mcp-security.md`.

Distinct from class 9 in `vuln-classes.md`, which covers untrusted content reaching a model through
an already-trusted tool: this covers the tool-serving infrastructure itself being the vulnerable
component, and the agent-to-agent trust boundaries when more than one agent is involved — classes
15 and 16 in `vuln-classes.md`. A server trusted "because it only runs locally" is still reachable
by any other local process; local execution is not an authentication boundary.

---

## Step 5 — Trust boundary trace

For each **blocking** or **high** candidate, and the three highest-value Step 1 entrypoints,
write the path from an untrusted caller to the sensitive operation:

```
anonymous → POST /api/webhooks/stripe  (no signature verification, webhooks.py:22)
          → order.mark_paid()          (trusts the payload's amount field)
          → fulfilment queued          → goods ship without payment
```

If you cannot write the path, the item is a lead, not a finding.

---

## Step 6 — Report

Per `references/severity-rubric.md`: findings with a traced attack path go to `## Issues` with
severity, location, why existing controls do not stop it, and the concrete fix. Everything
unconfirmed goes to `## Unverified Leads` with what you tried.

**Every `blocking` and `high` finding names the regression test that ships with the fix** — an
automated test asserting the denied case is denied, failing against the current code. Without it
the fix regresses on the next refactor of that handler.

```
Security Review complete
─────────────────────────────────────────────────────
Threat model:          N assets, N adversaries in scope, N inherited trust assumptions
Attack surface:        N entrypoints enumerated, M with no authz decision
Hunt sweep:            N/N tables run (omitted: <table> — <reason>)
Vulnerability classes: N/20 applicable, N answered
Authorisation model:   N decision points, N escalation paths found
Detection:             N security events logged / N required; denials logged: yes|no
Egress destinations:   N enumerated, N without a covering agreement
Trust boundary traces: N written
─────────────────────────────────────────────────────
Findings:   N blocking / N high / N medium / N low
Regression tests named for blocking/high: N/N
Unverified leads:      N
Controls unverifiable: N (checklist boxes with no citable evidence)
─────────────────────────────────────────────────────
Status: PASS | PASS WITH WARNINGS | FAIL
```

`PASS` asserts "I attacked this and these specific attempts failed", gated on the four conditions
in `severity-rubric.md`. A read-through is `PASS WITH WARNINGS`, and the shallow coverage is the
warning. Say which it was.

---

## Pre-deployment gate

Before a production deploy of a security-relevant change, confirm each §4 checklist was walked
with citations, plus these items that live in the references rather than the boxes above:

- [ ] SSRF: outbound destinations allow-listed after resolution; metadata ranges blocked
- [ ] Races: check-then-act invariants enforced in the database
- [ ] Tenancy: isolation structural, and it holds in jobs, exports, and cache keys
- [ ] Bulk/export paths authorise per record, identically to their single-record siblings
- [ ] Spend: caller-triggered paid work (LLM tokens, third-party APIs, egress) capped and alerted
- [ ] Keys: rotation operationally possible, compromise procedure named, separate per environment
- [ ] Audit trail: separate from app logs, append-only, retention stated, queryable by actor *and* object
- [ ] OWASP Top 10 and API Top 10: each item considered and addressed or acknowledged
- [ ] Mitigations at a gateway or proxy probed per path spelling (encoded separators, double
      encoding), with the answering component identified — not read from the configuration. Write
      probes target objects that do not exist: a probe that succeeds has written real data
