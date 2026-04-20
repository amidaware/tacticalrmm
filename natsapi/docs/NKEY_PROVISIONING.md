# NATS Auth Callout NKey Provisioning

Layer 3 auth callout requires an Ed25519 account key pair. The **private seed**
(`SA…`) signs every approved user JWT inside `tactical-nats-listener`. The
**public key** (`AD…`) goes into the NATS server config as the trusted
issuer. Leaking the seed compromises the whole NATS auth boundary, so treat
it like a root-level secret.

## One-time generation

```bash
# Requires nsc: brew install nats-io/nats-tools/nsc
nsc generate nkey --account
# Output (two lines — first is seed, second is public):
#   SAANWFZ3JINNPERWN3BQYYQINOLI7TFEQ3PQ5QKAEMKU5IZUSUAVELMA
#   ADRXASWJDV7GI5YKOIXB33CSNI7HTXWC7NFJRMHBHQM7O2QS7KRQZWH
```

Store both values, but in different places:

| Value | Where it goes | Who reads it |
|---|---|---|
| Seed (`SA…`) | GCP Secret Manager → K8s Secret `tactical-nats-auth` key `AUTH_ISSUER_SEED` | `tactical-nats-listener` pod (validator signs UserClaims JWT) |
| Public (`AD…`) | GCP Secret Manager → K8s Secret `nats-auth-callout` key `AUTH_ISSUER_PUBLIC` | `nats-server` config `authorization.auth_callout.issuer` |

Also generate a random `AUTH_SERVICE_PASS` — the password
`tactical-nats-listener` uses to connect as the `auth-service` user inside the
NATS `AUTH` account. Must be the same on both sides.

```bash
openssl rand -base64 32
```

## Writing to GCP Secret Manager

Assuming the tenant's single GCP SM entry (the one referenced by
`deployment.saas.ingress.gcp.externalSecretName`) already stores other
`SAAS_TENANT.*` values:

```bash
# Replace <tenant-secret-name> with the actual GCP SM secret name.
gcloud secrets versions add <tenant-secret-name> --data-file=- <<'EOF'
SAAS_TENANT.NATS_AUTH_ISSUER_SEED=SAANWFZ3JINNPERWN3BQYYQINOLI7TFEQ3PQ5QKAEMKU5IZUSUAVELMA
SAAS_TENANT.NATS_AUTH_ISSUER_PUBLIC=ADRXASWJDV7GI5YKOIXB33CSNI7HTXWC7NFJRMHBHQM7O2QS7KRQZWH
SAAS_TENANT.NATS_AUTH_SERVICE_PASS=<openssl-random-value>
EOF
```

(If your tenant stores each property as an independent GCP SM secret
rather than as keys inside one secret, follow whatever pattern the
meshcentral ExternalSecret already uses — see
`openframe-saas-tenant/manifests/integrated-tools/meshcentral/templates/external-secrets.yaml`.)

## ExternalSecret consumers

Two ExternalSecrets reconcile the GCP SM values into K8s Secrets:

- `openframe-saas-tenant/manifests/integrated-tools/tactical-rmm/templates/external-secret-nats-auth.yaml`
  → creates `tactical-nats-auth` with the **seed** and the service password.
  Consumed by the `tactical-nats-listener` Deployment.

- `openframe-saas-tenant/manifests/integrated-tools/nats/templates/external-secret-auth-callout.yaml`
  → creates `nats-auth-callout` with the **public key** and the service
  password. Consumed by the `nats-server` configmap via env substitution.

Both refresh every 24h. A rotation lands within 24h of the GCP SM update
without a manual reconcile — but see below.

## Rotation

Rotating the issuer key is disruptive: every existing connection signed
against the old key must be re-auth'd. Sequence:

1. `nsc generate nkey --account` → new pair.
2. Write new seed + public to GCP SM as new versions of the same keys.
3. Wait for ExternalSecret refresh (or `kubectl annotate externalsecret
   <name> force-sync=$(date +%s)` to trigger immediately).
4. Rolling-restart the `nats-server` StatefulSet first. Agents
   reconnect, the server still accepts the *new* issuer — but rejects
   already-issued tokens. Brief auth-rejection window until step 5.
5. Rolling-restart `tactical-nats-listener` Deployment. New auth requests get
   signed with the new seed.
6. Observe `nats_api_auth_callout_total{result="rejected"}` — should
   spike during the window then return to baseline.

NATS does not support multi-issuer lists in centralized auth callout
mode, so a seamless rotation (accept both old + new during a grace
window) is not possible. Plan rotations for a maintenance window.

Rotating `AUTH_SERVICE_PASS` has the same shape but affects only the
`tactical-nats-listener` → `nats-server` connection. Rolling-restart
`nats-server` first (it needs to learn the new password), then
`tactical-nats-listener`.

## Seed format validation

`loadIssuerKey` at `natsapi/authcallout.go:loadIssuerKey` rejects any
seed that isn't an `SA…` account key up-front with a clear error. If the
wrong value lands in the secret, the pod fail-fasts on startup instead
of silently mis-signing tokens.

## Threat model

- Seed leaked → an attacker with the seed can mint valid JWTs for any
  account the issuer is trusted for. **Rotate immediately** (procedure
  above). Consider also rotating every agent's `authtoken_token.key`
  because a seed-holder could have issued long-lived JWTs for arbitrary
  agent IDs before the rotation landed.
- Public key leaked → no compromise. The public key is safe to ship in
  config maps, logs, and `nats-api` startup output.
- `AUTH_SERVICE_PASS` leaked → an attacker can connect as the
  `auth-service` user, which under `auth_callout.auth_users` is exempted
  from the callout itself. They cannot mint JWTs, but they could try to
  subscribe to `$SYS.REQ.USER.AUTH` and observe credential attempts.
  Rotate and review audit logs.
