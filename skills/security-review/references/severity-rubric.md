# Severity Rubric and Evidence Standard

Load before writing any finding. Aggressive *hunting* and disciplined *reporting* are not in
tension — they are separated by this file. Hunt with maximum suspicion; report with an evidence
standard, so the blocking channel stays credible.

---

## Two channels, so nothing is dropped

| Channel | What goes here | Effect |
|---|---|---|
| `## Issues` | Findings where you can state the attack path concretely | Severity per the table below; blocking findings stop the board |
| `## Unverified Leads` | Suspicions you could not confirm — a hit you could not trace, a control you could not locate, a class you could not fully assess | Never blocking. Listed with what you tried and what would settle it |

**A suspicion is never discarded.** If you cannot promote it, demote it to a lead — do not delete
it, and do not inflate it into a blocking finding to be safe. The lead section is what makes
aggressive hunting cheap: you can chase 40 greps and report the 6 you confirmed plus the 9 you
could not rule out.

---

## Severity

Severity is `impact × reachability`. State both, or the severity is unjustified.

| Severity | Definition | Requires |
|---|---|---|
| `blocking` | Reachable by an untrusted or lower-privileged caller, and leads to auth bypass, data disclosure across a trust boundary, code execution, or credential compromise | The request path from an untrusted entrypoint to the flaw, named step by step |
| `high` | Same impact, but reachability depends on a precondition (an authenticated account, a specific role, a race, a non-default config) | The precondition stated explicitly |
| `medium` | Weakens a control without directly breaching it — missing defence in depth, a control present but bypassable in a narrower case, information disclosure without direct impact | What the control would have prevented |
| `low` | Hardening, hygiene, or a deviation from policy with no demonstrable attack path | Why it is worth the reader's time |

**Ambiguity resolves upward, once.** If you cannot decide between two adjacent severities, take
the higher one and say why it was ambiguous. Do not escalate a `medium` to `blocking` on a
two-step chain of assumptions — that is what `## Unverified Leads` is for.

**A missing control is a finding, not a question.** If the checklist item is "ownership check on
all user-data endpoints" and you cannot find the check, the finding is "no ownership check found
at `handlers/orders.py:88`", severity per the table — not "please confirm whether ownership is
checked". The user can dismiss a finding cheaply; they cannot act on a question they did not
know to ask.

---

## Evidence standard

Every finding in `## Issues` carries:

1. **Location** — `file:line`. A finding without a location is a lead.
2. **Attack path** — who calls what, in order, from an entrypoint you enumerated in Step 1.
3. **Why the existing controls do not stop it** — name the control you checked and how it is
   bypassed or absent. This is the step that kills false positives.
4. **The fix**, concretely. Not "validate input" — which validation, where, allow-listing what.

For `blocking` and `high`, add:

5. **Proof sketch** — the shape of the request or payload that exercises it (method, path, the
   field that carries it, the value class). Enough that a reader can reproduce it; not a working
   weaponised exploit.

If you cannot produce items 1–3, it is a lead. Say so and move on — do not pad `## Issues`.

---

## Ticking a checklist box

A box may be ticked **only** with a citation showing the control exists:

```
- [x] Ownership checks on all user-data endpoints — verified: deps.py:34 `require_owner`
      applied to all 7 routes in routers/orders.py
- [ ] Rate limiting on auth endpoints — NOT FOUND. Searched middleware/, main.py,
      ingress annotations. → finding SR-04
```

"Looks fine", "appears correct", and a bare `[x]` are not evidence. **Absence of evidence is a
finding, not a pass** — an unverifiable control is reported as unverified, with what you searched.

---

## The PASS gate

You may not report `PASS` unless all of the following are true, and the summary states them:

- Every entrypoint enumerated in Step 1 has been traced to an authorisation decision.
- Every hunt table in `hunt-patterns.md` was run, or its omission justified against the code.
- Every applicable class in `vuln-classes.md` was answered.
- Every ticked box carries a citation.

`PASS` means "I attacked this and these specific attempts failed". If it means "I read it and
nothing jumped out", the status is `PASS WITH WARNINGS` and the warning is the shallow coverage.
Say which it was.
