# Layer 3: NATS Auth Callout + Official NATS Helm Chart

**Goal:** Eliminate the static credential config file entirely. Agent
authentication is delegated to a service that queries Postgres on demand.
This removes the reload mechanism, enables NATS clustering, and uses the
official NATS Helm chart.

**Depends on:** Layer 2 (split deployments)

**Status:** Design (longer-term)

---

## Problem Statement

Layers 1 and 2 make the config reload reliable and decouple the
deployments, but the fundamental design remains: a static JSON file
containing every agent's credentials, regenerated on every agent
add/delete, and pushed to nats-server via file write + reload.

At scale this has issues:
- **Config size grows linearly** -- ~200 bytes per agent. At 50K agents
  the config is ~10MB, regenerated and reloaded for every single agent
  registration.
- **Reload is disruptive** -- nats-server re-evaluates all connections on
  config reload. Large configs cause latency spikes.
- **Clustering complexity** -- all cluster nodes must have the same auth
  config. Propagating a 10MB file to 3+ nodes on every agent change is
  expensive and racy.
- **No real-time auth revocation** -- a deleted agent's credentials remain
  valid until the next config reload lands.

---

## NATS Auth Callout Overview

Auth callout is a NATS-native mechanism where the server delegates
authentication decisions to a service. Instead of looking up credentials
in a static config, nats-server publishes a request to a well-known
subject and waits for an authorize/deny response.

### How It Works

```
Agent connects: user=<agent_id> password=<token>
    │
    ▼
nats-server receives CONNECT
    │
    ▼
Publishes authorization request to $SYS.REQ.USER.AUTH
    │ (contains: username, password, client IP, TLS info)
    │
    ▼
Auth service (running as NATS subscriber) receives request
    │
    ├─ Queries: SELECT 1 FROM agents_agent a
    │           JOIN accounts_user u ON u.agent_id = a.id
    │           JOIN authtoken_token t ON t.user_id = u.id
    │           WHERE a.agent_id = $1 AND t.key = $2
    │
    ├─ If valid: return signed JWT with permissions
    │   {
    │     "pub": {"allow": ["<agent_id>"]},
    │     "sub": {"allow": ["<agent_id>"]},
    │     "resp": {"max": 1, "ttl": "24h"}
    │   }
    │
    └─ If invalid: return error response
        → nats-server closes connection with "authorization violation"
```

### Key Properties

- Auth is evaluated **per connection**, not per message (no per-message overhead)
- The auth service is a regular NATS subscriber on `$SYS.REQ.USER.AUTH`
- Requests and responses are signed JWTs (Ed25519 NKeys)
- Optional encryption via X25519 curve (prevents credential sniffing on the wire)
- The auth service can be the same nats-api binary, just with an additional subscriber
- nats-server falls back to rejecting the connection if the auth service doesn't respond within timeout (configurable, default 1s)

---

## nats-server Configuration (Auth Callout)

The nats-server config becomes **static** -- no more per-agent entries:

```json
{
  "accounts": {
    "AUTH": {
      "users": [
        {
          "user": "auth-service",
          "password": "$SECRET_KEY"
        }
      ]
    },
    "APP": {},
    "SYS": {}
  },
  "authorization": {
    "auth_callout": {
      "issuer": "$AUTH_ACCOUNT_PUBLIC_NKEY",
      "auth_users": ["auth-service"],
      "account": "AUTH"
    }
  },
  "system_account": "SYS",
  "max_payload": 67108864,
  "host": "0.0.0.0",
  "port": 4222,
  "websocket": {
    "host": "0.0.0.0",
    "port": 9235,
    "no_tls": true
  }
}
```

