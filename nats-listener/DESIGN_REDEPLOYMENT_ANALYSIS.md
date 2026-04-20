# Redeployment Smoothness Analysis

**Goal:** Understand what breaks during `helm upgrade` today, and how
each design layer improves (or risks regressing) the rollout experience.

---

## Current State: What Happens During `helm upgrade`

### Dependency Chain

```
PostgreSQL / Redis  (external, assumed stable)
        │
        ▼
  Backend StatefulSet (tactical-backend-0)     ← CRITICAL BLOCKER
        │
        ├──────────────────┬───────────────┬──────────────────┐
        ▼                  ▼               ▼                  ▼
   NATS Deployment    Celery          Celerybeat          Websockets
   (init waits for    (init waits     (Recreate strategy  (init waits
    backend TCP:8000)  for backend)    → forced downtime)   for backend)

  Frontend / Nginx  ← independent, roll immediately
```

### Per-Component Rollout Behavior

| Component | Kind | Strategy | Replicas | Grace Period | Init Blocks On |
|-----------|------|----------|----------|-------------|----------------|
| Backend | StatefulSet | RollingUpdate | 1 | 30s (default) | Postgres, Redis, (Nginx) |
| NATS | Deployment | RollingUpdate (default) | 1 | 30s (default) | Postgres, **Backend TCP:8000** |
| Celery | Deployment | RollingUpdate (default) | 1 | 30s (default) | Postgres, Redis, Backend |
| Celerybeat | Deployment | **Recreate** | 1 | 30s (default) | Postgres, Redis, Backend |
| Websockets | Deployment | RollingUpdate (default) | 1 | 30s (default) | Postgres, Redis, Backend |
| Frontend | Deployment | RollingUpdate (default) | 1 | 30s (default) | None |
| Nginx | Deployment | RollingUpdate (default) | 1 | 30s (default) | None |

### K8s RollingUpdate Behavior with replicas=1

**Important nuance:** For a Deployment with `replicas: 1` and no explicit
strategy, K8s defaults to RollingUpdate with `maxSurge=25%` (rounds UP
to 1) and `maxUnavailable=25%` (rounds DOWN to 0). This means:

- K8s creates the new pod **before** killing the old one
- The old pod stays running until the new pod passes readiness
- Max total pods during rollout: 2 (1 desired + 1 surge)

For NATS, this means the old nats-server keeps running while the new
pod's init container bootstraps. Agents stay connected to the old pod
throughout. The disconnect happens only when the old pod is terminated
after the new one is ready — a brief ~2-5s reconnect window.

**Exception:** StatefulSets (backend) default to `RollingUpdate` with
`partition: 0`, which updates pods in reverse ordinal order. With
`replicas: 1`, this terminates the old pod, then creates the new one —
there IS a full gap for the backend.

### Rollout Scenarios

**Scenario 1: Backend-only update (most common)**
```
t=0s      Backend pod tactical-backend-0 terminated (StatefulSet)
t=0-30s   Backend graceful shutdown
          ┌─ NATS pod is UNAFFECTED — agents stay connected ─┐
t=30s     New backend pod starts init container
t=~60s    Backend passes startup probe (typical)
          Backend resumes sending commands to agents via NATS

          Agent disconnect: NONE
          Backend→agent commands: fail ~60s ("natsdown" returns)
          Telemetry: uninterrupted (nats-api keeps writing to Postgres)
```

**Scenario 2: NATS-only update**
```
t=0s      New NATS pod created (RollingUpdate, maxUnavailable=0)
          Old NATS pod still running — agents connected
t=0s      New pod init: waits for Postgres + Backend TCP:8000
t=~10s    Init container runs nats-api -bootstrap
t=~15s    New pod main container starts (supervisord)
t=~25s    New pod passes readiness (TCP:4222)
t=~25s    Old pod receives SIGTERM
t=~27s    Agents on old pod disconnect, reconnect to new pod via service

          Agent disconnect: ~2-5s (reconnect window when old pod dies)
          Telemetry gap: ~5s
```

**Scenario 3: Full helm upgrade (all images change)**
```
t=0s      Backend StatefulSet: old pod terminated (no surge for SS)
          NATS Deployment: new pod created alongside old (surge)
          ┌─ Old NATS pod still running — agents connected ─┐
t=0-30s   Backend shutdown, old NATS still serving agents
t=30s     New backend pod starts init container
          New NATS pod init blocked on backend TCP:8000
t=~60s    Backend passes startup probe
t=~60s    NATS init unblocks → bootstrap → main container starts
t=~70s    New NATS pod passes readiness
t=~70s    Old NATS pod terminated
t=~72s    Agents reconnect to new NATS pod

          Agent disconnect: ~2-5s at t=70s (old pod killed)
          Backend commands: fail for ~60s (backend restarting)
          Telemetry gap: ~5s at t=70s
```

