---
name: code-review
description: Structured backend and DevOps code review covering correctness, security, performance, database safety, Kubernetes manifests, GraphQL resolvers, Python quality, and test coverage gaps.
license: MIT
compatibility: opencode
---

# Code Review

A systematic review process for backend services, APIs, infrastructure code, and Kubernetes workloads. Use this when asked to review a PR, diff, or piece of code.

## When to Use

- Reviewing a pull request before merge
- Auditing a diff before promoting to staging or production
- Performing a targeted security or performance review
- Checking infrastructure / Kubernetes manifests before deployment

---

## Review Process

### Step 1 — Understand intent

Before reading code, establish:
- What is this change supposed to do? (PR description, commit messages, linked tickets)
- What is the blast radius? (number of services affected, data migrations, API changes)
- What environment will this first land in? (feature branch → test → staging → prod)

### Step 2 — Two-pass review

**Pass 1 — Critical (block the PR)**
1. Correctness & Logic
2. Security
3. Data Safety (DB migrations, destructive queries)
4. Race Conditions & Concurrency

**Pass 2 — Informational (flag but don't block)**
5. Performance
6. Error Handling
7. Kubernetes / Infrastructure
8. GraphQL
9. Test Coverage
10. Code Quality & Maintainability

---

## Pass 1: Critical

### 1. Correctness & Logic

- Does the code actually do what the description says?
- Are all edge cases handled: empty collections, null/None, zero, negative numbers?
- Off-by-one errors in loops, pagination, index slicing?
- Are conditionals complete — does every `if` have the right `else`?
- Enum / status values — are all new values handled everywhere they're switched on?

```python
# BAD: new enum value not handled
def handle_status(status: OrderStatus):
    if status == OrderStatus.PENDING:
        return queue_order()
    elif status == OrderStatus.SHIPPED:
        return notify_customer()
    # MISSING: CANCELLED, RETURNED — silent no-op

# GOOD: explicit exhaustive handling
def handle_status(status: OrderStatus):
    match status:
        case OrderStatus.PENDING: return queue_order()
        case OrderStatus.SHIPPED: return notify_customer()
        case OrderStatus.CANCELLED: return cancel_order()
        case _: raise ValueError(f"Unhandled status: {status}")
```

### 2. Security

- Hardcoded secrets, API keys, or passwords in code or config files?
- User input passed directly to SQL queries (injection risk)?
- User input used in file paths, shell commands, or eval?
- Authentication checks present on all protected endpoints?
- Authorization — can user A access user B's resources?
- Sensitive data (PII, tokens) written to logs?
- CORS, rate limiting, and security headers configured?

```python
# BAD: SQL injection
query = f"SELECT * FROM users WHERE email = '{email}'"

# GOOD: parameterised
query = "SELECT * FROM users WHERE email = $1", [email]

# BAD: path traversal
path = f"/data/uploads/{user_input}"

# GOOD: sanitise and constrain
path = base_dir / Path(user_input).name  # strip directory components
assert path.parent == base_dir           # confirm still inside base
```

### 3. Data Safety

- Migrations: are they backward-compatible? Can the old app still run during rollout?
- Destructive operations: `DROP`, `TRUNCATE`, `DELETE` without `WHERE` — intentional?
- New `NOT NULL` columns without defaults on tables with existing rows?
- Index creation — does it use `CONCURRENTLY` to avoid table locks in production?
- Bulk updates/deletes — are they batched to avoid long-running transactions?

```sql
-- BAD: locks entire table during migration
ALTER TABLE orders ADD COLUMN notes TEXT NOT NULL;

-- GOOD: backward-compatible migration sequence
-- Step 1 (deploy): add nullable column
ALTER TABLE orders ADD COLUMN notes TEXT;
-- Step 2 (after app deployed): backfill
UPDATE orders SET notes = '' WHERE notes IS NULL;
-- Step 3 (later): add constraint
ALTER TABLE orders ALTER COLUMN notes SET NOT NULL;

-- BAD: blocks table
CREATE INDEX idx_orders_status ON orders(status);

-- GOOD: non-blocking
CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status);
```

### 4. Race Conditions & Concurrency

- Check-then-act patterns without locking (TOCTOU)?
- Optimistic locking needed for concurrent updates?
- Async operations — are results checked before use?
- Shared mutable state across async tasks or threads?

```python
# BAD: TOCTOU race
async def transfer(from_id, to_id, amount):
    balance = await get_balance(from_id)
    if balance >= amount:          # another request can run here
        await debit(from_id, amount)
        await credit(to_id, amount)

# GOOD: atomic update with condition
async def transfer(from_id, to_id, amount):
    updated = await db.execute(
        "UPDATE accounts SET balance = balance - $1 "
        "WHERE id = $2 AND balance >= $1 RETURNING id",
        amount, from_id
    )
    if not updated:
        raise InsufficientFundsError()
    await credit(to_id, amount)
```

---

## Pass 2: Informational

### 5. Performance

- N+1 queries: are related records fetched in loops?
- Missing database indexes on columns used in `WHERE`, `JOIN`, or `ORDER BY`?
- Unbounded queries — large tables queried without `LIMIT`?
- Synchronous I/O blocking an async event loop?
- Expensive computations on every request that could be cached?

```python
# BAD: N+1
orders = await Order.all()
for order in orders:
    user = await User.get(order.user_id)  # N queries

# GOOD: batch fetch
orders = await Order.all().prefetch_related("user")
# or use DataLoader equivalent
```

### 6. Error Handling

- Are exceptions caught at the right level (not too broad, not swallowed)?
- Do error responses avoid leaking internal details (stack traces, SQL errors)?
- Are retries implemented with backoff for transient failures?
- Are partial failures handled (e.g., one item in a batch fails)?

```python
# BAD: swallows all errors silently
try:
    result = process()
except Exception:
    pass

# BAD: exposes internal detail
except Exception as e:
    return {"error": str(e), "traceback": traceback.format_exc()}

# GOOD: handle specifically, log internally, return safe message
except ValidationError as e:
    raise HTTPException(400, detail=e.user_message)
except Exception as e:
    logger.exception("Unexpected error processing request")
    raise HTTPException(500, detail="Internal server error")
```

### 7. Kubernetes / Infrastructure

- Image tag pinned (not `:latest`)?
- Resource requests and limits set?
- Liveness and readiness probes configured?
- Secrets sourced from vault/external-secrets, not hardcoded in manifests?
- `PodDisruptionBudget` present for critical services?
- `terminationGracePeriodSeconds` accounts for request drain time?
- RBAC: does the ServiceAccount have least-privilege permissions?
- Network policies: does this service need egress rules updated?

```yaml
# BAD
image: myapp:latest
# no resources, no probes, no PDB

# GOOD
image: myapp:1.4.2
resources:
  requests: { cpu: 100m, memory: 128Mi }
  limits: { cpu: 500m, memory: 512Mi }
readinessProbe:
  httpGet: { path: /readyz, port: 8080 }
  initialDelaySeconds: 5
  periodSeconds: 10
```

### 8. GraphQL

- N+1 in resolvers — are DataLoaders used for related fields?
- Mutations return errors in payload, not thrown exceptions?
- Auth checks inside resolvers, not only at the gateway?
- New list fields — are they paginated?
- Subscriptions — is topic namespaced per resource to prevent leaks?

### 9. Test Coverage

- Are new code paths exercised by tests?
- Do tests cover both happy path AND error/edge cases?
- Are integration tests present for new API endpoints?
- Are mocks realistic — do they match the actual interface?
- Tests that only assert "it doesn't throw" or "it renders" — are they meaningful?

### 10. Code Quality

- Dead code introduced (unreachable branches, unused imports, commented-out code)?
- Magic numbers or strings without named constants?
- Functions longer than ~50 lines — can they be decomposed?
- Consistent naming with the surrounding codebase?
- Comments that explain *why*, not just *what*?

---

## Output Format

For each finding:

```
[SEVERITY] file:line — Problem description
Fix: Specific recommended fix
```

Severity levels:
- `[CRITICAL]` — Must fix before merge (correctness, security, data safety)
- `[WARNING]` — Should fix; discuss if there's a reason to defer
- `[INFO]` — Worth noting; low risk, can be follow-up

Summary header:

```
Review: N issues — X critical, Y warnings, Z informational
```

---

## Review Checklist (quick reference)

**Before approving any PR that touches production paths:**

- [ ] No hardcoded secrets
- [ ] All SQL queries parameterised
- [ ] Auth + authz checks on protected endpoints
- [ ] DB migrations backward-compatible
- [ ] No unbounded queries on large tables
- [ ] N+1 queries addressed
- [ ] Error responses don't leak internals
- [ ] New Kubernetes manifests have resources + probes
- [ ] Tests cover new code paths (happy + error)
- [ ] Enum/status changes handled exhaustively
