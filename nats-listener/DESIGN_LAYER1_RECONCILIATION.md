# Layer 1: Reconciliation Loop + reload_nats() Cleanup

**Goal:** Make the NATS config reload mechanism reliable without architectural changes.

**Status:** Ready for implementation

---

## Problem Statement

The current reload mechanism relies on a fire-and-forget NATS publish to
`trmm.nats.reload`. If the message is lost (nats pod restarting, nats-api
crashed, network blip), the NATS server config drifts from the database.
The most critical failure: a newly registered agent cannot connect because
nats-server never received its credentials.

There is no retry, no reconciliation, and no desired-state comparison.

---

## Important: How the Wildcard Subscriber Works

Before diving in, a note on the NATS message routing in `svc.go`. The
wildcard subscriber (`nc.Subscribe("*", ...)` at line 198) discriminates
message types using `msg.Reply`, **not** `msg.Subject`:

```go
switch msg.Reply {       // ← Reply field, not Subject
case "agent-hello":      // agent publishes to subject=<agent_id>, reply="agent-hello"
case "agent-agentinfo":  // agent publishes to subject=<agent_id>, reply="agent-agentinfo"
...
}
```

Agents publish to their own `agent_id` as the subject (which the `*`
wildcard matches) and tag the message type in the Reply field. The
separate `trmm.nats.reload` subscription (line 355) works because the
dotted subject has 3 tokens and `*` only matches single-token subjects.

---

## Design

### 1. Reconciliation Loop in nats-api

Add a periodic background goroutine to `svc.go` that compares a hash of
the current agent credential set in Postgres against the last-known hash.
On mismatch, regenerate `nats-rmm.conf` and SIGHUP nats-server.

The existing `trmm.nats.reload` subscriber remains as a **fast path**
(immediate reload on agent add/delete). The reconciliation loop is the
**safety net** that catches anything the fast path missed.

#### Hash Computation

Query Postgres for all `(agent_id, token)` pairs in deterministic order,
stream them through MD5:

```go
func computeConfigHash(ctx context.Context, db *sqlx.DB) (string, int, error) {
    rows, err := db.QueryContext(ctx, `
        SELECT a.agent_id, t.key
        FROM agents_agent a
        JOIN accounts_user u ON u.agent_id = a.id
        JOIN authtoken_token t ON t.user_id = u.id
        ORDER BY a.agent_id ASC
    `)
    if err != nil {
        return "", 0, err
    }
    defer rows.Close()

    h := md5.New()
    count := 0
    for rows.Next() {
        var agentID, token string
        if err := rows.Scan(&agentID, &token); err != nil {
            return "", 0, err
        }
        count++
        fmt.Fprintf(h, "%s:%s;", agentID, token)
    }
    return hex.EncodeToString(h.Sum(nil)), count, rows.Err()
}
```

Performance: The query is the same JOIN used by `GenerateNatsRmmConfig()`
but only reads two columns. At 10K agents this is <50ms and ~200KB of
data. Running every 30-60s is negligible load.

#### Reconciliation Goroutine

Add after the metrics ticker setup in `svc.go` (~line 151), before the
signal handler:

