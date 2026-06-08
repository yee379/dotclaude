## Rate Limiting

Use slowapi (FastAPI). Apply aggressively to auth endpoints.

```python
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

## Security Headers Middleware

```python
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

## Checklist

- [ ] Rate limiting on all public endpoints (stricter on auth)
- [ ] CORS configured for explicit allowed origins only (not `*`)
- [ ] Security headers set (HSTS, CSP, X-Frame-Options, etc.)
- [ ] API versioning — old versions deprecated, not silently broken
- [ ] Request body size limit configured at gateway and service
- [ ] GraphQL: introspection disabled in production
- [ ] GraphQL: query depth and complexity limits configured
