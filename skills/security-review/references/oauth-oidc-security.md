## redirect_uri — Exact Match Only

RFC 9700 (BCP 240) requires exact string matching. Prefix, wildcard, and "starts-with" matching are
all bypassable (Authentik CVE-2024-52289: regex match bypassed for one-click account takeover).

```python
# BAD: prefix/wildcard match
if redirect_uri.startswith(client.registered_uri):
    ...

# GOOD: exact match against a registered allowlist
if redirect_uri not in client.registered_redirect_uris:
    raise InvalidRequestError("redirect_uri not registered")
```

## PKCE — Required for Every Client, Not Just Public Ones

```python
# GOOD: PKCE required regardless of client type, S256 only
if code_challenge_method != "S256":
    raise InvalidRequestError("PKCE with S256 required")
```

Implicit flow and Resource Owner Password Credentials are deprecated per RFC 9700 — flag either if
found in a new integration.

## Issuer Binding Is a Separate Check From Signature Verification

A token can pass signature verification and still belong to the wrong issuer in a multi-tenant
setup (n8n CVE-2026-59208: signature valid, issuer unchecked, cross-tenant auth).

```python
# BAD: signature checked, issuer not
payload = jwt.decode(token, key, algorithms=["RS256"])

# GOOD: issuer pinned explicitly
payload = jwt.decode(token, key, algorithms=["RS256"], issuer=expected_issuer)
if payload["iss"] != expected_issuer:
    raise UnauthorizedError("issuer mismatch")
```

## state / Mix-Up Attacks

- `state` is required and checked on every callback — its absence is login CSRF.
- Multi-authorization-server clients must echo and verify the `iss` parameter (RFC 9207) to prevent
  a mix-up attack — the client sent to the wrong authorization server.
- Account linking must match on `sub`, never on `email` — a mutable claim allows cross-IdP account
  takeover.

## CI/CD OIDC Federation Trust Policy

*Trigger: a GitHub Actions / GitLab CI workflow federates to a cloud role via OIDC.*

The trust policy's `sub`/`aud` condition must scope to the exact repo, branch, and workflow path —
not a wildcard. A condition like `repo:org/*:*` lets any fork or branch assume the role (the
"OH-MY-DC" pattern).

```json
// BAD
"StringLike": { "token.actions.githubusercontent.com:sub": "repo:org/*:*" }

// GOOD
"StringEquals": { "token.actions.githubusercontent.com:sub": "repo:org/app:ref:refs/heads/main" }
```

## Checklist

- [ ] `redirect_uri` matched by exact string, against a server-side allowlist
- [ ] PKCE (S256) required for every client type
- [ ] Implicit flow and ROPC not in use
- [ ] Token issuer verified explicitly, not assumed from a correct signature
- [ ] `state` required and checked on callback
- [ ] Multi-AS clients verify `iss` on the callback (RFC 9207)
- [ ] Account linking matches on `sub`, not `email`
- [ ] CI/CD OIDC trust policies scope `sub`/`aud` to an exact repo/branch/workflow, not a wildcard
- [ ] Token-exchange endpoints (RFC 8693) authenticate the client before issuing a new token
