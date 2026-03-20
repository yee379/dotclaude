---
name: security-review
description: Security review checklist for backend APIs, Kubernetes workloads, GraphQL endpoints, Python services, and infrastructure — covering secrets management, input validation, authentication, authorisation, injection prevention, supply chain security, open CVEs, defense in depth, and zero trust architecture.
license: MIT
compatibility: opencode
---

# Security Review

## Workflow position

```
/feature-plan → /full-review (board, parallel with plan-arch-review, plan-eng-review, plan-doc-review)
      │
      ▼
/security-review       ← YOU ARE HERE: security gate: secrets, auth, input validation,
      │                  injection prevention, supply chain, Kubernetes workload security
      ▼
implementation → /plan-closeout → /prod-release
```

Run after `/plan-eng-review` and before promoting to production. This skill checks that the implementation is safe to ship — not just correct. Any security finding here should block `prod-release` until resolved.

To run all gates in sequence automatically, use `/full-review` instead of invoking each skill individually.

---

A systematic security review for backend services, APIs, and Kubernetes infrastructure. Use before shipping any feature that handles user input, authentication, secrets, payments, or sensitive data.

**Model routing: Opus.** Security review requires adversarial reasoning — thinking like an attacker, tracing trust boundaries across the full stack, and catching subtle auth logic flaws that pattern-matching misses. Do not run at Sonnet or Haiku.

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

```python
# JWT verification — verify signature AND claims
import jwt
from datetime import datetime, timezone

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],     # specify explicitly — never ["*"]
            options={"verify_exp": True, "verify_aud": True},
            audience="api.example.com",
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token")
    return payload

# Tokens in httpOnly cookies (not localStorage — XSS safe)
response.set_cookie(
    key="session",
    value=token,
    httponly=True,
    secure=True,           # HTTPS only
    samesite="strict",     # CSRF protection
    max_age=3600,
)
```

**Checklist:**
- [ ] JWT algorithm explicitly specified (not `["*"]`)
- [ ] Token expiry enforced
- [ ] Tokens stored in httpOnly, Secure, SameSite=Strict cookies
- [ ] Refresh token rotation implemented
- [ ] Brute force protection on login endpoint (rate limiting + lockout)
- [ ] Password hashing with bcrypt/argon2 (min cost factor 12)
- [ ] No sensitive data in JWT payload (only user ID + role)

---

## 3. Authorisation

**Check on every request — not just at the gateway.**

```python
# BAD: assumes gateway enforces auth
async def get_order(order_id: str, db: Session):
    return db.query(Order).filter(Order.id == order_id).first()

# GOOD: enforce ownership in handler
async def get_order(
    order_id: str,
    db: Session,
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order", order_id)
    if order.user_id != current_user.id and current_user.role != Role.ADMIN:
        raise ForbiddenError()
    return order
```

```python
# RBAC pattern — explicit role checks
def require_role(*roles: Role):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise ForbiddenError()
        return current_user
    return dependency

# Usage
@router.delete("/users/{id}")
async def delete_user(
    id: str,
    _: User = Depends(require_role(Role.ADMIN)),
):
    ...
```

**Checklist:**
- [ ] Every endpoint checks auth (no anonymous access to protected routes)
- [ ] Ownership verified — user can only access their own resources
- [ ] Role checks performed in service layer, not only at gateway
- [ ] GraphQL resolvers enforce auth (not just the HTTP layer)
- [ ] Admin routes protected by role, not just auth
- [ ] Insecure direct object reference (IDOR) prevented — IDs are opaque or validated

---

## 4. Input Validation & Injection Prevention

**Never trust user input.**

```python
# SQL injection prevention — always use parameterised queries
# BAD
query = f"SELECT * FROM users WHERE email = '{email}'"
await db.execute(query)

# GOOD: ORM or parameterised
user = await db.execute(select(User).where(User.email == email))
# or raw SQL with params
await db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})

# Command injection prevention
# BAD
import subprocess
result = subprocess.run(f"convert {filename} output.jpg", shell=True)

# GOOD: no shell=True, explicit args
result = subprocess.run(["convert", filename, "output.jpg"], shell=False, check=True)

# Path traversal prevention
from pathlib import Path

BASE_DIR = Path("/app/uploads")

def safe_upload_path(filename: str) -> Path:
    # Strip directory components, get only the filename
    safe_name = Path(filename).name
    path = BASE_DIR / safe_name
    # Verify the resolved path is still inside BASE_DIR
    path.resolve().relative_to(BASE_DIR.resolve())
    return path
```

```python
# Pydantic for input validation — validate before any processing
from pydantic import BaseModel, EmailStr, Field, field_validator

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: UserRole
    age: int = Field(ge=0, le=150)

    @field_validator("name")
    @classmethod
    def name_no_html(cls, v: str) -> str:
        if "<" in v or ">" in v:
            raise ValueError("Name must not contain HTML")
        return v.strip()
```

**Checklist:**
- [ ] All user inputs validated with schema (Pydantic, marshmallow, etc.)
- [ ] No SQL string concatenation — ORM or parameterised queries only
- [ ] No `shell=True` with user-controlled input
- [ ] File paths sanitised — no directory traversal
- [ ] File uploads validated: size limit, MIME type, extension allowlist
- [ ] HTML/template output escaped — no raw user content rendered as HTML

