---
name: prod-release
description: Production release workflow — test and staging environment gates, pre-release checklist, Kubernetes promotion, smoke tests, feature flag rollout, monitoring validation, and rollback procedure.
license: MIT
compatibility: opencode
---

# Production Release

## Workflow position

```
/feature-plan            problem framing, requirements, rough system design, ADRs
      │
      ▼
/plan-architect-review   deep structural review: service boundaries, data ownership,
      │                  consistency models, failure domains, technology choices → ADR log
      ▼
/plan-eng-review         implementation gate: code quality, test coverage, performance,
      │                  edge cases → test plan artifact
      ▼
/prod-release          ← YOU ARE HERE: environment promotion, smoke tests, feature flag
                         rollout, monitoring validation, rollback procedure
```

Run after `/plan-eng-review` has passed and implementation is complete. This skill owns the promotion path from feature branch to production. Earlier skills validate plans — this skill ships them safely.

---

A disciplined process for promoting code from test through staging to production safely — with gates, checklists, and a clear rollback plan at every step.

## When to Use

- Promoting a feature or fix from staging to production
- Planning the release of a significant change
- Setting up a release process for a new service
- Writing a runbook for on-call before a high-risk deploy
- Post-incident: reviewing what release gate was missed

---

## Release Workflow

```
feature branch
     │
     ▼
[1] Test environment
     │  automated tests pass
     │  smoke tests pass
     ▼
[2] Staging environment
     │  integration tests pass
     │  QA sign-off (for user-facing changes)
     │  load test passes NFRs
     ▼
[3] Pre-release checklist
     │  all gates green
     ▼
[4] Production deploy (canary or full)
     │  health check passes
     │  error rate / latency baseline holds
     ▼
[5] Soak period (15min – 24h depending on risk)
     │  metrics stable
     ▼
[6] Full rollout / feature flag enable
     │
     ▼
[7] Post-release verification
```

---

## Gate 1: Test Environment

**Automated — must pass before staging promotion:**

```bash
# Run full test suite
pytest --tb=short -q               # Python
npm test -- --ci                   # Node
go test ./...                      # Go

# Smoke tests against deployed test service
curl -sf https://api-test.internal/healthz
curl -sf https://api-test.internal/readyz

# Integration tests
pytest tests/integration/ -m "smoke"
```

**Checklist:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Health and readiness endpoints return 200
- [ ] No new errors in test environment logs (compare to baseline)
- [ ] DB migrations ran successfully on test DB

---

## Gate 2: Staging Environment

**Deploy to staging:**

```bash
# Helm promotion
helm upgrade --install api ./charts/api \
  -n staging \
  -f charts/api/values-staging.yaml \
  --set image.tag=$IMAGE_TAG \
  --atomic --timeout 5m --wait

# Verify rollout
kubectl rollout status deployment/api -n staging
kubectl get pods -n staging -l app=api
```

**Run staging checks:**

```bash
# Smoke test
curl -sf https://api-staging.example.com/healthz
curl -sf https://api-staging.example.com/readyz

# Key user flows (automated or manual)
# - Auth: can a user log in?
# - Core action: does the primary feature work end-to-end?
# - Error path: does a bad request return the right error?
```

**Load test (for performance-sensitive changes):**

```bash
# k6 or locust — run against staging, not prod
k6 run --vus 50 --duration 2m load-test.js
# Check: p95 latency, error rate, no OOMKills
```

**Checklist:**
- [ ] Deployment is healthy (`kubectl get pods` — all Running)
- [ ] Smoke tests pass
- [ ] Key user flows verified
- [ ] Load test meets NFR targets (if applicable)
- [ ] No unexpected errors in staging logs
- [ ] DB migration tested against staging dataset
- [ ] Feature flags set correctly for staging

---

## Pre-Release Checklist

Complete this before every production deployment:

### Code & Build
- [ ] PR merged, all CI checks green on main
- [ ] Image digest / tag recorded: `$IMAGE_TAG`
- [ ] Previous stable image tag recorded for rollback: `$PREV_TAG`
- [ ] No secrets committed to the repository
- [ ] Dependencies scanned (`pip-audit` / `npm audit`) — no critical CVEs

### Database
- [ ] Migration is backward-compatible (old app can run against new schema)
- [ ] Migration tested on a copy of production data (row counts, timing)
- [ ] Destructive changes (DROP, TRUNCATE) explicitly signed off
- [ ] Rollback migration written and tested

### Infrastructure
- [ ] Kubernetes manifests reviewed (resources, probes, PDB)
- [ ] `helm diff` run — unexpected changes reviewed
- [ ] Secrets updated in vault/external-secrets if needed
- [ ] New environment variables documented

### Operations
- [ ] Monitoring dashboard updated for new metrics/endpoints
- [ ] Alerts configured for error rate, latency, and any new SLOs
- [ ] On-call informed of release (especially for high-risk changes)
- [ ] Runbook updated with new failure modes
- [ ] Rollback plan documented (see below)

