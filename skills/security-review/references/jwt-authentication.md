## JWT Verification

Verify signature AND claims explicitly. Never use `algorithms=["*"]`.

```python
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
```

## Secure Cookie Storage

Store tokens in httpOnly cookies — not localStorage (XSS safe).

```python
response.set_cookie(
    key="session",
    value=token,
    httponly=True,
    secure=True,           # HTTPS only
    samesite="strict",     # CSRF protection
    max_age=3600,
)
```

## Checklist

- [ ] JWT algorithm explicitly specified (not `["*"]`)
- [ ] Token expiry enforced
- [ ] Tokens stored in httpOnly, Secure, SameSite=Strict cookies
- [ ] Refresh token rotation implemented
- [ ] Brute force protection on login endpoint (rate limiting + lockout)
- [ ] Password hashing with bcrypt/argon2 (min cost factor 12)
- [ ] No sensitive data in JWT payload (only user ID + role)