---

## 5. API Security

```python
# Rate limiting — FastAPI + slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("10/minute")       # aggressive for auth endpoints
async def login(request: Request, body: LoginRequest):
    ...

@app.get("/search")
@limiter.limit("30/minute")
async def search(request: Request, q: str):
    ...
```

```python
# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
```

**Checklist:**
- [ ] Rate limiting on all public endpoints (stricter on auth)
- [ ] CORS configured for explicit allowed origins only (not `*`)
- [ ] Security headers set (HSTS, CSP, X-Frame-Options, etc.)
- [ ] API versioning — old versions deprecated, not silently broken
- [ ] Request body size limit configured at gateway and service
- [ ] GraphQL: introspection disabled in production
- [ ] GraphQL: query depth and complexity limits configured

---

## 6. Kubernetes Security

```yaml
# Pod Security — least privilege
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    fsGroup: 1001
  containers:
    - name: api
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
      # Writeable paths mounted explicitly
      volumeMounts:
        - name: tmp
          mountPath: /tmp
  volumes:
    - name: tmp
      emptyDir: {}
```

```yaml
# NetworkPolicy — default deny, explicit allow
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-netpol
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: database
      ports:
        - port: 5432
    - ports:
        - port: 53     # DNS
          protocol: UDP
```

**Checklist:**
- [ ] Containers run as non-root (`runAsNonRoot: true`)
- [ ] `allowPrivilegeEscalation: false`
- [ ] `readOnlyRootFilesystem: true` (mount writable paths explicitly)
- [ ] All capabilities dropped (`drop: ["ALL"]`)
- [ ] NetworkPolicy: default deny with explicit ingress/egress rules
- [ ] RBAC: ServiceAccount has only required permissions (no `cluster-admin`)
- [ ] Secrets not mounted as env vars on pods that don't need them
- [ ] Image scanning in CI (Trivy, Grype) — no critical CVEs in prod images
- [ ] Admission controller (OPA/Gatekeeper or Kyverno) enforcing pod security standards

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

### Zero Trust Principles

```yaml
# mTLS between services — no implicit trust on internal network
# (Istio / Linkerd service mesh example)
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: prod
spec:
  mtls:
    mode: STRICT   # reject plaintext — no exceptions
```

```yaml
# AuthorizationPolicy — explicit allow, deny by default
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: api-authz
  namespace: prod
spec:
  selector:
    matchLabels:
      app: api
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/prod/sa/frontend"]
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/api/*"]
```

```python
# Service-to-service auth — short-lived tokens, not long-lived API keys
# BAD: long-lived shared secret between services
headers = {"X-Service-Key": "static-secret-shared-forever"}

# GOOD: workload identity / SPIFFE / short-lived JWT
import google.auth.transport.requests
import google.oauth2.id_token

def get_service_token(audience: str) -> str:
    request = google.auth.transport.requests.Request()
    return google.oauth2.id_token.fetch_id_token(request, audience)
```

### Defense in Depth Layers

| Layer | Control | Verify |
|-------|---------|--------|
| Network | NetworkPolicy / firewall rules | Egress restricted to known destinations |
| Transport | mTLS between services | Plaintext internal traffic blocked |
| Application | Auth + authz on every request | No gateway-only auth assumptions |
| Data | Encryption at rest + in transit | KMS key rotation policy exists |
| Identity | Workload identity (SPIFFE/IRSA) | No long-lived static credentials |
| Observability | Audit logs, anomaly detection | Failed auth attempts alerted |
| Recovery | Incident response runbook | Blast radius limited by RBAC scope |

### Checklist: Defense in Depth
- [ ] **Layered controls** — auth enforced at gateway AND service layer (not gateway-only)
- [ ] **Blast radius scoped** — compromising one service cannot pivot to all services
- [ ] **Egress restricted** — services can only reach known, required destinations
- [ ] **Secrets have TTLs** — no eternal API keys; rotation automated
- [ ] **Audit logging** — all auth decisions logged and queryable
- [ ] **Alerting** — anomalous auth failure rates trigger on-call
- [ ] **Backups isolated** — backup storage not accessible from production workloads
- [ ] **Incident runbook exists** — clear steps for credential compromise, data breach

### Checklist: Zero Trust
- [ ] **Never trust network position** — internal services authenticate each other
- [ ] **mTLS enforced** between services (service mesh or manual cert management)
- [ ] **Workload identity** used instead of static credentials (SPIFFE, IRSA, Workload Identity)
- [ ] **Least privilege per workload** — ServiceAccounts scoped to minimum required
- [ ] **Device/client attestation** for sensitive operations (MFA, step-up auth)
- [ ] **Continuous verification** — tokens short-lived; re-auth required after expiry
- [ ] **Microsegmentation** — NetworkPolicy or service mesh policy limits lateral movement
- [ ] **No implicit trust for admin tooling** — kubectl, CI runners, deploy pipelines all use short-lived credentials

---



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