**Worst case (backend startup takes full 300s):**
Same as Scenario 3 but the NATS init blocks until t=~300s. The old NATS
pod stays running the entire time (maxUnavailable=0), so agents remain
connected for those 300s. The disconnect is still only ~2-5s when the
old pod is finally killed.

### What Agents Experience

Agents maintain **persistent NATS connections** (long-lived TCP).

**During backend-only restart:** Nothing changes for agents. They stay
connected to NATS. Their telemetry keeps flowing through nats-api to
Postgres. Only backend→agent commands (scripts, patches) fail.

**During NATS pod rollout (RollingUpdate):** The old pod stays alive
until the new one is ready. Agents experience a brief disconnect (~2-5s)
when the old pod is terminated. The NATS client library handles reconnect
automatically.

**During the reconnect window:**
- Agent telemetry is **buffered client-side** by the NATS client library
  and replayed on reconnect (if agent uses ReconnectBufSize > 0)
- Backend→agent commands fail with `"natsdown"` — no retry, no queue
- Scheduled tasks that fire during the backend gap **silently fail**

### What the Backend Experiences

The Django backend creates **ephemeral NATS connections** (connect per
command, 3s timeout, max 2 reconnect attempts):

```python
# helpers.py:114-123
opts = {
    "connect_timeout": 3,
    "max_reconnect_attempts": 2,
}
```

If NATS is down when the backend tries to send a command:
- `nats_cmd()` returns `"natsdown"` (agents/models.py:878)
- The command is **not retried** and **not queued**
- Fire-and-forget commands (`wait=False`) fail silently
- Request-reply commands (`wait=True`) return timeout to the UI

---

## Existing Problems

### 1. No PodDisruptionBudgets

Any `kubectl drain` or node autoscaler can evict NATS/backend pods
without checking cluster health. During node maintenance, all agents
disconnect simultaneously with no protection.

### 2. NATS Priority Class Bug

The NATS deployment references `tactical-priority` (deployment.yaml:22)
but `priorityclass.yaml` only defines `tactical-backend`. If
`priorityClass.enabled=true`, the NATS pod **fails to schedule**.

### 3. Single Replica Everything

Every component runs as `replicas: 1`. There is zero redundancy.
For Deployments (NATS, Celery, etc.), RollingUpdate with default
`maxUnavailable=0` keeps the old pod running until the new one is ready,
so there's only a brief reconnect gap (~2-5s). But for the backend
**StatefulSet**, pods are replaced sequentially (old terminated, then new
created), so there IS a full gap.

### 4. Backend Is the Bottleneck

Everything waits for `tactical-backend-0` TCP:8000. The backend's startup
probe allows up to 300 seconds. During that window, NATS, Celery,
Celerybeat, and Websockets are all stuck in init containers.

### 5. Celerybeat Recreate Strategy

Celerybeat uses `strategy: Recreate`, which kills the old pod before
starting the new one. This guarantees a gap where no scheduled tasks
fire. Combined with the backend dependency, the gap can be 60-300s.

### 6. emptyDir Volumes

NATS, Celery, Celerybeat, and Websockets all use emptyDir. Every
restart regenerates state from scratch. For NATS this means running
the full bootstrap query against Postgres on every pod restart.

### 7. No Graceful NATS Drain

The NATS deployment has no `preStop` hook. When K8s sends SIGTERM,
nats-server closes immediately. A `preStop` hook could tell agents
to reconnect to another node (relevant when clustering is added).

---

## Layer 1 Impact on Redeployment

**Changes:** Adds reconciliation loop to nats-api. Cleans up reload_nats().

### What Improves

- **Post-restart convergence:** After the NATS pod restarts, the
  reconciliation loop ensures the config matches the DB within 30s,
  even if the bootstrap generated a slightly stale config (e.g., an
  agent registered during the restart window).
- **No more lost reload signals:** If the backend publishes
  `trmm.nats.reload` while NATS is restarting, the reconciliation
  loop catches the drift on the next tick.

### What Doesn't Change

- Rollout sequence is identical
- Agent disconnection time is identical
- All the existing problems (no PDB, single replica, etc.) remain

### Risk

- **Minimal.** The reconciliation loop is a read-only Postgres query
  every 30s. If it fails, it logs and retries next tick. No new
  failure modes introduced.

---

## Layer 2 Impact on Redeployment

**Changes:** Split nats-server and nats-api into separate Deployments.

### What Improves

- **Independent rollouts:** Updating the nats-api Go binary no longer
  restarts nats-server. Agents stay connected during nats-api upgrades.
  This is the single biggest improvement.

  ```
  Before:  nats-api update → nats-server restarts → all agents disconnect
  After:   nats-api update → nats-api reconnects → agents unaffected
  ```

