## XML Signature Wrapping (XSW)

Not legacy-only — CVE-2025-25291/25292 (ruby-saml) and CVE-2025-47949 (Samlify) are 2025, in
actively maintained libraries. The validator checks a legitimate signed assertion while business
logic reads an attacker-injected second assertion in the same document.

```python
# BAD: selects the signed element by tag name — wrapping-vulnerable
assertion = doc.getElementsByTagName("Assertion")[0]

# GOOD: select by absolute XPath, resolve the reference the signature itself points to
assertion = doc.xpath("/samlp:Response/saml:Assertion", namespaces=NS)[0]
```

## Validation Checklist Beyond "Signature Is Valid"

A cryptographically valid signature on *some* assertion in the document is not enough.

- `NotBefore` / `NotOnOrAfter` — reject outside the replay window
- `InResponseTo` — binds the response to the specific request that triggered it
- `Destination` — must match this SP's exact ACS URL, not just any registered SP
- `Audience` — must match this SP's own EntityID exactly

## Golden SAML

IdP signing-key compromise lets an attacker forge arbitrary, validly-signed assertions — bypassing
every IdP-side control including MFA. No input-validation fix exists for this; detection is
behavioral: new-application access, impossible travel, or an assertion signed by a key the IdP
reports as unused.

## IdP-Initiated SSO — RelayState Has No Inherent CSRF Protection

```python
# BAD: RelayState redirected to unconditionally
return redirect(relay_state)

# GOOD: RelayState checked against an allowlist of known post-login destinations
if relay_state not in ALLOWED_RELAY_TARGETS:
    relay_state = DEFAULT_LANDING_PAGE
return redirect(relay_state)
```

## Checklist

- [ ] Signed element selected by absolute XPath, never `getElementsByTagName`
- [ ] `NotBefore`/`NotOnOrAfter`, `InResponseTo`, `Destination`, and `Audience` all checked, not
      just the signature
- [ ] SAML library version checked against known XSW CVEs for that library
- [ ] IdP signing-key compromise has a named detection path (behavioral, not preventive)
- [ ] `RelayState` validated against an allowlist before redirect
