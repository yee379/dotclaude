## Origin / RP ID — Server Allowlist Only

Same failure pattern as OAuth `redirect_uri`: never reconstruct the expected origin from a request
header.

```python
# BAD: origin taken from a client-controlled header
expected_origin = request.headers.get("Origin")

# GOOD: origin compared against a fixed, server-side allowlist
if webauthn_response.origin not in ALLOWED_ORIGINS:
    raise UnauthorizedError("origin mismatch")
```

## UP vs. UV — Do Not Conflate Presence With Verification

- **UP (user presence):** a tap or click happened. Satisfied by physical interaction alone.
- **UV (user verification):** the user authenticated to the authenticator (PIN, biometric).

A check for UP alone where UV is required silently downgrades assurance — an attacker in physical
possession of an unlocked authenticator passes UP without ever proving identity. Request and verify
`userVerification: "required"` for any step-up or sensitive action.

## Registration Is a Sensitive Account Action

New-credential registration must require reauthentication of the existing session, not just a valid
cookie — otherwise an attacker with a hijacked session can add their own passkey as a persistent
backdoor.

## Account Recovery Is the Weakest Path

A password/SMS/email reset flow that can regain access without the passkey silently downgrades the
account below its apparent assurance level. Review the recovery flow with the same scrutiny as the
passkey flow itself — it is usually the actual attack surface, not the WebAuthn ceremony.

## No Silent Fallback on Ceremony Failure

```python
# BAD: falls back to a weaker method without the user asking
if webauthn_failed:
    return start_sms_otp_flow()

# GOOD: failure is reported; fallback requires an explicit user choice, logged
if webauthn_failed:
    raise AuthenticationError("passkey verification failed")
```

## Checklist

- [ ] Origin and RP ID compared against a fixed server-side allowlist, never read from a request header
- [ ] Challenge is >= 16 random bytes, single-use
- [ ] `userVerification: "required"` set for any sensitive or step-up action — UP alone is not enough
- [ ] Credential registration requires reauthentication of the current session
- [ ] No attestation requested unless the relying party has a specific reason to need it
- [ ] Account recovery flow reviewed for whether it bypasses the passkey's assurance level
- [ ] No silent fallback to a weaker method on ceremony failure
