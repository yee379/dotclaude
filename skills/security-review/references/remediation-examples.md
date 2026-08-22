# Remediation Examples — Secrets and Logging

Load when writing the fix for a secrets or data-protection finding. These are the "what good
looks like" shapes to point the author at; the detection patterns live in `hunt-patterns.md`.

## Secrets

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

**If a secret was ever committed, the fix is rotation.** Removing it from the working tree, or
even rewriting history, does not un-leak a value that was pushed. Say so in the finding.

## Logging

```python
# BAD — sensitive data in log output
logger.info(f"User login: email={email}, password={password}")
logger.debug(f"Payment: card={card_number}, cvv={cvv}")

# GOOD — identifiers and non-sensitive attributes only
logger.info("User login attempt", extra={"user_id": user_id, "email_domain": email.split("@")[1]})
logger.info("Payment initiated", extra={"user_id": user_id, "amount": amount, "currency": currency})

# Masking PII in error reports
def mask_email(email: str) -> str:
    local, domain = email.split("@")
    return f"{local[:2]}***@{domain}"
```

Two further rules that the examples above do not show:

- **Strip newlines from any user-controlled value before logging it** — otherwise an attacker
  forges log entries and defeats the audit trail.
- **Structured fields, not f-strings.** `extra={}` keeps values out of the message template,
  which makes redaction at the aggregator possible.
