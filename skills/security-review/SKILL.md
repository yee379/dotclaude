---
name: security-review
description: Adversarial security review for backend APIs, Kubernetes workloads, GraphQL endpoints, Python services, and infrastructure. Enumerates the attack surface, actively hunts for vulnerable code, and reports findings with an attack path and severity — covering auth bypass, IDOR, injection, SSRF, secrets, supply chain, open CVEs, and zero trust. Use when asked to review security, "is this safe", audit for vulnerabilities, or as part of /board-review.
license: MIT
compatibility: opencode
---

# Security Review

## Workflow position

```
/draft-prd → /board-review (board, parallel with codebase-arch-review, codebase-eng-review, doc-review)
      │
      ▼
/security-review       ← YOU ARE HERE: security gate: attack surface, auth, injection,
      │                  secrets, supply chain, Kubernetes workload security
      ▼
implementation → /codebase-closeout → /prod-release
```

Run after `/codebase-eng-review` and before promoting to production. Any finding here should block
`prod-release` until resolved. To run all gates in sequence, use `/board-review`.

**Model routing: `opus`.** This requires adversarial reasoning — thinking like an attacker, tracing
trust boundaries across the full stack, and catching auth logic flaws that pattern-matching misses.
Do not run at Sonnet or Haiku.

---

## Stance

**You are not confirming that the author followed good practice. You are trying to break this
change.** A review that walks the checklists and finds nothing has usually failed to look, not
found a secure system.

Four rules govern everything below:

1. **Enumerate before you check.** You cannot review an entrypoint you never listed. Step 1 is
   not optional and not skippable for a "small" change.
2. **Absence of evidence is a finding.** If you cannot locate a control, the output says "no
   ownership check found at `orders.py:88`" — not "please confirm ownership is checked". A box may
   only be ticked with a `file:line` citation.
3. **Hunt suspiciously, report precisely.** Chase every lead; promote only what you can trace.
   Unconfirmed suspicions go to `## Unverified Leads` — never deleted, never inflated.
4. **Assume the caller is hostile and already authenticated.** Most real breaches are a valid
   account reaching data that is not theirs, not an anonymous attacker breaking crypto.

Load `references/severity-rubric.md` before writing any finding. It defines the severity table,
the evidence standard, the two output channels, and the gate on reporting `PASS`.

---

## Subagent mode

When run inside `/board-review`, the orchestrator provides `Plan file:` and `Output file:`
(e.g. `todo/review/<slug>/round-N-sr.md`). If an output file path was given, load
`references/subagent-protocol.md` (in the `board-review` skill directory) and follow it exactly,
with two additions specific to this skill:

- Add a `## Unverified Leads` section to the skeleton, after `## Issues`.
- Issue format: `SEVERITY | area | file:line | description`. Severity per
  `references/severity-rubric.md`. Findings unresolvable without user input get `blocking`.

Checkpoints for this skill: attack surface enumeration, hunt sweep, vulnerability classes, secrets,
auth, authorisation, input validation, API security, Kubernetes, supply chain, data protection,
CVE scan, defense in depth, trust boundary trace.

## Priority hierarchy

If running low on context: Step 1 → Step 2 → auth/authz → injection → secrets → the classes in
Step 3 → Kubernetes → supply chain → data protection → CVE scan → defense in depth. **Never skip
Step 1, Step 2, or auth/authz.** A partial review that enumerated the surface is far more useful
than a complete checklist walk that did not.

---

## Step 1 — Enumerate the attack surface

Before any checklist. Produce a table of **every** way data or control enters the system in this
change. Missing an entrypoint here invalidates everything downstream.

```bash
git diff $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~5)...HEAD --stat
```

| # | Entrypoint | Type | Reachable by | Auth required | Authz decision at |
|---|---|---|---|---|---|
| 1 | `POST /api/orders/{id}` | HTTP route | any authenticated user | JWT | `deps.py:34` |
| 2 | `orders.created` consumer | queue | any producer on the topic | none | — ← gap |

Types to sweep for — do not stop at HTTP routes: HTTP/GraphQL/gRPC endpoints, queue and stream
consumers, webhook receivers, scheduled jobs, CLI commands and flags, environment variables and
config files, file and object-storage uploads, template render inputs, deserialisation sites,
inter-service calls, admin and debug surfaces, and anything an LLM tool call can reach.

