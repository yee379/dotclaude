# Feasibility checks for plans

These exist because "is this buildable at all" is a cheap, mechanical question that a board reviewer
otherwise has to answer in Round 1 — a dependency that doesn't resolve, a symbol that doesn't exist, a
cluster resource that isn't there, a schema assumption that doesn't hold. Every one of those is a
`grep`, a package-registry lookup, or a `kubectl get` run once, here, instead of a reviewer's judgement
spent discovering it later.

This is **not** the precision sweep (`precision-rules.md`) — precision checks whether the plan agrees
with itself; feasibility checks whether the plan agrees with reality. Run both; they catch different
things.

Apply these at Phase 2.5, after Requirements/Capacity and before ADRs. Fix what fails, or record it
explicitly as an accepted unverified assumption — do not carry a silent ❌ into Phase 3.

---

## Codebase mode

### 1. Dependency exists & is healthy

**Failure it prevents:** a plan naming a library that's been deprecated, archived, or never existed
under that name — caught by `research` in Round 1 instead of here.

- For every new library/package named in Design or Requirements, confirm it resolves: `pip index
  versions <pkg>`, `npm view <pkg> version`, or check it's already pinned in `go.mod` /
  `requirements.txt` / `package.json`.
- Quick check only — if genuinely unfamiliar and the choice is contested, hand off to `/search-first`
  or `/research` rather than duplicating that skill's job here.

### 2. Referenced code exists

**Failure it prevents:** an FR's `Where` or a Module Design entry pointing at a file/symbol that
doesn't exist, isn't discovered until an engineer (or reviewer) opens the file.

- For every symbol/file cited in an FR's `Where` field or in Module Design, confirm it's present at
  that path now via `grep`/`rg`.

### 3. Test baseline is real

**Failure it prevents:** an AC naming a test command or framework that doesn't actually run in this
repo, or claiming a pass/fail count that was never measured.

- Run the test command the plan's ACs will rely on, once, and record the real pass/fail counts before
  any change is made.

### 4. Schema/data assumptions hold

**Failure it prevents:** a migration plan built on a column, type, or constraint that doesn't match
the schema as it exists today.

- If a migration is proposed, inspect the current schema/table now and confirm assumed
  columns/constraints/types match. Flag any mismatch.

### 5. External dependencies are reachable

**Failure it prevents:** a design that assumes an external API/service is reachable from this
environment, discovered false only at implementation time.

- Confirm reachability from docs/config, or record it explicitly as an unverified assumption if it
  can't be checked now.

---

## Platform mode

### 1. Capacity numbers are live, not assumed

**Failure it prevents:** a capacity table (Phase 2) populated from memory or a stale dashboard,
treated as ground truth by every reviewer downstream.

- Every row in the Phase 2 capacity table must be backed by the actual command run this session
  (`kubectl top`, a quota query) — not a remembered or estimated value.

### 2. Referenced resources exist

**Failure it prevents:** a plan assuming a Helm chart version, CRD, or StorageClass that isn't
actually available in this cluster.

- Confirm the Helm chart/repo at the stated version (`helm show chart`), any CRDs the plan depends on
  are installed (`kubectl get crd`), and any named StorageClass exists (`kubectl get storageclass`).

### 3. RBAC/NetworkPolicy baseline

**Failure it prevents:** a plan assuming a green-field namespace when a ServiceAccount, Role, or
NetworkPolicy it depends on (or conflicts with) already exists.

- Check whether a referenced ServiceAccount/Role/NetworkPolicy already exists before the plan assumes
  otherwise.

---

## Output

```
## Feasibility checks — run YYYY-MM-DD

| Check | Target | Command | Result |
|---|---|---|---|
| <check name> | <what it's checking> | <exact command run> | ✅ / ❌ |

Unresolved (❌ recorded as accepted assumption, not silently dropped):
- <item>: <why it couldn't be verified now, and what it's assumed to be>
```

This table doubles as groundwork for the `## Measured facts` block precision rule 1 asks for —
`board-review` Step 1.5a's ground-truth pass can re-verify these instead of re-deriving them from
scratch.

Report the result to the user in one line:

> "Feasibility checks: N of M passed live (K dependency, J resource, ...). L unresolved, recorded as
> assumptions."

If everything passed, say that too — it's a real signal, not an empty result.
