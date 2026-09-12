# Data Classification, Minimisation, and Egress

Loaded at §4.8, after the data protection checklist. **Trigger:** the change adds, stores,
transmits, or newly exposes any field about a person or organisation, or sends data to any
destination outside this service.

§4.8 asks whether data is protected. This asks the prior question: **should we hold it at all,
and where does it go?** Data not collected cannot leak; a destination not enumerated cannot be
protected. Both become permanent the moment they ship.

---

## 1. Classification

Every new or newly-exposed field gets a class. **An unclassified field is a finding** — no
control can be applied to data nobody has classified.

| Class | Examples | Obliges |
|---|---|---|
| Public | Published docs | Integrity only |
| Internal | Aggregate metrics, non-sensitive config | Access control |
| Confidential | Customer business data, contracts, source | Encrypted at rest, access controlled and logged |
| Restricted | Credentials and keys, identifiable personal data, financial, health, biometric, government ID, precise location, minors' data | Encryption, retention limit, deletion path, access audit, breach notification |

Two commonly missed in a research environment: **human-subject data** under an IRB protocol, and
data received under a **DUA or export-control restriction**. Both are stricter than any platform
default — name the governing agreement, because it sets the bar, not the baseline.

Watch for reclassification by combination: a postcode, a birth date, and a job title are each
low-risk and jointly identifying.

## 2. Minimisation

- **Is each field needed?** Name the feature each restricted field serves. "It was in the
  payload" is how a system accumulates liability with no matching capability
- **Can it be avoided?** A hash instead of the value; a bucket instead of a precise figure; a
  provider token instead of a card number; last-4 instead of the full number; `is_over_18`
  instead of a birth date. Each substitution removes a class of future incident
- **Retention:** how long, and what deletes it? "Indefinitely" is legitimate only as a stated
  decision, not as the default outcome of nobody choosing
- **Copies inherit the class.** Does the field reach logs, metric labels, analytics, search
  indexes, caches, derived tables, warehouses, backups? These are routinely missed by the
  deletion flow §4.8 requires — which is how a completed deletion request leaves data in three
  places

## 3. Egress inventory

**This table is the deliverable.** An unenumerated destination is an unreviewed one.

| Destination | Data sent | Class | Purpose | Agreement |
|---|---|---|---|---|
| Payment provider | email, amount | Restricted | payment | DPA |
| Error reporter | stack + request context | ? ← check breadcrumbs and body capture |
| Telemetry collector | span attributes | ? ← check for IDs and values |
| LLM provider | prompt contents | ? ← most often unreviewed |

Check specifically:

- **Third-party SDKs and SaaS** — analytics, error reporting (Sentry breadcrumbs and request
  bodies are a classic unintended PII channel), **session replay** (records form field contents
  unless explicitly masked, including fields never submitted), support widgets, flag services, CDNs
- **LLM and ML providers** — what enters the prompt, whether retained, whether trainable on,
  whether a zero-retention agreement exists. Regulated or third-party data entering a vendor
  model is a privacy *and* an injection question (`vuln-classes.md` class 9)
- **Customer-configured webhooks and exports** — a user-supplied destination is an exfiltration
  channel shipped as a feature. Destination allow-listed? Payload minimised? Config change audited?
- **Residency** — does any destination cross a border the governing agreement, IRB protocol, or
  DUA prohibits? Sub-processors of your processors count
- Egress to a first-seen destination is also a detection signal (`detection-audit.md` §4)

## 4. Non-production data

- [ ] **Is production data copied into staging, dev, CI, notebooks, or a laptop?** If so it keeps
      production classification under a much weaker control set — no audit trail, wider access,
      longer retention, often no encryption. One of the most common real breach paths, and it
      appears in almost no threat model
- [ ] If masked or synthesised, is the masking **verified**? Partial masking leaving a join key
      intact re-identifies the dataset
- [ ] Can non-production reach production secrets, or a production replica?
- [ ] Do ad-hoc queries, support tools, and notebooks against production leave an audit trail
      naming the human who ran them? (`detection-audit.md` §1)

## 5. Subject rights and disclosure

- [ ] The deletion flow reaches **every** copy from §2 and every destination from §3 — third
      parties, backups, analytics included. Clearing only the primary table is non-compliant
      *and* believed to work, which is worse than a known gap
- [ ] Export, correction, and consent-withdrawal paths exist where the governing regime requires
- [ ] Data sharing is disclosed in the governing notice — privacy policy, consent form, IRB
      protocol, or DUA. A §3 destination absent from the notice is itself a finding

---

Unclassified fields, unenumerated destinations, and unreachable deletion paths are findings —
typically `medium`, rising to `high` where restricted data reaches a destination with no covering
agreement, since that disclosure has already happened rather than merely being possible.