For each entrypoint answer: **who can reach it without credentials, and what is the worst thing
they can do if the authorisation decision is wrong?** Any row with no authorisation decision, or
one that happens only at a gateway, is a finding — not a question.

State the count. `Attack surface: N entrypoints enumerated, M without an authorisation decision.`

---

## Step 2 — Hunt

Load `references/hunt-patterns.md` and run every table. It gives concrete `rg` commands per
vulnerability class — injection sinks, authorisation gaps, secret shapes and git history, TLS and
crypto misuse, SSRF and outbound requests, logging disclosure, pod security, and CI/CD injection.

A hit is a lead. Read it in context, then dismiss it with a reason or promote it. Record which
tables you ran; an omitted table needs a justification grounded in the code.

---

## Step 3 — Answer the classes grep cannot see

Load `references/vuln-classes.md`. These are the classes that appear as a *missing* pattern or an
interaction rather than a bad line — IDOR/BOLA, mass assignment, SSRF reachability, TOCTOU and
races, business-logic abuse, application-layer tenant isolation, cache key confusion,
authentication edge cases and alternate paths, untrusted content reaching an LLM with tools,
supply chain beyond CVEs, already-leaked secrets, and resource-asymmetry DoS.

For each class the change triggers, answer its questions and record the answer. **"Not considered"
is itself a finding.**

---

## Step 4 — Verify the controls

The checklists below are verification, not discovery — Steps 1–3 do the finding. **Every box needs
a `file:line` citation or it is reported as unverified.** See the ticking rules in
`references/severity-rubric.md`.

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
enumerate **every** authentication path, not just the one this change touches — see class 8 in
`vuln-classes.md`.

### 4.3 Authorisation

**Checked on every request, at the service layer — not only at the gateway.** Load
`references/rbac-patterns.md` for ownership check and role dependency patterns. Cross-check the
result against the Step 1 table: every entrypoint must map to an authorisation decision.

### 4.4 Input validation and injection prevention

Load `references/injection-prevention.md` for SQL, command, path traversal, and Pydantic patterns.
Validation must allow-list; a block-list is a finding on its own.

### 4.5 API security

Load `references/api-security.md` for rate limiting and security headers. Rate limiting by request
count does not bound cost — check for one expensive request too.

### 4.6 Kubernetes (application deployment)

Full platform-layer review — RBAC topology, NetworkPolicy, multi-tenancy, service mesh — is
`/platform-security-review`. Application deployment:

- [ ] Non-root (`runAsNonRoot: true`, `runAsUser` set), read-only root filesystem
- [ ] `privileged: false`, `allowPrivilegeEscalation: false`, capabilities dropped
- [ ] No `hostNetwork` / `hostPID` / `hostPath` without written justification
- [ ] NetworkPolicy applied — default-deny plus explicit ingress *and* egress
- [ ] ServiceAccount least-privilege; no wildcard verbs or resources; token not auto-mounted if unused
- [ ] Secrets via mounted volume or external-secrets, not environment variables
- [ ] Image referenced by digest, not a mutable tag
- [ ] Image scan passes in CI (trivy/grype); no CISA KEV matches in base image or deps

### 4.7 Dependency and supply chain

```bash
pip-audit                          # Python CVEs
npm audit --audit-level=high       # Node CVEs
trivy image ghcr.io/org/api:1.4.2  # container image
```

- [ ] Vulnerability scan in CI, blocking on high/critical
- [ ] Lock files committed (`uv.lock`, `package-lock.json`)
- [ ] Base image pinned to digest; GitHub Actions pinned to commit SHA
- [ ] Automated dependency update PRs (Dependabot / Renovate)
- [ ] No CDN-loaded third-party script without an SRI hash
- [ ] New dependencies checked for typosquatting, install-time scripts, and dependency confusion
- [ ] CI cannot leak secrets to fork-triggered workflows (`pull_request_target`, `workflow_run`)

### 4.8 Data protection

Fix shapes: `references/remediation-examples.md`.

