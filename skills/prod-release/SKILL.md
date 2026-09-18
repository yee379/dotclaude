---
name: prod-release
description: Production release workflow — test and staging environment gates, pre-release checklist, Kubernetes promotion, smoke tests, feature flag rollout, monitoring validation, and rollback procedure.
license: MIT
compatibility: opencode
---

# Production Release

Promoting code from test through staging to production safely — gates, checklists, and a clear
rollback plan at every step. Runs after `/closeout-prd`; earlier skills validate plans, this one
ships them.

Use it for promoting a feature or fix to production, planning a significant release, setting up a
release process for a new service, writing an on-call runbook before a high-risk deploy, or
post-incident review of which gate was missed.

**Check for a project-local `deploy-*` skill first.** Convention: a project's real release
process — its actual gates, environments, and rollback commands — lives in a directory-scoped
skill named `deploy-*` inside that project's own `.claude/skills/`. It appears in the skill
listing with a path prefix. If the repo you're in has one, load and follow it instead — most
specific wins. This file is the generic fallback for repos with no project-local `deploy-*` skill.

```
feature branch → [1] test env (automated + smoke tests)
               → [2] staging (integration, QA sign-off, load test vs NFRs)
               → [3] pre-release checklist (all gates green)
               → [4] production deploy (canary or full)
               → [5] soak 15 min – 24 h by risk
               → [6] full rollout / flag enable
               → [7] post-release verification
```

---

## Gate 1: Test environment

```bash
pytest --tb=short -q               # Python
npm test -- --ci                   # Node
go test ./...                      # Go

curl -sf https://api-test.internal/healthz
curl -sf https://api-test.internal/readyz
pytest tests/integration/ -m "smoke"
```

- [ ] All unit and integration tests pass
- [ ] Health and readiness endpoints return 200
- [ ] No new errors in test logs, compared to baseline
- [ ] DB migrations ran successfully on the test DB

## Gate 2: Staging

```bash
make release ENV=staging IMAGE_TAG=$IMAGE_TAG
kubectl rollout status deployment/api -n staging
kubectl get pods -n staging -l app=api

curl -sf https://api-staging.example.com/healthz
curl -sf https://api-staging.example.com/readyz

# Load test for performance-sensitive changes — against staging, never prod
k6 run --vus 50 --duration 2m load-test.js   # check p95, error rate, no OOMKills
```

Key user flows, automated or manual: can a user log in? does the primary feature work end to end?
does a bad request return the right error?

- [ ] Deployment healthy — all pods Running
- [ ] Smoke tests pass; key user flows verified
- [ ] Load test meets NFR targets (if applicable)
- [ ] No unexpected errors in staging logs
- [ ] DB migration tested against the staging dataset
- [ ] Feature flags set correctly for staging

---

## Gate 3: Pre-release checklist

**Code & build**
- [ ] PR merged, all CI green on main
- [ ] Image digest/tag recorded: `$IMAGE_TAG`; previous stable tag recorded for rollback: `$PREV_TAG`
- [ ] No secrets committed
- [ ] Dependencies scanned (`pip-audit` / `npm audit`) — no critical CVEs

**Database**
- [ ] Migration is backward-compatible — the old app can run against the new schema
- [ ] Tested on a copy of production data (row counts, timing)
- [ ] Destructive changes (DROP, TRUNCATE) explicitly signed off
- [ ] Rollback migration written and tested

**Infrastructure**
- [ ] Manifests reviewed (resources, probes, PDB); `helm diff` run and unexpected changes reviewed
- [ ] **Drift check:** `kubectl diff -f deploy/prod/manifests/` — no unexplained live state
- [ ] Secrets updated in vault/external-secrets if needed; new env vars documented
- [ ] **No TLS cert or rotated secret expires within 7 days** — it would fail mid-soak

**Operations**
- [ ] **Dependency health pre-check** — every upstream (databases, caches, external APIs, queues)
      confirmed healthy *before* deploying. A degraded dependency at deploy time causes
      misattributed incidents
- [ ] **Metric baseline recorded** — error rate, p95 latency, RPS, pod count snapshotted
      immediately before deploy, stored in the task file or release notes. Everything in
      post-deploy verification compares against this
- [ ] Dashboard updated for new metrics/endpoints; alerts configured for error rate, latency, and
      any new SLOs
- [ ] On-call informed, especially for high-risk changes; runbook updated with new failure modes
- [ ] Rollback plan documented

**Communication**
- [ ] Stakeholders notified (user-visible change); maintenance window scheduled (if required)
- [ ] Feature flag ready for gradual rollout (if applicable)

---

## Deploy

```bash
make diff ENV=prod                              # 1. diff first — no surprises
make release ENV=prod IMAGE_TAG=$IMAGE_TAG      # 2. render, commit, deploy
kubectl rollout status deployment/api -n prod   # 3. verify immediately
kubectl get pods -n prod -l app=api
```

> Uses `make render` + `make deploy`, not `helm upgrade` directly. Full Makefile workflow:
> `/k8s-deploy`.

**Canary, for high-risk changes:** deploy `deploy-canary.yaml` (replicas 1, new tag) alongside
stable and route ~5% of traffic via Ingress or mesh weights. Watch error rate and latency for
15 min — stable → raise the weight; degraded → scale the canary to 0 immediately. Then promote:

