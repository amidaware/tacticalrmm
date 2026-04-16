# Layer 2: Split nats-server and nats-api into Separate Deployments

**Goal:** Decouple the lifecycle of the NATS message broker from the
telemetry ingestion service, enabling independent scaling, updates, and
the path to NATS HA clustering.

**Depends on:** Layer 1 (reconciliation loop)

**Status:** Design

---

## Problem Statement

Today, nats-server and nats-api run in the same container under
supervisord. This creates multiple problems in Kubernetes:

1. **Coupled lifecycle** -- updating the nats-api Go binary forces a
   nats-server restart, disconnecting all agents.
2. **No HA path** -- NATS clustering requires nats-server to be managed
   as a StatefulSet with stable network identities; it cannot share a
   pod with an unrelated workload.
3. **/proc walk** -- `generate.go:findNatsServerPID()` scans `/proc/*/comm`
   to SIGHUP nats-server. This only works in a shared PID namespace
   and is fragile.
4. **Single failure domain** -- a panic in nats-api's handler can (despite
   recovery) degrade the pod, and a nats-server OOM kills both processes.

---

## Current Coupling Points

| Coupling | Location | Mechanism |
|----------|----------|-----------|
| Shared PID namespace | `generate.go:175-198` | `/proc` walk to find nats-server PID |
| SIGHUP signal | `generate.go:158-168` | `syscall.Kill(pid, SIGHUP)` |
| Shared filesystem | `entrypoint.sh`, `deployment.yaml:97` | `emptyDir` at `/opt/tactical` for nats-rmm.conf |
| Supervisord | `entrypoint.sh:49-78` | Single supervisord manages both processes |
| Combined Docker image | `tactical-nats/Dockerfile` | Go build + nats base image + supervisord |
| Bootstrap ordering | `deployment.yaml:41-54` | Init container runs `nats-api -bootstrap` before either starts |

---

## Target Architecture

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│ nats-server (StatefulSet)   │     │ nats-api (Deployment)        │
│                             │     │                              │
│ Image: nats:2.12-alpine     │     │ Image: tactical-nats-api     │
│        (official, unmodified)│     │        (Go binary only)      │
│                             │     │                              │
│ Config: ConfigMap mount     │     │ Connects to nats-server as   │
│         nats-rmm.conf       │     │ regular NATS client          │
│                             │     │                              │
│ Sidecar: config-reloader    │     │ Responsibilities:            │
│   watches ConfigMap mount   │     │  - Subscribe to agent topics │
│   calls /varz or SIGHUP on  │     │  - Write to Postgres         │
│   config change             │     │  - Reconciliation loop       │
│                             │     │  - Regenerate nats-rmm.conf  │
│ Ports: 4222, 9235, 8222     │     │    via K8s API (ConfigMap)   │
│                             │     │  - Prometheus /metrics       │
│ Can cluster (3 replicas)    │     │                              │
│ Can use PDB                 │     │ Ports: 9189 (metrics)        │
└─────────────────────────────┘     └──────────────────────────────┘
```

---

## Config Delivery: How nats-api Updates nats-server

With the processes in separate pods, nats-api can no longer write a file
and SIGHUP. Three options, in order of recommendation:

### Option A: Shared PVC + Config Reloader Sidecar (Recommended)

```
nats-api pod                      nats-server pod
  │                                 │
  │ writes nats-rmm.conf           │ config-reloader sidecar
  │ to PVC                         │ watches PVC path with fsnotify
  │──────► [ PVC: nats-config ] ──►│ detects change → SIGHUP nats-server
  │                                 │ (shareProcessNamespace: true)
```

- nats-api writes to a ReadWriteMany PVC (or ReadWriteOnce if single-node)
- A config-reloader sidecar in the nats-server pod watches the file
- On change, the sidecar sends SIGHUP to nats-server (needs `shareProcessNamespace: true`)
- The official NATS Helm chart includes a reloader sidecar out of the box

**Pros:** Simple, no K8s API calls, works with official NATS chart.
**Cons:** Requires RWX PVC if nats-api and nats-server are on different nodes.

### Option B: Kubernetes ConfigMap API

```
nats-api pod                      nats-server pod
  │                                 │
  │ PATCH ConfigMap                │ ConfigMap mounted as volume
  │ "tactical-nats-config"         │ K8s updates mount (60-90s delay)
  │──────► [ K8s API ] ──────────►│ config-reloader detects change
  │                                 │ → SIGHUP nats-server