- **nats-server can be managed by official Helm chart:** Gets proper
  StatefulSet semantics, stable network identity, config reloader sidecar.

- **Path to replicas > 1:** nats-server as a StatefulSet can scale to
  3 replicas with NATS clustering. nats-api as a Deployment can also
  scale (though must handle duplicate message processing).

### What Doesn't Change

- nats-server restarts still disconnect all agents (single replica)
- Backend is still the bottleneck for NATS startup
- No PDB, no graceful drain

### New Risks

| Risk | Mitigation |
|------|------------|
| Shared PVC (Option A): RWX storage may not be available | Fall back to ConfigMap API (Option B) |
| Config reloader sidecar adds complexity | Use official NATS chart which includes it |
| nats-api bootstrap must run before nats-server starts | Keep init container ordering, but now across pods — need to coordinate via shared volume or readiness |
| Two Deployments to monitor instead of one | Better separation of concerns, easier to debug |

### Rollout Scenarios (Post-Split)

**Scenario A: nats-api update only**
```
t=0s    New nats-api pod starts
t=3s    Connects to existing nats-server
t=5s    Subscribes to subjects, ready
        Agents: UNAFFECTED (nats-server never restarted)
        Downtime: 0s for agents, ~5s gap in telemetry ingestion
```

**Scenario B: nats-server update (StatefulSet with Layer 2)**
```
t=0s    New nats-server pod created (if StatefulSet: old terminated first)
        If Deployment with maxUnavailable=0: old pod stays until new ready
t=~20s  New pod reads config from PVC/ConfigMap
t=~25s  nats-server ready (TCP:4222 probe passes)
t=~25s  Old pod terminated (if it was still running)
t=~27s  Agents reconnect to new pod
        Downtime: ~2-5s (reconnect window)
```

**Scenario C: Full helm upgrade (both)**
```
t=0s    Backend StatefulSet: old pod terminated
        nats-server + nats-api: rolling update starts
        Old nats-server stays running (agents connected)
t=~60s  Backend ready
t=~65s  nats-api connects, starts subscribing
        nats-server new pod ready → old pod terminated
t=~67s  Agents reconnect (~2-5s)
        Agent disconnect: ~2-5s
        Backend commands: fail ~60s (backend restarting)
```

### Recommended Additions for Layer 2

1. **PodDisruptionBudget for nats-server:**
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: tactical-nats-server
   spec:
     minAvailable: 1
     selector:
       matchLabels:
         app.kubernetes.io/component: tactical-nats-server
   ```

2. **preStop hook for nats-server:**
   ```yaml
   lifecycle:
     preStop:
       exec:
         command: ["nats-server", "--signal", "ldm=1"]  # Lame Duck Mode, PID 1
   ```
   Lame Duck Mode tells connected clients to reconnect to other servers.
   The `=1` specifies the PID (nats-server is PID 1 in its container).
   Useful when clustering is added in Layer 3. For single-replica setups,
   a simple `sleep 5` is sufficient to let K8s remove the pod from
   service endpoints before connections drop.

3. **Increase terminationGracePeriodSeconds to 45s** for the NATS pod:
   ```yaml
   terminationGracePeriodSeconds: 45
   ```
   Gives time for LDM/sleep (5-10s) + nats-api drain (10s) + worker
   cleanup (15s). The current default (30s) is tight: nats-api needs
   10s drain + 15s worker grace = 25s (svc.go:44-49), leaving only 5s
   margin.

---

## Layer 3 Impact on Redeployment

**Changes:** Auth callout + official NATS Helm chart with clustering.

### What Improves

- **NATS HA (3 replicas):** Agent connections are distributed across
  cluster nodes. Rolling update takes down one node at a time. Agents
  on that node reconnect to the remaining two. **Zero agent downtime
  during NATS rollouts.**

  ```
  Before:  1 NATS pod → restart → 100% agents disconnect
  After:   3 NATS pods → rolling → ~33% agents briefly reconnect
  ```

- **No config regeneration on agent add/delete:** Auth callout validates
  credentials on-demand from Postgres. The nats-server config is static.
  No reload, no config file write, no SIGHUP. Rolling updates are
  config-change-free.

- **Official NATS chart provides:**
  - StatefulSet with ordered rolling updates
  - PodDisruptionBudget (minAvailable: 2 of 3)
  - Config reloader sidecar (for static config changes)
  - Lame Duck Mode on SIGTERM (clients migrate before shutdown)
  - Cluster route auto-discovery via headless service

### Rollout Scenarios (Post-Layer-3)

**Scenario A: nats-api update**
```
Agents: UNAFFECTED
Telemetry gap: ~5s while new pod connects
Auth callout gap: ~5s (nats-server queues auth requests until service reconnects,
  or rejects with timeout — configurable)
