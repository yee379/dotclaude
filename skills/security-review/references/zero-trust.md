## mTLS — STRICT mode (Istio)

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: prod
spec:
  mtls:
    mode: STRICT   # reject plaintext — no exceptions
```

## AuthorizationPolicy — explicit allow, deny by default

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: api-authz
  namespace: prod
spec:
  selector:
    matchLabels:
      app: api
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/prod/sa/frontend"]
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/api/*"]
```

## Workload Identity — short-lived tokens, not static secrets

```python
# BAD: long-lived shared secret between services
headers = {"X-Service-Key": "static-secret-shared-forever"}

# GOOD: workload identity / SPIFFE / short-lived JWT
import google.auth.transport.requests
import google.oauth2.id_token

def get_service_token(audience: str) -> str:
    request = google.auth.transport.requests.Request()
    return google.oauth2.id_token.fetch_id_token(request, audience)
```

## Defense in Depth Layers

| Layer | Control | Verify |
|-------|---------|--------|
| Network | NetworkPolicy / firewall rules | Egress restricted to known destinations |
| Transport | mTLS between services | Plaintext internal traffic blocked |
| Application | Auth + authz on every request | No gateway-only auth assumptions |
| Data | Encryption at rest + in transit | KMS key rotation policy exists |
| Identity | Workload identity (SPIFFE/IRSA) | No long-lived static credentials |
| Observability | Audit logs, anomaly detection | Failed auth attempts alerted |
| Recovery | Incident response runbook | Blast radius limited by RBAC scope |

## Checklists

### Defense in Depth
- [ ] Layered controls — auth enforced at gateway AND service layer
- [ ] Blast radius scoped — compromising one service cannot pivot to all
- [ ] Egress restricted — services reach only known destinations
- [ ] Secrets have TTLs — no eternal API keys; rotation automated
- [ ] Audit logging — all auth decisions logged and queryable
- [ ] Alerting — anomalous auth failure rates trigger on-call
- [ ] Backups isolated — not accessible from production workloads
- [ ] Incident runbook exists — credential compromise, data breach steps

### Zero Trust
- [ ] Never trust network position — internal services authenticate each other
- [ ] mTLS enforced between services
- [ ] Workload identity used (SPIFFE, IRSA, Workload Identity)
- [ ] Least privilege per workload — ServiceAccounts scoped to minimum
- [ ] Device/client attestation for sensitive operations (MFA, step-up auth)
- [ ] Continuous verification — tokens short-lived; re-auth after expiry
- [ ] Microsegmentation — NetworkPolicy limits lateral movement
- [ ] No implicit trust for admin tooling — kubectl, CI runners use short-lived credentials
