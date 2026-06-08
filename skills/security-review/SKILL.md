---
name: security-review
description: Security review checklist for backend APIs, Kubernetes workloads, GraphQL endpoints, Python services, and infrastructure — covering secrets management, input validation, authentication, authorisation, injection prevention, supply chain security, open CVEs, defense in depth, and zero trust architecture.
license: MIT
compatibility: opencode
---

# Security Review

## Workflow position

```
/draft-prd → /board-review (board, parallel with codebase-arch-review, codebase-eng-review, doc-review)
      │
      ▼
/security-review       ← YOU ARE HERE: security gate: secrets, auth, input validation,
      │                  injection prevention, supply chain, Kubernetes workload security
      ▼
implementation → /codebase-closeout → /prod-release
```

Run after `/codebase-eng-review` and before promoting to production. This skill checks that the implementation is safe to ship — not just correct. Any security finding here should block `prod-release` until resolved.

To run all gates in sequence automatically, use `/board-review` instead of invoking each skill individually.

---

## Subagent mode

When this skill runs inside `/board-review` the orchestrator will provide:
- `Plan file:` — path to read from disk
- `Output file:` — path to write findings to (e.g. `todo/review/<slug>/round-N-sr.md`)

**If an output file path was provided, follow this protocol exactly:**

1. **Write the skeleton first** — before any analysis, create the output file:
   ```
   ## Summary
   _(written last)_

   ## Issues
   _(in progress)_

   ## Decisions Required
   _(in progress)_

   ## Amendments
   _(in progress)_

   ## Status
   IN PROGRESS
   ```

2. **Write after every section** — after completing each checklist section (secrets,
   auth, authorisation, input validation, API security, Kubernetes, supply chain, data
   protection, CVE scan, defense in depth):
   - Append new findings to `## Issues` in the output file (SEVERITY | area | description)
   - Append any Decisions Required entries
   - Append any plan amendments made
   - Do NOT wait until the end — write each section's findings immediately

3. **Suppress AskUserQuestion** — do not call AskUserQuestion. For every decision point
   write a structured `### Decision:` entry in `## Decisions Required` and continue.
   Security findings that are unresolvable without user input get `blocking` severity.

4. **Write ## Summary and final ## Status last** — replace the _(written last)_ placeholder
   only after all sections are complete. Set ## Status to PASS | PASS WITH WARNINGS | FAIL.

---

## Priority hierarchy

If running low on context: auth/authz → injection/input validation → secrets → Kubernetes
→ supply chain → data protection → CVE scan → defense in depth. Never skip auth/authz.

---

**Model routing: `opus`.** Security review requires adversarial reasoning — thinking like an attacker, tracing trust boundaries across the full stack, and catching subtle auth logic flaws that pattern-matching misses. Do not run at Sonnet or Haiku.

## When to Use

- Implementing or modifying authentication or authorisation
- Adding new API endpoints or GraphQL operations
- Handling file uploads or user-generated content
- Changing how secrets or credentials are stored/accessed
- Deploying new Kubernetes workloads
- Integrating third-party services
- Preparing for a security audit or pen test

---

## 1. Secrets Management

**Never store secrets in code, config files, or container images.**

```python
# BAD — hardcoded secret
DATABASE_URL = "postgresql://user:s3cr3t@db:5432/app"
API_KEY = "sk-proj-abc123"

# GOOD — environment variables validated at startup
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str       # fails at startup if missing
    api_key: str
    jwt_secret: str

settings = Settings()      # raises if any required var is absent
```

```yaml
# BAD — secret value in Kubernetes manifest
env:
  - name: DB_PASSWORD
    value: "s3cr3t"

# GOOD — reference from Secret (or better: External Secrets Operator)
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: password
```

**Checklist:**
- [ ] No hardcoded secrets in source code
- [ ] No secrets in Dockerfile or image layers (`docker history` clean)
- [ ] `.env` files in `.gitignore`; no `.env` committed
- [ ] Production secrets stored in vault / AWS Secrets Manager / GCP Secret Manager
- [ ] Kubernetes secrets encrypted at rest (etcd encryption)
- [ ] Secret rotation plan exists for API keys and DB credentials

---

## 2. Authentication

Load `references/jwt-authentication.md` for JWT verification and secure cookie patterns.

---

## 3. Authorisation

**Check on every request — not just at the gateway.**

Load `references/rbac-patterns.md` for ownership check and role dependency patterns.

---

## 4. Input Validation & Injection Prevention

**Never trust user input.**

Load `references/injection-prevention.md` for SQL, command, path traversal, and Pydantic validation patterns.

---

## 5. API Security

Load `references/api-security.md` for rate limiting and security headers middleware patterns.

---

## 6. Kubernetes Security (Application Deployment)

For full platform-layer security review (RBAC policies, NetworkPolicy topology, multi-tenancy, service mesh), use `/platform-security-review`.

Application-level deployment checklist:
- [ ] Container runs as non-root (`runAsNonRoot: true`, `runAsUser` set)
- [ ] Read-only root filesystem (`readOnlyRootFilesystem: true`)
- [ ] Privileged mode disabled (`privileged: false`, `allowPrivilegeEscalation: false`)
- [ ] NetworkPolicy applied (default-deny + explicit ingress/egress rules)
- [ ] RBAC: ServiceAccount has least-privilege permissions only
- [ ] Secrets injected via mounted volume or external-secrets, not environment variables
- [ ] No secrets in image layers or ConfigMaps
- [ ] Image referenced by digest (not mutable tag) in production
- [ ] Image vulnerability scan passes in CI (trivy/grype)
- [ ] CISA KEV check: no known-exploited CVEs in base image or deps

