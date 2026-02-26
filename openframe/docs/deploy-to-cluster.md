# Deploying Python Code Changes to Cluster (Hot Deploy)

For testing Django/Python changes in the running cluster without rebuilding the Docker image.

---

## When to use this

- Quick iteration on API views, serializers, filters
- Testing a new endpoint before committing
- Debugging in the live cluster environment

**Not suitable for:** migrations, new dependencies, changes to Go code (`natsapi`), Dockerfile changes.

---

## Prerequisites

- `kubectl` configured with access to the cluster
- Changes made locally in `api/tacticalrmm/`

---

## Steps

### 1. Find the API pod

```bash
kubectl get pods -n integrated-tools | grep tactical-backend
```

Expected output:
```
tactical-backend-0   1/1   Running   0   141m
```

### 2. Copy changed files into the pod

The API code lives at `/opt/tactical/api/` inside the pod.

**Copy a single file:**
```bash
kubectl cp api/tacticalrmm/scripts/views.py \
  integrated-tools/tactical-backend-0:/opt/tactical/api/scripts/views.py
```

**Copy a new directory:**
```bash
# Create directory first
kubectl exec -n integrated-tools tactical-backend-0 -- mkdir -p /opt/tactical/api/v2/scripts

# Copy files
kubectl cp api/tacticalrmm/v2/__init__.py \
  integrated-tools/tactical-backend-0:/opt/tactical/api/v2/__init__.py

kubectl cp api/tacticalrmm/v2/urls.py \
  integrated-tools/tactical-backend-0:/opt/tactical/api/v2/urls.py

kubectl cp api/tacticalrmm/v2/scripts/__init__.py \
  integrated-tools/tactical-backend-0:/opt/tactical/api/v2/scripts/__init__.py

kubectl cp api/tacticalrmm/v2/scripts/views.py \
  integrated-tools/tactical-backend-0:/opt/tactical/api/v2/scripts/views.py

kubectl cp api/tacticalrmm/v2/scripts/filter.py \
  integrated-tools/tactical-backend-0:/opt/tactical/api/v2/scripts/filter.py
```

**Update urls.py:**
```bash
kubectl cp api/tacticalrmm/tacticalrmm/urls.py \
  integrated-tools/tactical-backend-0:/opt/tactical/api/tacticalrmm/urls.py
```

### 3. Reload uWSGI

uWSGI runs as PID 1076 (check with `ps aux | grep uwsgi` if differs). Send `HUP` signal to reload workers without downtime:

```bash
kubectl exec -n integrated-tools tactical-backend-0 -- kill -HUP $(kubectl exec -n integrated-tools tactical-backend-0 -- ps aux | grep 'uwsgi.*app.ini' | head -1 | awk '{print $1}')
```

Or with a known PID:
```bash
kubectl exec -n integrated-tools tactical-backend-0 -- kill -HUP 1076
```

### 4. Verify routes are registered

```bash
kubectl exec -n integrated-tools tactical-backend-0 -- \
  python /opt/tactical/api/manage.py show_urls | grep v2
```

### 5. Port-forward for local testing

```bash
kubectl port-forward -n integrated-tools tactical-backend-0 8000:8000
```

API is now available at `http://localhost:8000`.

---

## Testing the endpoint

Get a token from TacticalRMM UI: **Settings → API Keys** or use login:

```bash
curl -s -X POST http://localhost:8000/v2/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}' | python -m json.tool
```

Use the token:
```bash
TOKEN="your-token-here"

# List scripts
curl -s http://localhost:8000/v2/scripts/ \
  -H "Authorization: Token $TOKEN" | python -m json.tool

# Search
curl -s "http://localhost:8000/v2/scripts/?search=backup" \
  -H "Authorization: Token $TOKEN" | python -m json.tool

# Filter + paginate
curl -s "http://localhost:8000/v2/scripts/?shell=powershell&page=1&page_size=10" \
  -H "Authorization: Token $TOKEN" | python -m json.tool
```

---

## Caveats

| Limitation | Notes |
|---|---|
| Changes are lost on pod restart | Pod restart pulls original image. For permanent changes — commit and rebuild |
| Only `tactical-backend-0` | `tactical-celery` and `tactical-websockets` don't serve HTTP API |
| No migrations | Changes to `models.py` require a proper rebuild with `manage.py migrate` |
| `__pycache__` stale bytecode | If behaviour is unexpected after reload, delete `.pyc` files: `kubectl exec -n integrated-tools tactical-backend-0 -- find /opt/tactical/api/v2 -name "*.pyc" -delete` |