```go
// Reconciliation: detect config drift and self-heal.
// The trmm.nats.reload subscriber is the fast path; this is the safety net.
reconcileInterval := parseDurationEnv("RECONCILE_INTERVAL", 30*time.Second)
var lastConfigHash string

go func() {
    // Compute initial hash so the first tick is a no-op if config is current.
    if h, _, err := computeConfigHash(rootCtx, db); err == nil {
        lastConfigHash = h
    }

    ticker := time.NewTicker(reconcileInterval)
    defer ticker.Stop()
    for {
        select {
        case <-rootCtx.Done():
            return
        case <-ticker.C:
            ctx, cancel := context.WithTimeout(rootCtx, dbJobTimeout)
            hash, count, err := computeConfigHash(ctx, db)
            cancel()
            if err != nil {
                reconcileTotal.WithLabelValues("query_error").Inc()
                logger.Errorf("reconcile: hash query: %v", err)
                continue
            }
            if hash == lastConfigHash {
                reconcileTotal.WithLabelValues("in_sync").Inc()
                continue
            }
            logger.Infof("reconcile: config drift detected (%d agents), regenerating", count)
            reconcileTotal.WithLabelValues("drift_detected").Inc()
            if err := GenerateNatsRmmConfig(logger, db, r.Key, natsRmmConfigPath); err != nil {
                reconcileTotal.WithLabelValues("regen_error").Inc()
                logger.Errorf("reconcile: regenerate: %v", err)
                continue
            }
            if err := SignalNatsServerReload(logger); err != nil && !errors.Is(err, ErrNatsServerNotFound) {
                reconcileTotal.WithLabelValues("signal_error").Inc()
                logger.Errorf("reconcile: SIGHUP: %v", err)
            }
            lastConfigHash = hash
            reconcileTotal.WithLabelValues("ok").Inc()
        }
    }
}()
```

#### Thread Safety for Shared Hash State

Both the reconciliation goroutine and the `trmm.nats.reload` subscriber
callback run in separate goroutines. The shared `lastConfigHash` must be
protected. Use `sync.Mutex` (not `atomic.Value` — strings aren't
pointer-sized):

```go
var (
    mu             sync.Mutex
    lastConfigHash string
)

func setHash(h string) { mu.Lock(); lastConfigHash = h; mu.Unlock() }
func getHash() string  { mu.Lock(); defer mu.Unlock(); return lastConfigHash }
```

#### Interaction with trmm.nats.reload Subscriber

When the existing reload subscriber fires (svc.go:355), it should also
update `lastConfigHash` so the next reconciliation tick sees the config as
current and skips the redundant regeneration:

```go
// In reload subscriber, after successful GenerateNatsRmmConfig:
if h, _, err := computeConfigHash(context.Background(), db); err == nil {
    setHash(h) // prevents redundant reconciliation on next tick
}
```

#### Note: GenerateNatsRmmConfig Lacks Context

`GenerateNatsRmmConfig()` (generate.go:25) uses `db.Query()` without a
`context.Context` parameter. This means the reconciliation loop's timeout
context does not propagate into the config generation query. For Layer 1
this is acceptable (the query is fast), but should be refactored to accept
`context.Context` when implementing Layer 2.

#### New Prometheus Metrics

Add to `metrics.go`:

```go
reconcileTotal = promauto.NewCounterVec(prometheus.CounterOpts{
    Name: "nats_api_reconcile_total",
    Help: "Config reconciliation outcomes.",
}, []string{"result"})
// Labels: in_sync, drift_detected, ok, query_error, regen_error, signal_error

reconcileDurationSeconds = promauto.NewHistogram(prometheus.HistogramOpts{
    Name:    "nats_api_reconcile_duration_seconds",
    Help:    "Time to compute config hash and compare.",
    Buckets: prometheus.ExponentialBuckets(0.001, 2, 12), // 1ms .. ~4s
})
```

#### New Environment Variable

| Variable | Default | Description |
|----------|---------|-------------|
| `RECONCILE_INTERVAL` | `30s` | How often to check for config drift. Set to `0` to disable. |

---

### 2. Cleanup of reload_nats() in Python

**File:** `api/tacticalrmm/tacticalrmm/utils.py`, lines 227-495

The function currently does four things:

| Step | Lines | Purpose | Needed in K8s? |
|------|-------|---------|----------------|
| Build user list from ORM | 245-293 | Construct NATS auth config | **Yes** (for standalone) |
| Write nats-rmm.conf to local disk | 341-355 | Local nats-server reads it | **No** (different pod) |
| subprocess nats-server --signal reload | 363-424 | SIGHUP local nats-server | **No** (different pod) |
| subprocess nats-api signal | 426-439 | Signal nats-api to reload | **No** (nats-api is subscriber) |
| Redis publish agent_updates | 441-486 | Notify peer backends | **Yes** (celery etc.) |
| NATS publish trmm.nats.reload | 488-491 | Notify tactical-nats container | **Yes** (fast path) |