```

- nats-api uses the Kubernetes API to update a ConfigMap
- nats-server mounts the ConfigMap; K8s propagates changes (up to kubelet sync period, ~60s)
- Config-reloader sidecar detects the change and SIGHUPs nats-server

**Pros:** No shared PVC needed, native K8s pattern.
**Cons:** Requires RBAC (ServiceAccount + Role for ConfigMap PATCH), 60-90s propagation delay.

### Option C: NATS Admin HTTP API

```
nats-api pod                      nats-server pod
  │                                 │
  │ writes config to shared vol    │ nats-server admin port 8222
  │ then POST /reload              │
  │──────► [ HTTP :8222 ] ────────►│ nats-server reloads config
```

- nats-server is started with `http_port: 8222` (monitoring + admin)
- nats-api writes the config file, then calls `POST http://tactical-nats:8222/server/config/reload`
- No sidecar needed

**Pros:** Direct, minimal latency, no sidecar.
**Cons:** Requires config file to be accessible to nats-server (still needs shared volume or ConfigMap). NATS admin API may not support remote config reload in all versions.

### Recommendation

**Start with Option A** (shared PVC + reloader sidecar). It's the most
proven pattern, compatible with the official NATS Helm chart, and requires
minimal custom code.

If RWX PVC is not available in the cluster, fall back to **Option B**
(ConfigMap API).

---

## Go Code Changes

### Remove from generate.go

```go
// DELETE: findNatsServerPID() — lines 175-198
// DELETE: SignalNatsServerReload() — lines 158-168
// DELETE: ErrNatsServerNotFound sentinel — lines 170-173
```

### New: configWriter interface

Abstract the config delivery mechanism so it can be swapped:

```go
// configWriter delivers a fresh nats-rmm.conf to wherever nats-server
// reads it from. Implementations: file write (current), ConfigMap patch,
// or HTTP push.
type configWriter interface {
    WriteConfig(ctx context.Context, data []byte) error
}

// fileConfigWriter writes to a local/shared filesystem path (Option A).
type fileConfigWriter struct {
    path string
}

func (w *fileConfigWriter) WriteConfig(_ context.Context, data []byte) error {
    // Existing atomic write logic from GenerateNatsRmmConfig
    return atomicWriteFile(w.path, data, 0o660)
}

// configMapWriter patches a Kubernetes ConfigMap (Option B).
type configMapWriter struct {
    client    kubernetes.Interface
    namespace string
    name      string
    key       string
}

func (w *configMapWriter) WriteConfig(ctx context.Context, data []byte) error {
    cm, err := w.client.CoreV1().ConfigMaps(w.namespace).Get(ctx, w.name, metav1.GetOptions{})
    if err != nil {
        return err
    }
    cm.Data[w.key] = string(data)
    _, err = w.client.CoreV1().ConfigMaps(w.namespace).Update(ctx, cm, metav1.UpdateOptions{})
    return err
}
```

### Update svc.go reload subscriber

```go
// OLD (lines 355-375):
//   GenerateNatsRmmConfig(logger, db, r.Key, natsRmmConfigPath)
//   SignalNatsServerReload(logger)
//
// NEW:
//   data := GenerateNatsRmmConfigBytes(logger, db, r.Key)
//   writer.WriteConfig(ctx, data)
//   // No SIGHUP — the config-reloader sidecar or K8s handles it.
```

### Update reconciliation loop (from Layer 1)

Same change: replace `GenerateNatsRmmConfig + SignalNatsServerReload`
with `writer.WriteConfig`.

---

## Docker Image Split

### Image 1: tactical-nats-api (new)