---

## 7. Dependency & Supply Chain Security

```bash
# Python
pip-audit                          # check for known CVEs
uv lock --upgrade                  # update lockfile

# Node
npm audit --audit-level=high
npm audit fix

# Container images
trivy image ghcr.io/org/api:1.4.2
grype ghcr.io/org/api:1.4.2

# Pin base image digests (not just tags)
FROM python:3.12-slim@sha256:abc123...
```

**Checklist:**
- [ ] Dependency vulnerability scan in CI (blocks on high/critical)
- [ ] Lock files committed (`uv.lock`, `package-lock.json`)
- [ ] Base image pinned to digest, not just tag
- [ ] Automated PRs for dependency updates (Dependabot / Renovate)
- [ ] Third-party scripts not loaded from CDN without SRI hash

---

## 8. Data Protection

```python
# Logging — never log sensitive data
# BAD
logger.info(f"User login: email={email}, password={password}")
logger.debug(f"Payment: card={card_number}, cvv={cvv}")

# GOOD
logger.info("User login attempt", extra={"user_id": user_id, "email_domain": email.split("@")[1]})
logger.info("Payment initiated", extra={"user_id": user_id, "amount": amount, "currency": currency})

# Masking PII in error reports
def mask_email(email: str) -> str:
    local, domain = email.split("@")
    return f"{local[:2]}***@{domain}"
```

**Checklist:**
- [ ] No passwords, tokens, or full card numbers in logs
- [ ] PII masked in logs and error reports
- [ ] Sensitive fields excluded from API responses unless required (password hash, internal IDs)
- [ ] Data retention policy enforced (old records purged per policy)
- [ ] PII fields encrypted at rest in database (if required by compliance)
- [ ] GDPR/CCPA: user data deletion flow implemented

---

## 9. Open CVE & Vulnerability Intelligence

**Active CVEs are threat intel, not just CI hygiene.** Beyond scanning dependencies, the reviewer should assess whether any known CVEs are exploitable in the current deployment context.

```bash
# Scan code dependencies
pip-audit --format=json --output=audit.json
npm audit --json > audit.json

# Scan container images — report critical and high
trivy image --severity CRITICAL,HIGH ghcr.io/org/api:1.4.2
grype ghcr.io/org/api:1.4.2 --fail-on high

# Check OS packages inside running container
trivy image --vuln-type os ghcr.io/org/api:1.4.2

# Query NVD/OSV for specific package CVEs
# https://osv.dev/list   — searchable by package name
# https://nvd.nist.gov/  — NVD search
```

**Reviewer tasks:**
1. **Run a CVE scan** against the feature branch's dependency manifest and container image.
2. **Triage each critical/high finding** — is it reachable given the app's usage? Document reasoning.
3. **Check EPSS score** for critical CVEs — Exploit Prediction Scoring System indicates exploitation likelihood. Prioritise EPSS > 0.5.
4. **Check for newly disclosed CVEs** in frameworks used (FastAPI, Django, Next.js, etc.) against the NVD feed since last review.
5. **Cross-reference with CISA KEV** (Known Exploited Vulnerabilities catalogue) — any match is an immediate blocker.

**Checklist:**
- [ ] `pip-audit` / `npm audit` / `trivy` run and output reviewed
- [ ] All CRITICAL findings either patched, mitigated, or documented as accepted risk with rationale
- [ ] HIGH findings triaged — exploitability in context assessed
- [ ] CISA KEV catalogue checked — no matches in production dependencies
- [ ] CVE scan integrated into CI pipeline (blocks merge on CRITICAL)
- [ ] Suppression/allowlist file reviewed — no stale suppressions hiding real risk

---

## 10. Defense in Depth & Zero Trust

**Assume breach at every layer.** Defense in depth means no single control failure leads to full compromise. Zero trust means nothing is implicitly trusted — not internal traffic, not service-to-service calls, not the cluster network.

Load `references/zero-trust.md` for mTLS, AuthorizationPolicy, workload identity patterns, and defense-in-depth / zero-trust checklists.

---

## Pre-Deployment Quick Reference

Before every production deployment of a security-relevant change:

- [ ] Secrets: no hardcoded values; rotation plan exists
- [ ] Auth: JWT/session handling correct; brute-force protection in place
- [ ] Authz: ownership checks on all user-data endpoints
- [ ] Input validation: all user inputs go through schema validation
- [ ] Injection: no SQL/command/path injection vectors
- [ ] Rate limiting: aggressive on auth; present on all public endpoints
- [ ] Security headers: HSTS, CSP, X-Frame-Options configured
- [ ] Kubernetes: non-root, read-only FS, NetworkPolicy, capability drop
- [ ] Dependencies: no known CVEs; lock file committed
- [ ] Logging: no PII or secrets in log output
- [ ] OWASP Top 10: each item considered and addressed or acknowledged
- [ ] CVEs: critical/high findings triaged; CISA KEV checked; no active exploits in deps
- [ ] Defense in depth: auth enforced at gateway AND service layer; blast radius scoped
- [ ] Zero trust: mTLS between services; workload identity in use; no long-lived static credentials