#### Recommended Changes

```python
def reload_nats(*, publish: bool = True) -> None:
    """
    Broadcast a NATS config update signal.

    In Kubernetes/Docker, the tactical-nats sidecar subscribes to
    trmm.nats.reload and regenerates nats-rmm.conf from Postgres.
    The nats-api reconciliation loop serves as a safety net.

    For standalone installs, this function also writes the config
    locally and signals the co-located nats-server.
    """
    logger = logging.getLogger(__name__)

    # Count agents for notification payload
    agent_count = Agent.objects.filter(
        user__isnull=False, user__auth_token__isnull=False
    ).count()

    # Standalone installs: write config + SIGHUP (legacy path)
    if _is_standalone_install():
        _write_local_nats_config(logger)
        _signal_local_nats_server(logger)

    if publish:
        _publish_nats_reload_signal(agent_count)
        _publish_redis_agent_update(agent_count)
```

**What changes:**
- Remove ~100 lines of debug `print()` statements
- Gate local file write + subprocess behind `_is_standalone_install()` check
  (e.g., `os.path.exists("/usr/local/bin/nats-server")` — already the current guard)
- Extract helpers for readability
- The Redis pubsub path (`agent_updater.py`) stays as-is for peer backend notification

#### What stays unchanged

- `core/agent_updater.py` — still needed for celery/websocket instances
- `_publish_nats_reload_signal()` — still the fast-path trigger for nats-api
- All callers of `reload_nats()` (agents/views.py, apiv3/views.py, core/views.py, management commands)

---

### 3. Reload Trigger Inventory

For reference, all places that call `reload_nats()`:

| Trigger | File | When |
|---------|------|------|
| New agent registers | `apiv3/views.py:480` | Agent installer first check-in |
| Agent deleted via API | `agents/views.py:283` | Admin deletes agent |
| Bulk delete CLI | `agents/management/commands/bulk_delete_agents.py:105` | Admin bulk cleanup |
| Manual reload | `core/views.py:170` | Admin triggers from UI |
| Management command | `core/management/commands/reload_nats.py:11` | CLI |
| Redis peer notification | `core/agent_updater.py:77` | Another backend instance reloaded (calls with `publish=False`) |

---

## Failure Mode Analysis (After Layer 1)

| Scenario | Before | After |
|----------|--------|-------|
| NATS publish lost (pod restart) | Config never updates | Reconciliation detects drift within 30s |
| nats-api crashed during reload | Config partially updated | Reconciliation retries on next tick |
| Network blip between backend and NATS | Silent failure | Reconciliation catches it |
| Direct DB edit (bypassing backend) | Never detected | Reconciliation detects hash change |
| nats-api not connected yet (boot race) | Config stuck until next restart | Bootstrap covers cold start; reconciliation covers warm drift |
| Postgres slow/unavailable | Hash query times out | Logged, retried next tick (non-fatal) |

---

## Files to Change

| File | Change |
|------|--------|
| `nats-listener/svc.go` | Add reconciliation goroutine + shared hash state |
| `nats-listener/reconcile.go` | New file: `computeConfigHash()` function |
| `nats-listener/metrics.go` | Add `reconcile_total`, `reconcile_duration_seconds` |
| `nats-listener/utils.go` | Add `parseDurationEnv()` helper |
| `api/tacticalrmm/tacticalrmm/utils.py` | Clean up `reload_nats()`, remove dead code paths |

---

## Testing

1. **Unit test for hash stability:** Given the same DB state, `computeConfigHash` returns the same value across calls.
2. **Integration test for drift detection:** Insert an agent directly into Postgres (bypassing `reload_nats`), verify reconciliation picks it up within one interval.
3. **Test that reload subscriber updates the hash:** Publish `trmm.nats.reload`, verify the next reconciliation tick shows `in_sync`.
4. **Test Python cleanup:** Verify `reload_nats()` in K8s mode does NOT attempt subprocess calls.
