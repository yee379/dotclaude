# Test Adequacy Rubric — Platform Changes

Load during Step 6 of `/platform-eng-review` to judge whether a plan's verification is
adequate, and to decide blocking vs warning. The fill-in template lives separately in
`references/test-plan-template.md`.

## 1. Automated vs manual — the baseline rule

**Automated tests are the bar. Manual verification is not a substitute.**

| Test type | Must be automated? | Rationale |
|---|---|---|
| Regression tests | ✅ Yes — must run in CI on every future deploy | Manual regression erodes immediately |
| Positive feature tests | ✅ Yes — must run in CI | Proves the feature works repeatably, not just on the day |
| Negative / security tests | ✅ Yes — must run in CI | A security control with no automated test is untested in practice |
| Smoke tests (post-deploy) | ✅ Yes — must be a script, not manual curl + eyeball | Must gate the rollout, not follow it |
| Alert firing verification | ⚠️ One-time manual acceptable | Synthetic failure is hard to automate; document the result |

"I will check it" is not a test plan.

## 2. Minimum coverage standard — per change type

| Change type | Required test coverage |
|---|---|
| New feature / new service | ✅ Positive test per new capability<br>✅ Negative test if any access control is involved<br>✅ Smoke test post-deploy<br>✅ Regression suite still passes |
| Configuration change (routing, values, flags) | ✅ Positive test: intended behaviour still works<br>✅ Regression suite still passes |
| Security control (NetworkPolicy, ipAllowList, RBAC, JWT gate) | ✅ Negative test: blocked traffic/request returns expected rejection<br>✅ Positive test: permitted traffic/request still works<br>✅ Both must be automated |
| Infrastructure change (resource tuning, HPA, probes) | ✅ Smoke test: service responds after apply<br>✅ Regression suite still passes |
| Rollback / restore | ✅ Rollback tested in staging: previous version restores cleanly |

A plan that lists fewer tests than its change type requires is **incomplete**.

## 3. Assessing the plan's existing verification steps

| Dimension | The question | Example of adequate |
|---|---|---|
| Negative path | Do the controls actually block what they should? | ipAllowList: external request to a blocked path returns 403. NetworkPolicy: denied pod-to-pod traffic is actually blocked |
| Positive path | Does legitimate traffic still work after the change? | Routing change: a valid request reaches the backend. JWT gate: a valid token returns 200 — not only that an invalid one returns 401 |
| New feature | Does the new capability provably work? | At least one automated positive test per capability. "It deployed successfully" is not evidence |
| Regression | Which existing suites must still pass? | Named suites listed as a required DoD gate **and** wired into CI for future deploys |
| Smoke | Is it a script, not a person? | `./test/smoke-test.sh` asserting specific responses. "I curled it and it looked fine" is not a smoke test |
| Timing | Do tests run immediately after apply? | Positioned in the implementation sequence, not deferred to "later". Credential-dependent tests (e.g. `TEST_JWT`) state how to obtain the credential and what to do if it is unavailable |

## 4. Verdict thresholds

**Blocking:**
- Any test required by the change type (§2) is missing
- Any test is manual-only with no automation path
- A security control has no automated test verifying it (positive or negative path)
- Existing test suites are not listed as a required gate
- Tests are not wired into CI for future deploys

**Warning:**
- Test execution timing is ambiguous ("verify after apply" without specifying when, by whom, with what script)
- A smoke test exists but is described as a manual step rather than a scripted gate