```dockerfile
FROM golang:1.26-alpine AS build
ARG TARGETOS TARGETARCH
WORKDIR /src
COPY natsapi/go.mod natsapi/go.sum ./
RUN go mod download
COPY natsapi/ ./
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -trimpath -ldflags "-s -w" -o /out/nats-api ./cmd/nats-api

FROM alpine:3.19
RUN apk add --no-cache ca-certificates
COPY --from=build /out/nats-api /usr/local/bin/nats-api
USER 1000
EXPOSE 9189
ENTRYPOINT ["/usr/local/bin/nats-api"]
```

No supervisord, no nats-server binary, no bash. Just the Go binary.

### Image 2: nats-server

Use the **official unmodified** `nats:2.12-alpine` image.
No custom Dockerfile needed.

### Backward compatibility (Docker Compose)

Keep the existing combined `tactical-nats` Dockerfile for Docker Compose
users who want the single-container experience. Gate the split behind a
compose profile or separate compose file:

```yaml
# docker-compose.k8s.yml (or profile: k8s)
services:
  tactical-nats-server:
    image: nats:2.12-alpine
    command: ["nats-server", "--config", "/etc/nats/nats-rmm.conf"]
    volumes:
      - nats-config:/etc/nats
    ports:
      - "4222:4222"
      - "9235:9235"

  tactical-nats-api:
    image: tactical-nats-api:latest
    depends_on: [tactical-nats-server, tactical-postgres]
    environment:
      NATS_CONNECT_HOST: tactical-nats-server
      NATS_CONFIG: /etc/nats/nats-rmm.conf
    volumes:
      - nats-config:/etc/nats
```

---

## Helm Chart Changes

### New templates

```
charts/tacticalrmm/templates/nats-api/
  deployment.yaml       # nats-api as a Deployment
  service.yaml          # ClusterIP for metrics scraping
  configmap.yaml        # nats-api.conf
  serviceaccount.yaml   # If using Option B (ConfigMap writer)
  role.yaml             # ConfigMap PATCH permission
  rolebinding.yaml

charts/tacticalrmm/templates/nats-server/
  statefulset.yaml      # nats-server (or replaced by subchart)
  service.yaml          # ClusterIP: 4222, 9235
  configmap.yaml        # Initial nats-rmm.conf (bootstrap)
  pvc.yaml              # Shared config volume (Option A)
```

### values.yaml additions

```yaml
tactical-nats-server:
  enabled: true
  image:
    repository: nats
    tag: "2.12-alpine"
  replicas: 1                # Increase to 3 for clustering (Layer 3)
  resources:
    requests: { cpu: 50m, memory: 128Mi }
    limits:   { cpu: 100m, memory: 256Mi }
  configReloader:
    enabled: true
    image: natsio/nats-server-config-reloader:0.16.1

tactical-nats-api:
  enabled: true
  image:
    registry: ghcr.io/flamingo-stack/tacticalrmm
    repository: tactical-nats-api
    tag: latest
  replicas: 1
  logLevel: INFO
  reconcileInterval: "30s"
  configDelivery: file        # "file" (Option A) or "configmap" (Option B)
  resources:
    requests: { cpu: 50m, memory: 256Mi }
    limits:   { cpu: 100m, memory: 512Mi }
```

### nats-server StatefulSet with config-reloader sidecar

Note: `shareProcessNamespace: true` is required so the config-reloader
sidecar can send SIGHUP to the nats-server process in the same pod.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: tactical-nats-server
spec:
  replicas: {{ (index .Values "tactical-nats-server").replicas }}
  serviceName: tactical-nats-server
  template:
    spec:
      shareProcessNamespace: true   # Required for sidecar SIGHUP
      containers:
        - name: nats-server
          image: nats:2.12-alpine
          args: ["--config", "/etc/nats/nats-rmm.conf"]
          ports:
            - containerPort: 4222
            - containerPort: 9235
            - containerPort: 8222
          volumeMounts:
            - name: nats-config
              mountPath: /etc/nats

        - name: config-reloader
          image: natsio/nats-server-config-reloader:0.16.1
          args:
            - "-config"
            - "/etc/nats/nats-rmm.conf"
            - "-pid"
            - "1"  # nats-server is PID 1 in shared namespace
          volumeMounts:
            - name: nats-config
              mountPath: /etc/nats

      volumes:
        - name: nats-config
          persistentVolumeClaim:
            claimName: nats-config   # Shared with nats-api