- [ ] No passwords, tokens, or full card numbers in logs; PII masked in logs and error reports
- [ ] User-controlled values stripped of newlines before logging (log forging)
- [ ] Sensitive fields excluded from API responses (password hash, internal IDs, other tenants' data)
- [ ] Production error handler returns a generic message — no stack traces or SQL in responses
- [ ] Data retention enforced; PII encrypted at rest where compliance requires
- [ ] GDPR/CCPA user data deletion flow implemented

### 4.9 Open CVE and vulnerability intelligence

**Active CVEs are threat intel, not CI hygiene.** For each critical/high finding:

1. Is it **reachable** given how this app uses the package? Document the reasoning either way.
2. **EPSS score** — prioritise > 0.5 regardless of CVSS.
3. **CISA KEV match** — any match is an immediate blocker.
4. Newly disclosed CVEs in frameworks used, since the last review.

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

**Assume breach at every layer.** Load `references/zero-trust.md` for mTLS, AuthorizationPolicy,
workload identity, and the defense-in-depth checklists. The question to answer: **when this
service is compromised, what else falls?** Name the blast radius explicitly.

---

## Step 5 — Trust boundary trace

For each **blocking** or **high** candidate, and for at least the three highest-value entrypoints
from Step 1, write the path from an untrusted caller to the sensitive operation:

```
anonymous → POST /api/webhooks/stripe  (no signature verification, webhooks.py:22)
          → order.mark_paid()          (trusts the payload's amount field)
          → fulfilment queued          → goods ship without payment
```

This is what separates a finding from a guess. If you cannot write the path, the item is a lead,
not a finding.

---

## Step 6 — Report

Per `references/severity-rubric.md`: findings with a traced attack path go to `## Issues` with
severity, location, why existing controls do not stop it, and the concrete fix. Everything you
could not confirm goes to `## Unverified Leads` with what you tried.

```
Security Review complete
─────────────────────────────────────────────────────
Attack surface:        N entrypoints enumerated, M with no authz decision
Hunt sweep:            N/N tables run (omitted: <table> — <reason>)
Vulnerability classes: N/12 applicable, N answered
Trust boundary traces: N written
─────────────────────────────────────────────────────
Findings:   N blocking / N high / N medium / N low
Unverified leads:      N
Controls unverifiable: N (checklist boxes with no citable evidence)
─────────────────────────────────────────────────────
Status: PASS | PASS WITH WARNINGS | FAIL
```

`PASS` asserts "I attacked this and these specific attempts failed" — it is gated on the four
conditions in `severity-rubric.md`. If the review was a read-through rather than an attack, the
status is `PASS WITH WARNINGS` and the shallow coverage is the warning. Say which it was.

---

## Pre-Deployment Quick Reference

Before every production deployment of a security-relevant change:

- [ ] Attack surface enumerated; every entrypoint maps to an authorisation decision
- [ ] Secrets: none hardcoded, none in history unrotated, rotation plan exists
- [ ] Auth: every auth path reviewed, not just the changed one; brute-force protection present
- [ ] Authz: ownership enforced in the query, at the service layer, on every user-data endpoint
- [ ] Input validation: allow-listed schema on all inputs; no injection sink reachable
- [ ] SSRF: outbound destinations allow-listed after resolution; metadata ranges blocked
- [ ] Races: check-then-act invariants enforced in the database
- [ ] Tenancy: isolation structural, and it holds in jobs, exports, and cache keys
- [ ] Rate limiting: aggressive on auth; cost-bounded, not just count-bounded
- [ ] Security headers: HSTS, CSP, X-Frame-Options configured
- [ ] Kubernetes: non-root, read-only FS, NetworkPolicy, capabilities dropped, digest-pinned
- [ ] Supply chain: no known CVEs, lock files committed, actions SHA-pinned, CI secrets contained
- [ ] Logging: no PII or secrets; no stack traces in responses
- [ ] OWASP Top 10 and API Top 10: each item considered and addressed or acknowledged
- [ ] CVEs: critical/high triaged; CISA KEV checked; EPSS considered
- [ ] Defense in depth: enforced at gateway AND service layer; blast radius named
- [ ] Zero trust: mTLS between services; workload identity; no long-lived static credentials
