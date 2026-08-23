# Precision rules for plans

These exist because a plan that disagrees with itself, or with the repo, generates review
amendments that look like findings but are self-inflicted. In one three-round board review, ~48 of
53 final-round amendments were this class; only ~5 were real design defects. Reviewers only get to
spend their budget on real defects once the precision defects stop consuming it.

Apply these **while writing**, and run the self-check before handing the plan to `/board-review`.

---

## 1. Never write a value you could derive

Every fact restated in a plan is a copy that goes stale, and reviewers correctly hunt them.

**Failure it prevents:** a hostname count that went 9 → 18 → 7 across three rounds, was wrong in
five places at once, and drove a requirement to demand the *opposite* of the ticket's purpose.
Also: a stale test count, a wrong environment count, and ~60 line-number citations of which several
had drifted.

- State **how to derive** a fact, not its value: the command, the endpoint, the accessor.
- Where a value is genuinely needed for reasoning, put it in **one** dated `## Measured facts`
  block with the exact command that produced it, and add a rule that no other site may re-quote it.
  Every downstream site references the block by name.
- Distinguish quantities that are easy to conflate, in a table, with one row each. If two numbers
  can be mistaken for each other, they *will* be.
- Prefer **symbol references** (`_normalize_host`, `_is_plausible`, `POST /policies/load`) over line
  numbers. Symbols survive edits; line numbers do not. Use line numbers only when the exact
  position matters, and expect to re-verify them.
- A count you cannot derive at implementation time is not evidence. Say so explicitly.

## 2. State each rule normatively in exactly one place

**Failure it prevents:** a rejection-reason taxonomy that existed in four places and disagreed in
two of them; a contract restated in a delivery slice using a form the contract itself had struck; a
module-design lead-in carrying a superseded version of the rule its own pseudocode got right.

- One section owns each rule. Name the rule so other sections can reference it by name.
- Add one line saying **which section wins** when prose and table disagree.
- When you revise a rule, grep for every site that restates it. If you cannot enumerate the sites,
  that is the signal it is stated in too many places.

## 3. Requirements must say *where*, not just *what*

**Failure it prevents:** a requirement that never pinned where in a function a new scan runs, so
the literal reading counted the wrong things. And a grammar that never mentioned whitespace
stripping while replacing a function that stripped — a silent allow→deny **authorization**
regression, i.e. a 403 for a live user, that survived three review rounds.

- Give the **insertion point**: function, and position relative to existing gates and guards.
- Give the **complete** transformation. If you are replacing an existing function, state every
  behaviour of the old one and whether the new one keeps it. Enumerate them; do not summarise.
- For any set of values, add a **"produced by"** column naming the code path that emits each
  member. A set whose members come from different paths is two sets wearing one name.

## 4. Derive slice placement from a stated invariant

**Failure it prevents:** the same misplacement caught three separate times by three reviewers
across two rounds — a requirement, then a doc criterion, then three edits inside another criterion,
each landing in a slice where its statement was not yet true.

- Write the invariant once, up front: **every artefact lands in the slice where its statement
  becomes true.**
- Then check every row against it before review. With the rule stated, the violations are
  self-evident; without it, each one has to be rediscovered.
- State the **build-order prerequisites** explicitly. "The rest may ship in any order" is almost
  always false — anything that consumes a new module depends on the slice that creates it.

## 5. Validate test specs against the fixtures they would actually run on

**Failure it prevents:** four planned test rows that a plausibility guard silently refuses, so the
store keeps the fixture and one row passes for the wrong reason. Plus a `parametrize` block that
would not collect, a missing fixture import, and a "tests that will flip" list that named a `def`
line and an `assert` line of the same test as two different tests.

- Pin each named test to its **fixture, file, and the guards it must pass**.
- **Run the tests you claim will break** and paste the real output. Predicting which tests flip is
  guessing about an executable fact.
- Record the real suite size from a real run, or do not state it.

## 6. Claim exactly the strength that holds

**Failure it prevents:** "monotonically stronger on every axis", "the allowlist is empty on a cold
store", "no host gets a redirect", "everything else may ship in any order" — each false as written,
each a guaranteed amendment. Reviewers are built to attack over-claims.

- Scope the claim. `new ⊆ old over the emitted authority set` survives; "strictly stronger" does not.
- Prefer a hedged-but-precise sentence over a crisp-but-false one.
- When a claim is only true under conditions, put the conditions in the sentence, not a footnote.

## 7. Record rejected alternatives with the reason each loses

**Failure it prevents:** three reviewers independently proposing three colliding designs for the
same question, because the plan recorded the decision without the reasoning that closed it.

- For each contested decision, list what was rejected **and the fact that kills it** — the import
  cycle, the unreachable branch, the measurement.
- A decision without its rejected alternatives will be re-litigated by the next reader.

## 8. Write byte-level content as escapes

**Failure it prevents:** a literal `K` standing in for U+212A KELVIN SIGN, surviving three rounds
in a payload corpus — a test that passes while testing nothing.

- Any non-ASCII payload is written `\uXXXX`, never as a glyph.
- Add a grep to the definition of done proving no literal glyphs remain.

## 9. Length is a defect generator

A plan padded with restatements, duplicate citations, and quoted-instead-of-referenced code has more
drift surface than one that says each thing once — and every extra copy is an amendment waiting to
happen. This is a duplication problem, not a length problem: a long plan that says everything exactly
once is fine; a short plan that restates a value in three places is not. Do not cut content to hit a
line-count target — cut restatements, stale quotes, and things better expressed as a repo reference.

- If a value, rule, or code block appears more than once, that is the defect — collapse it to one
  source of truth, however long or short the result is.
- Long plans are not more rigorous. They are harder to keep self-consistent, which is the property
  reviewers actually test — and that risk comes from duplication, not from page count.

---

## Self-check before `/board-review`

Run this and fix what it finds. Each line maps to a rule above.

- [ ] **Values:** every number in the plan is either in the dated `## Measured facts` block with its
      command, or is derived at implementation time. No number is transcribed between sections.
- [ ] **Conflatable quantities** are in one table, one row each, named distinctly.
- [ ] **Citations:** every `file:line` re-verified against the file *now*; symbol references used
      wherever the exact line does not matter.
- [ ] **Single-source:** each normative rule stated once; grep confirms no stale restatement.
- [ ] **Requirements:** each names its insertion point and the complete transformation; every set has
      a "produced by" column.
- [ ] **Replacement audit:** for every function being replaced, each existing behaviour is listed and
      explicitly kept or dropped.
- [ ] **Slices:** the placement invariant is stated, every artefact checked against it, build-order
      prerequisites named.
- [ ] **Tests:** named tests pinned to fixture + guards; the "will flip" list produced by *running*
      the suite; suite size from a real run.
- [ ] **Claims:** no universal claim ("always", "every axis", "strictly stronger", "any order")
      survives unscoped.
- [ ] **Alternatives:** each contested decision records what was rejected and the fact that kills it.
- [ ] **Escapes:** `grep -P` for the relevant codepoints returns nothing.
- [ ] **Duplication:** no value, rule, or code block is stated more than once anywhere in the plan.

Report the result to the user as a one-line count of what the sweep fixed. If it fixed nothing, say
so — that is a meaningful signal about the plan, not an absence of output.