```

### nats-api Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tactical-nats-api
spec:
  replicas: 1
  template:
    spec:
      initContainers:
        - name: bootstrap
          image: {{ .Values.tactical-nats-api.image }}
          command: ["/usr/local/bin/nats-api", "-bootstrap", "-out", "/etc/nats/nats-rmm.conf"]
          envFrom: [...]
          volumeMounts:
            - name: nats-config
              mountPath: /etc/nats

      containers:
        - name: nats-api
          image: {{ .Values.tactical-nats-api.image }}
          args: ["-config", "/etc/nats-api/nats-api.conf"]
          env:
            - name: NATS_CONNECT_HOST
              value: tactical-nats-server.{{ .Release.Namespace }}.svc.cluster.local
            - name: NATS_CONFIG
              value: /etc/nats/nats-rmm.conf   # Write path for config
            - name: RECONCILE_INTERVAL
              value: "30s"
          volumeMounts:
            - name: nats-config
              mountPath: /etc/nats
            - name: nats-api-config
              mountPath: /etc/nats-api

      volumes:
        - name: nats-config
          persistentVolumeClaim:
            claimName: nats-config
        - name: nats-api-config
          configMap:
            name: tactical-nats-api
```

---

## Startup Sequence (Post-Split)

```
1. PostgreSQL + Redis start (no change)
2. tactical-backend starts, runs migrations
3. tactical-nats-api init container:
   - Waits for Postgres + backend
   - Runs nats-api -bootstrap → writes nats-rmm.conf to shared PVC
4. tactical-nats-server starts:
   - Reads nats-rmm.conf from shared PVC
   - Config-reloader sidecar starts watching
5. tactical-nats-api main container starts:
   - Connects to nats-server as client (tacticalrmm/SECRET_KEY)
   - Subscribes to agent subjects + trmm.nats.reload
   - Starts reconciliation loop
```

---

## Migration Path

| Phase | Change | Risk |
|-------|--------|------|
| 1 | Build separate tactical-nats-api Docker image | None (additive) |
| 2 | Add new Helm templates alongside existing ones, gated by feature flag | None (opt-in) |
| 3 | Refactor Go code: extract `configWriter` interface, remove `/proc` walk behind flag | Low (feature-flagged) |
| 4 | Deploy split architecture in staging | Medium (integration testing) |
| 5 | Flip production to split architecture | Medium (rollback available) |
| 6 | Remove legacy combined templates + Dockerfile | Low (cleanup) |

---

## Files to Change

### Go (natsapi/)

| File | Change |
|------|--------|
| `generate.go` | Extract `configWriter` interface; move `findNatsServerPID`/`SignalNatsServerReload` behind build tag or env flag |
| `svc.go` | Use `configWriter` in reload subscriber and reconciliation loop |
| `cmd/nats-api/main.go` | Add `-config-delivery` flag (`file` or `configmap`) |
| `configmap_writer.go` | New file: Kubernetes ConfigMap writer implementation |
| `go.mod` | Add `k8s.io/client-go` dependency (only if Option B). Note: `nats-io/nkeys` is already an indirect dep (go.mod:24) |

### Docker

| File | Change |
|------|--------|
| `docker/containers/tactical-nats-api/Dockerfile` | New: standalone nats-api image |
| `docker/containers/tactical-nats/Dockerfile` | Keep for Docker Compose backward compat |

### Helm (charts/tacticalrmm/)

| File | Change |
|------|--------|
| `templates/nats-api/deployment.yaml` | New |
| `templates/nats-api/service.yaml` | New |
| `templates/nats-api/configmap.yaml` | New |
| `templates/nats-server/statefulset.yaml` | New (or replace with subchart) |
| `templates/nats-server/service.yaml` | New |
| `templates/nats-server/pvc.yaml` | New: shared config PVC |
| `templates/nats/deployment.yaml` | Deprecate (keep behind legacy flag) |
| `values.yaml` | Add `tactical-nats-server` and `tactical-nats-api` sections |
