---
name: code-review
description: Structured backend and DevOps code review covering correctness, security, performance, database safety, Kubernetes manifests, GraphQL resolvers, Python quality, and test coverage gaps.
license: MIT
compatibility: opencode
---

# Code Review

Systematic review for backend services, APIs, infrastructure code, and Kubernetes workloads. Use
when reviewing a PR before merge, auditing a diff before staging or production, doing a targeted
security or performance pass, or checking manifests before deployment.

## Step 1 — Understand intent

Before reading code: what is this change supposed to do (PR description, commits, linked
tickets)? What is the blast radius (services affected, data migrations, API changes)? What
environment does it land in first?

## Step 2 — Two passes

**Pass 1 blocks the PR:** correctness & logic · security · data safety · races & concurrency.
**Pass 2 is informational:** performance · error handling · Kubernetes · GraphQL · test coverage ·
code quality.

---

## Pass 1: Critical

### 1. Correctness & logic

Does the code do what the description says? Are empty collections, `None`, zero, and negatives
handled? Off-by-one in loops, pagination, slicing? Does every `if` have the right `else`? Are new
enum/status values handled **everywhere** they are switched on?

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

Hardcoded secrets in code or config? User input reaching SQL, file paths, shell commands, or
`eval`? Authentication on every protected endpoint? Authorisation — can user A reach user B's
resources? PII or tokens in logs? CORS, rate limiting, and security headers configured?

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

For anything beyond this — attack surface enumeration, the authorisation model, injection sinks,
supply chain — use `/security-review`.

### 3. Data safety

Are migrations backward-compatible — can the old app still run during rollout? Any `DROP`,
`TRUNCATE`, or `DELETE` without `WHERE`, and is it intentional? New `NOT NULL` columns without
defaults on populated tables? Index creation using `CONCURRENTLY`? Bulk updates batched to avoid
long transactions?

```sql
-- BAD: locks entire table during migration
ALTER TABLE orders ADD COLUMN notes TEXT NOT NULL;

-- GOOD: backward-compatible sequence
ALTER TABLE orders ADD COLUMN notes TEXT;                    -- deploy
UPDATE orders SET notes = '' WHERE notes IS NULL;            -- backfill
ALTER TABLE orders ALTER COLUMN notes SET NOT NULL;          -- later

-- BAD: blocks table          -- GOOD: non-blocking
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status);
```

### 4. Races & concurrency

Check-then-act without locking (TOCTOU)? Optimistic locking needed for concurrent updates? Async
results checked before use? Shared mutable state across tasks or threads?

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

N+1 queries — related records fetched in a loop? Missing indexes on `WHERE`/`JOIN`/`ORDER BY`
columns? Unbounded queries on large tables? Synchronous I/O on an async event loop? Expensive
per-request computation that could be cached?

```python
# BAD: N+1
orders = await Order.all()
for order in orders:
    user = await User.get(order.user_id)  # N queries

# GOOD: batch fetch
orders = await Order.all().prefetch_related("user")
```

### 6. Error handling

Exceptions caught at the right level — not too broad, not swallowed? Error responses free of
stack traces and SQL? Retries with backoff for transient failures? Partial batch failures handled?

```python
# BAD: swallows everything
try:
    result = process()
except Exception:
    pass

# BAD: exposes internals
except Exception as e:
    return {"error": str(e), "traceback": traceback.format_exc()}

# GOOD: handle specifically, log internally, return safe message
except ValidationError as e:
    raise HTTPException(400, detail=e.user_message)
except Exception:
    logger.exception("Unexpected error processing request")
    raise HTTPException(500, detail="Internal server error")
```

### 7. Kubernetes / infrastructure

Image tag pinned (not `:latest`)? Resource requests and limits set? Liveness and readiness probes?
Secrets from vault/external-secrets rather than the manifest? `PodDisruptionBudget` for critical
services? `terminationGracePeriodSeconds` covering request drain? ServiceAccount least-privilege?
Network policy egress rules updated?

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

DataLoaders for related fields, or N+1 in resolvers? Mutations returning errors in the payload
rather than throwing? Auth checks inside resolvers, not only at the gateway? New list fields
paginated? Subscription topics namespaced per resource?

### 9. Test coverage

Are new code paths exercised? Both happy path **and** error/edge cases? Integration tests for new
endpoints? Mocks realistic against the actual interface? Any test asserting only "it doesn't
throw" or "it renders" — is it meaningful?

### 10. Code quality

Dead code introduced (unreachable branches, unused imports, commented-out blocks)? Magic numbers
or strings without named constants? Functions over ~50 lines that could decompose? Naming
consistent with the surrounding codebase? Comments explaining *why*, not *what*?

---

## Output

```
[SEVERITY] file:line — Problem description
Fix: Specific recommended fix
```

`[CRITICAL]` must fix before merge (correctness, security, data safety) · `[WARNING]` should fix,
discuss to defer · `[INFO]` worth noting, can be follow-up.

```
Review: N issues — X critical, Y warnings, Z informational
```

## Merge gate

Before approving any PR touching production paths, confirm the Pass 1 sections were walked and:

- [ ] No hardcoded secrets; all SQL parameterised
- [ ] Auth + authz on protected endpoints
- [ ] Migrations backward-compatible; no unbounded queries on large tables
- [ ] Enum/status changes handled exhaustively
- [ ] Error responses don't leak internals
- [ ] New manifests have resources + probes
- [ ] Tests cover new paths, happy and error