```

**Scenario B: nats-server rolling update (3 replicas)**
```
t=0s    nats-server-2 enters Lame Duck Mode
        Clients on nats-2 receive LDM notification
        Clients start migrating to nats-0 and nats-1
t=10s   nats-server-2 terminates
        Any remaining clients reconnect to nats-0/nats-1
t=15s   New nats-server-2 starts, joins cluster
t=20s   nats-server-2 ready
        Repeat for nats-server-1, then nats-server-0
        
        Agent downtime: 0s (connections migrate)
        Telemetry gap: 0s (nats-api connected to cluster, not individual nodes)
```

**Scenario C: Full helm upgrade**
```
t=0s    Backend restarts (same as current, ~60s)
        Agents: UNAFFECTED (NATS cluster stays up)
        Agent commands: fail for ~60s (backend can't connect to NATS)
t=60s   Backend ready, reconnects to NATS cluster
        nats-api: UNAFFECTED (independent Deployment)
        nats-server: UNAFFECTED (independent StatefulSet, no config change)
```

### New Risk: Auth Service Availability

If the auth callout service (embedded in nats-api) is down:
- **Existing connections:** UNAFFECTED (already authenticated)
- **New connections:** REJECTED (nats-server times out the auth callout)
- **Reconnecting agents:** REJECTED until auth service is back

**Mitigation:**
- Run nats-api with `replicas: 2` (auth callout is stateless, both
  instances subscribe to `$SYS.REQ.USER.AUTH`)
- Add auth response caching (5-min TTL) so recent authentications
  don't need the service
- Set auth callout timeout to 5s (default 1s is too aggressive for
  Postgres query under load)

---

## Summary: Redeployment Impact by Layer

Note: "agent disconnect" means agents lose their NATS TCP connection.
With RollingUpdate (maxUnavailable=0), the old NATS pod stays alive
until the new one is ready, so the disconnect is only the brief ~2-5s
reconnect window when the old pod terminates.

| Metric | Current | After Layer 1 | After Layer 2 | After Layer 3 |
|--------|---------|---------------|---------------|---------------|
| Agent disconnect on NATS image update | **~2-5s** (reconnect) | **~2-5s** | **~2-5s** (nats-server only) | **No** (0s, LDM) |
| Agent disconnect on nats-api code update | **~2-5s** (coupled) | **~2-5s** (coupled) | **No** (0s, separate pod) | **No** (0s) |
| Agent disconnect on backend-only update | **No** (0s) | **No** (0s) | **No** (0s) | **No** (0s) |
| Agent disconnect on full upgrade | **~2-5s** (reconnect) | **~2-5s** | **~2-5s** | **No** (0s) |
| Backend commands during backend restart | Fail ~60s | Fail ~60s | Fail ~60s | Fail ~60s |
| Config drift after restart | Possible | **Fixed** (30s) | **Fixed** (30s) | **N/A** (no config) |
| Lost reload signals | Possible | **Fixed** | **Fixed** | **N/A** |
| Scheduled tasks during celerybeat restart | Missed (~30s+) | Missed (~30s+) | Missed (~30s+) | Missed (~30s+) |

**Key insight:** The current architecture is better than initially
assessed. RollingUpdate with maxUnavailable=0 means agents are NOT
disconnected for extended periods. The main issues are:
1. Config drift (fixed by Layer 1)
2. Coupled nats-api/nats-server lifecycle (fixed by Layer 2)
3. No HA / zero-downtime rolling updates (fixed by Layer 3)

---

## Recommended Quick Wins (Any Layer)

These are independent of the 3-layer plan and should be done regardless:

### 1. Fix the PriorityClass bug

The NATS deployment references `tactical-priority` but only
`tactical-backend` is defined. Either rename or add the missing class.

### 2. Add PodDisruptionBudgets

Even with single replicas, a PDB prevents accidental eviction during
node drain:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: tactical-nats
spec:
  maxUnavailable: 0    # Block eviction entirely for single-replica
  selector:
    matchLabels:
      app.kubernetes.io/component: tactical-nats
```

### 3. Set explicit terminationGracePeriodSeconds

Match the actual shutdown timing:

| Component | Recommended | Why |
|-----------|-------------|-----|
| NATS | 45s | 10s drain + 15s worker grace + buffer |
| Backend | 60s | Django can take time to finish in-flight requests |
| Celery | 120s | Long-running tasks need time to complete |

### 4. Add preStop hooks for graceful connection drain

```yaml
# For NATS
lifecycle:
  preStop:
    exec:
      command: ["sh", "-c", "sleep 5"]  # Let K8s remove from service endpoints first
```

### 5. Increase backend NATS reconnect attempts

```python
# helpers.py — change from 2 to 10
opts["max_reconnect_attempts"] = 10
```

This prevents the backend from giving up on NATS during a brief restart.
