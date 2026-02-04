# Y12.AI Deployment on Cloudflare Containers

This guide covers deploying Y12.AI on Cloudflare Containers with external managed services.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare Edge Network                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Frontend   │  │   Backend   │  │     WebSockets      │  │
│  │  (Vue.js)   │  │  (Django)   │  │   (Django ASGI)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    NATS     │  │   Celery    │  │    Celery Beat      │  │
│  │  (Agents)   │  │  (Workers)  │  │    (Scheduler)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
      │   Neon DB   │ │   Upstash   │ │  Cloudflare │
      │ (PostgreSQL)│ │   (Redis)   │ │     R2      │
      └─────────────┘ └─────────────┘ └─────────────┘
```

## Prerequisites

1. **Cloudflare Account** with Containers access (currently in beta)
2. **Wrangler CLI** v3.0+
3. **External Services**:
   - PostgreSQL: [Neon](https://neon.tech) or [Supabase](https://supabase.com)
   - Redis: [Upstash](https://upstash.com)
   - File Storage: Cloudflare R2

## Step 1: Set Up External Services

### PostgreSQL (Neon - Recommended)

1. Create account at https://neon.tech
2. Create new project "y12-ai"
3. Copy connection string:
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/y12ai?sslmode=require
   ```

### Redis (Upstash)

1. Create account at https://upstash.com
2. Create Redis database in closest region
3. Copy Redis URL:
   ```
   rediss://default:xxx@us1-xxx.upstash.io:6379
   ```

### Cloudflare R2 (File Storage)

1. Go to Cloudflare Dashboard > R2
2. Create bucket "y12-assets"
3. Generate API credentials

## Step 2: Configure Wrangler

```bash
# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Set secrets
wrangler secret put DATABASE_URL
# Paste: postgresql://user:password@ep-xxx.neon.tech/y12ai?sslmode=require

wrangler secret put REDIS_URL
# Paste: rediss://default:xxx@us1-xxx.upstash.io:6379

wrangler secret put SECRET_KEY
# Paste: your-random-secret-key-min-50-chars

wrangler secret put ALLOWED_HOSTS
# Paste: y12.ai,api.y12.ai,ws.y12.ai

wrangler secret put CORS_ORIGIN_WHITELIST
# Paste: https://y12.ai
```

## Step 3: Build and Push Container Images

```bash
# Navigate to project root
cd /path/to/y12-ai

# Build backend image
docker build -t y12ai/y12-backend:latest -f docker/containers/tactical/dockerfile .

# Build frontend image
docker build -t y12ai/y12-frontend:latest -f docker/containers/tactical-frontend/dockerfile .

# Build NATS image
docker build -t y12ai/y12-nats:latest -f docker/containers/tactical-nats/dockerfile .

# Push to Cloudflare Container Registry
wrangler containers registry login
docker tag y12ai/y12-backend:latest registry.cloudflare.com/y12ai/y12-backend:latest
docker push registry.cloudflare.com/y12ai/y12-backend:latest

docker tag y12ai/y12-frontend:latest registry.cloudflare.com/y12ai/y12-frontend:latest
docker push registry.cloudflare.com/y12ai/y12-frontend:latest

docker tag y12ai/y12-nats:latest registry.cloudflare.com/y12ai/y12-nats:latest
docker push registry.cloudflare.com/y12ai/y12-nats:latest
```

## Step 4: Deploy to Cloudflare

```bash
# Deploy all containers
cd cloudflare
wrangler containers deploy

# Run database migrations
wrangler containers exec y12-backend -- python manage.py migrate

# Create superuser
wrangler containers exec y12-backend -- python manage.py createsuperuser
```

## Step 5: Configure DNS

In Cloudflare Dashboard:

| Type  | Name | Content              | Proxy |
|-------|------|----------------------|-------|
| CNAME | @    | y12-frontend.containers.cloudflare.com | ✓ |
| CNAME | api  | y12-backend.containers.cloudflare.com  | ✓ |
| CNAME | ws   | y12-websockets.containers.cloudflare.com | ✓ |

## Step 6: Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Update OAuth credentials:
   - Authorized JavaScript origins: `https://y12.ai`
   - Authorized redirect URIs: `https://api.y12.ai/accounts/google/login/callback/`

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `rediss://...` |
| `SECRET_KEY` | Django secret key | Random 50+ chars |
| `ALLOWED_HOSTS` | Allowed hostnames | `y12.ai,api.y12.ai` |
| `CORS_ORIGIN_WHITELIST` | CORS origins | `https://y12.ai` |
| `API_HOST` | API hostname | `api.y12.ai` |
| `APP_HOST` | App hostname | `y12.ai` |

## Limitations & Considerations

### What Works on Cloudflare Containers
- ✅ Django backend API
- ✅ Vue.js frontend
- ✅ Celery workers
- ✅ WebSocket connections
- ✅ NATS agent communication

### What Needs External Services
- ⚠️ PostgreSQL → Use Neon or Supabase
- ⚠️ Redis → Use Upstash
- ⚠️ File storage → Use Cloudflare R2
- ⚠️ MeshCentral → Needs separate VPS (see below)

### MeshCentral (Remote Desktop)

MeshCentral requires persistent connections and MongoDB. Options:

1. **Separate VPS**: Run MeshCentral on a small VPS ($5/mo DigitalOcean)
2. **Skip MeshCentral**: Disable remote desktop features
3. **Use alternative**: Integrate with Cloudflare Browser Isolation

To disable MeshCentral:
```python
# In local_settings.py
MESH_ENABLED = False
```

## Cost Estimate

| Service | Free Tier | Paid Estimate |
|---------|-----------|---------------|
| Cloudflare Containers | Beta (free) | ~$20-50/mo |
| Neon PostgreSQL | 0.5GB free | ~$19/mo |
| Upstash Redis | 10K commands/day | ~$10/mo |
| Cloudflare R2 | 10GB free | ~$5/mo |
| **Total** | **Free tier possible** | **~$35-85/mo** |

## Monitoring & Logs

```bash
# View container logs
wrangler containers logs y12-backend

# View all containers status
wrangler containers list

# Scale containers
wrangler containers scale y12-celery --replicas=3
```

## Troubleshooting

### Database Connection Issues
```bash
# Test database connection
wrangler containers exec y12-backend -- python -c "from django.db import connection; connection.ensure_connection(); print('OK')"
```

### Redis Connection Issues
```bash
# Test Redis connection
wrangler containers exec y12-backend -- python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"
```

### Container Not Starting
```bash
# Check container logs
wrangler containers logs y12-backend --tail=100

# Restart container
wrangler containers restart y12-backend
```

## Alternative: Hybrid Deployment

For production, consider a hybrid approach:

1. **Frontend on Cloudflare Pages** (free, fast CDN)
2. **Backend on Cloudflare Containers** (containerized)
3. **Database on Neon** (serverless PostgreSQL)
4. **MeshCentral on small VPS** (for remote desktop)

This gives you the best of both worlds: edge performance for frontend, managed containers for backend, and full functionality with MeshCentral.