```bash
kubectl set image deployment/api-stable api=$IMAGE_TAG -n prod
kubectl delete deployment api-canary -n prod
```

## Post-deploy verification

```bash
curl -sf https://api.example.com/healthz
curl -sf https://api.example.com/readyz
./scripts/smoke-test-prod.sh

kubectl get pods -n prod -l app=api
kubectl top pods -n prod -l app=api
kubectl logs -n prod -l app=api --since=5m | grep -E "ERROR|CRITICAL|Exception"
```

**Watch for 15–30 min, comparing every metric to the recorded baseline — not to an absolute
threshold.** A service at 0.8% error rate pre-deploy that jumps to 1.5% has regressed, but neither
value alone trips a naive "error rate > 1%" rule.

| Metric | Roll back if delta exceeds | Investigate if delta exceeds |
|---|---|---|
| HTTP 5xx error rate | > +1% above baseline | > +0.1% above baseline |
| p95 latency | > 2× baseline, sustained > 5 min | > 1.3× baseline |
| Pod restarts | > 2 in 10 min (new, not pre-existing) | Any new restarts |
| DB connection errors | Any not present at baseline | — |
| Memory usage | > +30% above baseline (OOMKill risk) | > +15% above baseline |
| RPS | Drop > 20% vs baseline (traffic not arriving) | Drop > 5% |

## Rollback

**Roll back when any "roll back if" column above is breached**, or on pod crashlooping, detected
data corruption, or a security incident triggered by the change.

```bash
# Preferred: git-based rollback via Makefile
git log --oneline deploy/prod/manifests/   # find last known-good SHA
make rollback ENV=prod ROLLBACK_SHA=<sha>

# Fallback: emergency only — reconcile git state afterwards
kubectl rollout undo deployment/api -n prod
kubectl rollout status deployment/api -n prod

# If the DB migration needs rolling back, run this BEFORE rolling back the app.
# Test the down migration in staging first.
alembic downgrade -1               # Python/Alembic
python manage.py migrate app 0023  # Django
```

Afterwards:
- [ ] Verify metrics return to baseline
- [ ] Write an incident summary: what broke, how it was detected, time to rollback
- [ ] File a ticket for the fix before re-attempting
- [ ] Update the pre-release checklist if a gate was missed

## Feature flag rollout

For gradual rollout without a canary:

```python
# LaunchDarkly / Unleash / homegrown — same pattern
def can_use_new_feature(user_id: str) -> bool:
    return feature_flags.is_enabled("new-upload-flow", user_context={"id": user_id})

# Stages: internal team (0.1%) → 5% → 25% → 100%, watching metrics at each
```

Naming: `<service>-<feature>-<date>`, e.g. `upload-new-resize-2026-03-18`. **Remove the flag
within one sprint of full rollout** — dead flags are a maintenance burden and a permanently
untested branch.

---

## Release notes

**Find where this repo already records releases — do not default to creating a root
`CHANGELOG.md` unasked.** In order:

1. **A root `CHANGELOG.md`** — almost always the right target. Append with `Edit` and an exact
   `old_string` match; **never `Write`, never regenerate an existing entry**. A rewritten history
   is worse than a missing one — if unsure whether content exists for this version, read the whole
   file first.
2. **A per-service equivalent** — some repos deliberately keep history elsewhere: a version-history
   table in a debug/runbook `SKILL.md`, a `## Deployment Log` in each task file, a changelog
   section in `docs/RUNBOOK.md`. If one exists and is being kept current, that **is** this repo's
   changelog — use it rather than creating a competitor. A test asserting the version table has a
   row for the current `VERSION` means this is enforced convention, not habit.
3. **Neither** — ask whether to create a root `CHANGELOG.md` or skip it this release. Don't decide
   silently either way: a missing changelog is a real gap, and creating one nobody asked for is
   scope creep on a release you were asked to ship.

Adapt the shape to whatever convention already exists — don't force this template onto a repo with
a terser one:

```markdown
## Release v1.4.2 — 2026-03-18

### Changes
- feat: user photo upload with automatic resizing
- fix: order status not updating on cancellation

### Migration
- `ALTER TABLE users ADD COLUMN photo_url TEXT` (backward-compatible, nullable)

### Rollback
- `make rollback ENV=prod ROLLBACK_SHA=<prev-sha>` reverts to v1.4.1
- No migration rollback needed (additive only)

### Monitoring
- New metric: `upload.duration_ms` — alert if p95 > 3000
- Dashboard: https://grafana.internal/d/uploads

### On-call notes
- If upload errors spike: check S3 bucket policy and CloudFront distribution
```

Write it in the **same commit** as the version bump — a version bumped without its changelog entry
is exactly the drift a later `git log -p` archaeology session has to reconstruct by hand.

## After a successful deployment

1. Task file (`todo/<number>-<slug>.md`): `**Status:**` → `🚀 Deployed`
2. `TODO.md`: status column → `🚀 Deployed`
3. **Confirm the changelog entry actually landed** — a separate check, not implied by steps 1–2.
   Task tracking and release history answer different questions ("what's the status of #NNN" vs
   "what shipped in v1.4.2"), so a task marked Deployed with no changelog row is a classic miss.

> `🚀 Deployed` is the terminal status for codebase tasks; `/prd-workflow` uses `🚀 Applied` for
> Kubernetes changes — code is deployed, manifests are applied. Check which workflow you are in.