### Communication
- [ ] Stakeholders notified (if user-visible change)
- [ ] Maintenance window scheduled (if required)
- [ ] Feature flag ready for gradual rollout (if applicable)

---

## Production Deploy

### Standard deploy (Helm)

```bash
# 1. Diff first — no surprises
helm diff upgrade api ./charts/api \
  -n prod \
  -f charts/api/values-prod.yaml \
  --set image.tag=$IMAGE_TAG

# 2. Deploy with atomic rollback on failure
helm upgrade --install api ./charts/api \
  -n prod \
  -f charts/api/values-prod.yaml \
  --set image.tag=$IMAGE_TAG \
  --atomic \
  --timeout 10m \
  --wait

# 3. Verify immediately
kubectl rollout status deployment/api -n prod
kubectl get pods -n prod -l app=api
```

### Canary deploy (for high-risk changes)

```yaml
# Deploy canary alongside stable
# Route 5% of traffic to canary using Ingress or service mesh weights

# Step 1: Deploy canary deployment
kubectl apply -f deploy-canary.yaml   # replicas: 1, image: NEW_TAG

# Step 2: Watch error rate + latency for 15 min
# If stable → increase canary weight
# If degraded → scale canary to 0 immediately

# Step 3: Promote fully
kubectl set image deployment/api-stable api=$IMAGE_TAG -n prod
kubectl delete deployment api-canary -n prod
```

---

## Post-Deploy Verification

Run immediately after deploying to production:

```bash
# Health checks
curl -sf https://api.example.com/healthz
curl -sf https://api.example.com/readyz

# Key smoke tests
./scripts/smoke-test-prod.sh

# Check pod health
kubectl get pods -n prod -l app=api
kubectl top pods -n prod -l app=api

# Check for new errors in logs (last 5 min)
kubectl logs -n prod -l app=api --since=5m | grep -E "ERROR|CRITICAL|Exception"
```

**Metrics to watch for 15–30 min after deploy:**

| Metric | Alert threshold | Action if breached |
|---|---|---|
| HTTP 5xx error rate | > 1% (was < 0.1%) | Rollback immediately |
| p95 latency | > 2× baseline | Rollback if sustained > 5 min |
| Pod restarts | > 2 restarts in 10 min | Rollback + investigate |
| DB connection errors | Any | Check migration, rollback if needed |
| Memory usage | > 80% of limit | Scale up or rollback if OOMKill risk |

---

## Rollback

**Decision: rollback if any of these are true:**
- Error rate > 1% and rising
- p95 latency > 2× baseline for > 5 min
- Pod crashlooping
- Data corruption detected
- Security incident triggered by the change

**Rollback procedure:**

```bash
# Option 1: Helm rollback (preferred — restores values and image)
helm rollback api -n prod           # to previous release
helm history api -n prod            # confirm which revision

# Option 2: Redeploy previous image
helm upgrade api ./charts/api \
  -n prod \
  -f charts/api/values-prod.yaml \
  --set image.tag=$PREV_TAG \
  --atomic --timeout 5m

# Option 3: kubectl rollout undo (image only, not values)
kubectl rollout undo deployment/api -n prod
kubectl rollout status deployment/api -n prod

# If DB migration needs rollback — run BEFORE rolling back app
# Test the down migration in staging first!
alembic downgrade -1               # Python/Alembic
python manage.py migrate app 0023  # Django
```

**After rollback:**
- [ ] Verify error rate returns to baseline
- [ ] Write incident summary: what broke, how detected, time to rollback
- [ ] File ticket for fix before re-attempting
- [ ] Update pre-release checklist if a gate was missed

---

## Feature Flag Rollout

For gradual rollout without a canary deploy:

```python
# LaunchDarkly / Unleash / homegrown — same pattern
def can_use_new_feature(user_id: str) -> bool:
    return feature_flags.is_enabled("new-upload-flow", user_context={"id": user_id})

# Rollout stages
# 1. Internal team only (0.1%)
# 2. 5% of users — watch metrics
# 3. 25% — watch metrics
# 4. 100% — retire flag
```

**Flag naming convention:**
```
<service>-<feature>-<date>
e.g.: upload-new-resize-2026-03-18
```

**Cleanup:** Remove feature flags within 1 sprint of full rollout. Dead flags are a maintenance burden.

---

## Release Notes Template

For each production release:

```markdown
## Release v1.4.2 — 2026-03-18

### Changes
- feat: user photo upload with automatic resizing
- fix: order status not updating on cancellation
- chore: upgrade PostgreSQL driver to 2.9.1

### Migration
- `ALTER TABLE users ADD COLUMN photo_url TEXT` (backward-compatible, nullable)

### Rollback
- `helm rollback api -n prod` reverts to v1.4.1
- No migration rollback needed (additive only)

### Monitoring
- New metric: `upload.duration_ms` — alert if p95 > 3000
- Dashboard: https://grafana.internal/d/uploads

### On-call notes
- If upload errors spike: check S3 bucket policy and CloudFront distribution
```