This config **never changes** when agents are added or removed.
No reload mechanism needed. No config file regeneration. No reconciliation loop
(though Layer 1's loop could remain as a health check).

---

## Auth Service Implementation

The auth service runs inside nats-api (or as a separate binary). It
subscribes to `$SYS.REQ.USER.AUTH` and responds with signed JWTs.

### Using the synadia-io/callout.go Library

```go
import (
    "github.com/nats-io/jwt/v2"
    "github.com/nats-io/nkeys"
    callout "github.com/synadia-io/callout.go"
)

func startAuthService(nc *nats.Conn, db *sqlx.DB, issuerSeed []byte) error {
    issuerKP, err := nkeys.FromSeed(issuerSeed)
    if err != nil {
        return err
    }

    authorizer := func(req *callout.Request) (*callout.Response, error) {
        username := req.Claims().ConnectOptions.Username
        password := req.Claims().ConnectOptions.Password

        // Backend superuser: allow everything
        if username == "tacticalrmm" && password == secretKey {
            return req.Approve(&jwt.UserClaims{
                UserPermissionLimits: jwt.UserPermissionLimits{
                    Permissions: jwt.Permissions{
                        Pub:  jwt.Permission{Allow: jwt.StringList{">"}},
                        Sub:  jwt.Permission{Allow: jwt.StringList{">"}},
                    },
                },
            }, issuerKP)
        }

        // Agent: validate against database
        var exists bool
        err := db.QueryRowContext(req.Context(), `
            SELECT EXISTS(
                SELECT 1 FROM agents_agent a
                JOIN accounts_user u ON u.agent_id = a.id
                JOIN authtoken_token t ON t.user_id = u.id
                WHERE a.agent_id = $1 AND t.key = $2
            )
        `, username, password).Scan(&exists)

        if err != nil || !exists {
            return req.Reject("authorization violation"), nil
        }

        return req.Approve(&jwt.UserClaims{
            UserPermissionLimits: jwt.UserPermissionLimits{
                Permissions: jwt.Permissions{
                    Pub:  jwt.Permission{Allow: jwt.StringList{username}},
                    Sub:  jwt.Permission{Allow: jwt.StringList{username}},
                    Resp: &jwt.ResponsePermission{MaxMsgs: 1, Expires: 24 * time.Hour},
                },
            },
        }, issuerKP)
    }

    svc, err := callout.NewService(nc, callout.WithAuthorizer(authorizer))
    return err
}
```

### Performance Considerations

**Auth callout latency** adds to every agent connection handshake:

| Component | Expected Latency |
|-----------|-----------------|
| NATS internal routing | <1ms |
| Auth service processing | <1ms |
| Postgres query (indexed) | 1-5ms |
| **Total per connection** | **2-7ms** |

This is acceptable because:
- Auth is per-connection, not per-message
- Agents maintain long-lived connections (reconnect only on failure/restart)
- A fleet of 10K agents all reconnecting simultaneously (worst case: nats-server restart) would take ~7ms * 10K = ~70 seconds if serial, but NATS handles concurrent auth callouts

**Important: Backend uses ephemeral connections.** The Django backend
creates a new NATS connection for every `nats_cmd()` call
(agents/models.py:876: `nc = await nats.connect(**opts)`). Each
connection triggers auth callout. With frequent commands (e.g., bulk
script execution across 1000 agents), this means 1000 auth callout
round-trips. The backend's superuser auth (`tacticalrmm`/`SECRET_KEY`)
should be cached aggressively or the backend should switch to a
connection pool.

**Caching option:** For large fleets, add an in-memory LRU cache in the
auth service (key: `agent_id:token_hash`, TTL: 5 minutes). This reduces
Postgres load during mass reconnect events and frequent backend commands.

```go
type authCache struct {
    mu    sync.RWMutex
    items map[string]cacheEntry // key: "agent_id:token_sha256"
}

type cacheEntry struct {
    allowed   bool
    expiresAt time.Time
}
```

Cache invalidation: the `trmm.nats.reload` signal (kept from Layer 1)
clears the cache. Or use a short TTL (5 min) and accept that a deleted
agent might stay connected for up to 5 minutes.

---

## Official NATS Helm Chart as Subchart

With auth callout, the nats-server config is static. This makes it
trivial to use the official NATS Helm chart.

### Chart.yaml

```yaml
apiVersion: v2
name: tacticalrmm
version: 0.1.0
dependencies:
  - name: nats
    version: "1.2.x"
    repository: "https://nats-io.github.io/k8s/helm/charts/"
    condition: nats.enabled
    alias: nats-server
```

### values.yaml

```yaml
nats-server:
  enabled: true

  config:
    cluster:
      enabled: true           # 3-node cluster
    jetstream:
      enabled: false          # Not needed for RMM (pure pub/sub)
    merge:
      max_payload: 67108864
      websocket:
        host: "0.0.0.0"
        port: 9235
        no_tls: true
      accounts:
        AUTH:
          users:
            - user: auth-service
              password: "$SECRET_KEY"   # Injected via env
        APP: {}
        SYS: {}
      authorization:
        auth_callout:
          issuer: "$AUTH_NKEY"          # Injected via env/secret
          auth_users: ["auth-service"]
          account: AUTH
      system_account: SYS

  container:
    image:
      repository: nats
      tag: 2.12-alpine

  # 3 replicas for HA
  statefulSet:
    replicas: 3

  # Pod disruption budget
  podDisruptionBudget:
    minAvailable: 2
```

### What the Official Chart Provides

Out of the box, with no custom code:

- **StatefulSet** with stable network identities (nats-0, nats-1, nats-2)
- **Cluster auto-discovery** via headless service
- **Config reloader sidecar** (watches mounted config, SIGHUPs on change)
- **Readiness/liveness probes** on NATS health endpoint
- **PodDisruptionBudget** for safe rolling updates
- **Service** for client connections (4222) and cluster routes (6222)
- **Monitoring** integration (Prometheus, NATS surveyor)

---

## What Gets Removed

With auth callout in place, the following code/mechanisms become unnecessary:

| Component | Status |
|-----------|--------|
| `GenerateNatsRmmConfig()` in generate.go | **Removed** -- no more static config generation |
| `computeConfigHash()` from Layer 1 | **Removed** or repurposed as health check |
| `trmm.nats.reload` NATS subject | **Repurposed** -- clears auth cache instead of regenerating config |
| `reload_nats()` in Python | **Simplified** -- only publishes cache-clear signal |
| `agent_updater.py` Redis subscriber | **Removed** -- no local config to refresh |
| Bootstrap init container | **Simplified** -- no config generation, just wait for dependencies |
| Config reloader sidecar | **Removed** -- config is static |
| Reconciliation loop (Layer 1) | **Optional** -- can repurpose as auth cache warm-up |

---

## NKey Management

Auth callout requires an Ed25519 NKey pair for signing JWTs:

### Key Generation

```bash
# Generate account keypair (one-time setup)
nsc generate nkey --account
# Output:
#   SAANWFZ3JINNPERWN3BQYYQINOLI7TFEQ3PQ5QKAEMKU5IZUSUAVELMA
#   ADRXASWJDV7GI5YKOIXB33CSNI7HTXWC7NFJRMHBHQM7O2QS7KRQZWH

# The seed (SA...) is the private key → store as K8s Secret
# The public key (AD...) goes into nats-server config as "issuer"
```

### Secret Management

```yaml
# K8s Secret
apiVersion: v1
kind: Secret
metadata:
  name: tactical-nats-auth
type: Opaque
data:
  AUTH_ISSUER_SEED: <base64 of SA... seed>
  AUTH_ISSUER_PUBLIC: <base64 of AD... public key>
```

The auth service reads the seed from the secret to sign JWTs.
The nats-server config references the public key as `issuer`.

---

## Agent Impact

**No changes required to agents.** Agents still connect with:
- `user: <agent_id>`
- `password: <auth_token>`

The authentication mechanism is transparent to NATS clients. The only
difference is that credentials are validated dynamically instead of
being looked up in a static config.

**Behavioral difference:** A newly registered agent can connect
**immediately** after `reload_nats()` returns (which now just clears
the auth cache). No waiting for config regeneration + file write + SIGHUP + nats-server reload.

---

## Migration Path

| Phase | Change | Rollback |
|-------|--------|----------|
| 1 | Generate NKey pair, store as K8s Secret | Delete secret |
| 2 | Add auth callout handler to nats-api (alongside existing telemetry subscribers) | Remove handler |
| 3 | Deploy nats-server with auth callout config (via official chart) in parallel with existing nats | Delete new StatefulSet |
| 4 | Point one test agent at new nats-server, validate auth + telemetry | Revert agent config |
| 5 | Gradually migrate agents to new nats-server | Revert per-agent |
| 6 | Decommission old tactical-nats deployment | Redeploy if needed |
| 7 | Remove config generation code, reconciliation loop, reload_nats() legacy paths | Git revert |

### Parallel Deployment Strategy

During migration, both old and new NATS can coexist:

```
                    ┌─ old tactical-nats (static config)
Agents ────────────┤
                    └─ new nats-cluster (auth callout)
                         ├─ nats-0
                         ├─ nats-1
                         └─ nats-2
```

Agent connection target is controlled by the agent's NATS URL config.
New agents get the new URL at registration. Existing agents are migrated
in batches by pushing a config update command through the old NATS.

---

## Dependencies

### Go modules to add

```
github.com/nats-io/jwt/v2       # JWT creation and signing (new direct dep)
github.com/nats-io/nkeys        # Ed25519 NKey operations (already indirect dep at v0.4.7 in go.mod)
github.com/synadia-io/callout.go # Auth callout service framework (new dep)
```

Note: The current go.mod uses Go 1.26 and already pulls `nats-io/nkeys`
v0.4.7 as a transitive dependency of `nats-io/nats.go`. Promoting it to
a direct dependency should not introduce version conflicts.

### Infrastructure

- NKey pair generation tooling (`nsc` CLI or custom init job)
- K8s Secret for NKey seed
- Official NATS Helm chart (`nats-io/k8s`)
- Optional: Prometheus ServiceMonitor for NATS metrics

---

## Comparison: Before and After

| Aspect | Current (Static Config) | After (Auth Callout) |
|--------|------------------------|---------------------|
| Config file | ~200 bytes * N agents | Static, ~500 bytes total |
| Agent add/delete | Regenerate + reload | Immediate (no action) |
| Auth revocation | Next reload cycle | Next connection attempt (or cache TTL) |
| NATS clustering | Complex (config sync) | Trivial (static config, shared auth service) |
| Postgres dependency | Bootstrap + reconciliation only | Every agent connection (cacheable) |
| Code complexity | generate.go, reconcile, reload_nats(), agent_updater | Auth handler (~100 lines) |
| Failure mode | Lost reload = broken agents | Auth service down = no new connections (existing stay) |

---

## Open Questions

1. **Auth service availability** -- if the auth service is down, no new
   agents can connect. Should we run 2+ replicas? The auth service can
   be embedded in nats-api, which is already a Deployment that can scale.

2. **Cache invalidation strategy** -- TTL-based (simple, 5-min lag) vs.
   event-based (reload signal clears cache, immediate but more complex)?

3. **Encryption (xkey)** -- auth callout supports X25519 encryption of
   the request/response. Worth the overhead? Probably not if the NATS
   cluster is internal-only.

4. **JetStream** -- not needed for the current pub/sub model, but if we
   want durable message delivery for reload signals (replacing the
   reconciliation loop), JetStream could provide exactly-once delivery.
   Worth evaluating as a separate enhancement.

5. **Agent token rotation** -- currently not implemented. Auth callout
   makes it trivial: rotate the token in Postgres, agent reconnects with
   new token on next disconnect. No config regeneration needed.
