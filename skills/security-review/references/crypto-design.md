# Cryptographic Design

Loaded at §4.12. **Trigger:** the change encrypts or decrypts, signs or verifies, hashes a
password, generates a token/secret/identifier, or introduces a key.

`hunt-patterns.md` catches bad **primitives** — MD5, ECB, `Math.random`. This is the layer above:
correct primitives assembled wrongly, which is the normal failure. AES-256 with a reused nonce,
or a perfect signature check run after parsing, provides no security while passing every
primitive-level grep.

---

## 1. Do not build it

- **No custom protocol or construction** — not "encrypt then append a SHA-256", not a hand-rolled
  token format, not a bespoke key exchange. Use libsodium, `cryptography`'s `Fernet`/`AESGCM`, or
  a platform KMS. A bespoke construction is a `high` finding on its own: nobody in this review,
  including you, can verify it
- **Encryption without authentication is a finding.** AES-CBC or CTR without a MAC is malleable;
  where an error distinguishes bad padding from bad content it is a decryption oracle. Use AEAD:
  AES-GCM, AES-SIV, ChaCha20-Poly1305
- Encrypt-then-MAC, never MAC-then-encrypt, if a composition is unavoidable

## 2. Randomness

- [ ] `secrets` / `crypto.randomBytes` / `os.urandom` — never `random`, `Math.random`, a PID, or
      a timestamp — for every session ID, token, reset code, invite code, nonce, salt, API key
- [ ] **≥ 128 bits of entropy** for anything guessable in bulk
- [ ] UUIDv4 is acceptable as unguessable; **UUIDv1 and v7 embed a timestamp** and are partially
      predictable — never a secret or reset token
- [ ] No token derived from user data (email hash, `user_id` + salt) — guessable by anyone who
      knows the input

## 3. Nonce and IV discipline

**Nonce reuse under the same key destroys GCM and CTR entirely** — confidentiality and
authenticity both. The most common way a correct algorithm choice fails.

- [ ] How is uniqueness guaranteed — random 96-bit per message, or a counter with **durable**
      state? An in-memory counter repeats after every pod restart
- [ ] Nonce/IV stored or transmitted with the ciphertext — not secret, but must be unique
- [ ] Deterministic encryption used for searchability **leaks equality** — identical plaintext
      gives identical ciphertext. Acceptable, and stated?

## 4. Key lifecycle

Always the missing part. For every key:

- **Generation** — where, by what, with what entropy
- **Storage** — KMS, HSM, or Vault. Not the repository, not a ConfigMap; an environment variable
  only where nothing better exists (it appears in crash dumps and child processes)
- **Access** — which workload identity may use it, and can that identity **export** the key or
  only request operations? Non-exportable is a materially different blast radius
- **Rotation** — procedure, cadence, and the question that decides whether rotation is possible
  at all: **can data encrypted under the old key still be read?**

  Envelope encryption (per-record data key wrapped by a rotatable master key) makes rotation a
  metadata operation. Encrypting everything directly under one long-lived key makes rotation a
  full re-encryption project, which is why it never happens. If the design is the latter, the
  finding is "key rotation is not operationally possible", not "cadence undefined"
- **Key ID stored with the ciphertext**, so a rotated or compromised key can be identified and
  the affected data scoped
- **Compromise response** — the named procedure. Unnamed means non-existent
- **Separation** — distinct keys per environment and per purpose. A staging key that decrypts
  production data makes staging a production system

## 5. Passwords and key derivation

- [ ] Argon2id (preferred), scrypt, or bcrypt. A plain or fast hash on a password column is
      `blocking`, not partial credit — SHA-256 with a salt included
- [ ] Work factor stated, tuned to current hardware, with a plan to raise it and re-hash on login
- [ ] Per-user salt — automatic in the bcrypt/argon2 formats; verify the format is actually used
- [ ] bcrypt's 72-byte input limit handled explicitly, not silently truncating a passphrase
- [ ] A separate KDF (HKDF/Argon2) for deriving keys from a password
- [ ] Pepper, if used, stored separately from the database

## 6. Verification order and comparison

- [ ] **Verify before parse.** A signature checked *after* deserialising means the parser already
      processed attacker input and is now the attack surface. Webhook HMACs are computed over the
      **raw** body before JSON parsing (`hunt-patterns.md`)
- [ ] Constant-time comparison for every MAC, token, signature, secret
      (`hmac.compare_digest`, `crypto.timingSafeEqual`)
- [ ] Algorithm **allow-listed explicitly** — `alg` is attacker-controlled
      (`jwt-authentication.md`)
- [ ] Verification key selected by a **trusted mapping**, not by a `kid`/`jku`/`x5u` the token
      supplies. A `kid` that becomes a file path or URL is key confusion *and* SSRF
- [ ] Expiry, issuer, audience, not-before all validated — not only the signature. A valid
      signature on a token minted for a different audience is a cross-service bypass

## 7. Transport

- [ ] Verification never disabled (greps in `hunt-patterns.md`); TLS ≥ 1.2
- [ ] Pinning only where rotation is operationally solved, or it is an outage waiting
- [ ] **Certificate and key expiry monitored** — the most common self-inflicted outage here. Who
      is alerted, how many days ahead?
- [ ] Service-to-service mTLS and workload identity are `zero-trust.md` and
      `/platform-security-review`

---

Every ticked box needs a `file:line`. "Uses AES-GCM" without showing where the nonce comes from
is `## Unverified Leads`, not a verified control.
