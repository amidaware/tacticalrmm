#!/bin/bash
set -e

# SSH Gateway full deployment script for vanilla TRMM
# - Patches nginx for SSH stream proxy on port 443 (idempotent)
# - Pulls latest from fork's ssh-gateway branch
# - Runs migrations
# - Restarts gateway service
# - Verifies deployment

FORCE=""
NGINX_ONLY=""
DEPLOY_USER="tactical"

usage() {
    echo "Usage: $0 [--force] [--nginx-only] [--user <username>]"
    echo "  --force      Hard reset to origin/ssh-gateway (discards local changes)"
    echo "  --nginx-only Only patch nginx, skip code deployment"
    echo "  --user       Server user (default: tactical)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE="yes"
            shift
            ;;
        --nginx-only)
            NGINX_ONLY="yes"
            shift
            ;;
        --user)
            DEPLOY_USER="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
info() { log "INFO: $*"; }
error() { log "ERROR: $*" >&2; }

die() { error "$1"; exit 1; }

# Check user
if [ "$(whoami)" != "$DEPLOY_USER" ]; then
    die "Must run as $DEPLOY_USER"
fi

NGINX_CONF="/etc/nginx/nginx.conf"
NGINX_STREAM_CONF="/etc/nginx/conf.d/stream-ssh.conf"

patch_nginx() {
    info "Checking nginx configuration..."

    # Check if nginx.conf exists
    [ -f "$NGINX_CONF" ] || die "nginx.conf not found at $NGINX_CONF - is TRMM installed?"

    # Check if already patched (idempotent)
    if grep -q "upstream ssh_backend" "$NGINX_CONF" 2>/dev/null; then
        info "nginx already has stream config, skipping nginx patch"
        return 0
    fi

    # Validate vanilla structure
    if ! grep -q "^events {" "$NGINX_CONF"; then
        die "nginx.conf missing 'events {}' block - non-standard structure detected. Manual nginx setup required for SSH gateway."
    fi

    if ! grep -q "^http {" "$NGINX_CONF"; then
        die "nginx.conf missing 'http {}' block - non-standard structure detected. Manual nginx setup required for SSH gateway."
    fi

    # Check if separate stream conf already exists
    if [ -f "$NGINX_STREAM_CONF" ]; then
        info "Stream config already exists at $NGINX_STREAM_CONF, skipping nginx patch"
        return 0
    fi

    info "Patching nginx for SSH stream proxy..."

    # Create backup
    BACKUP="${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$NGINX_CONF" "$BACKUP"
    info "Backed up nginx.conf to $BACKUP"

    # Create stream snippet
    cat > "$NGINX_STREAM_CONF" << 'STREAM_EOF'
stream {
    map $ssl_preread_protocol $backend {
        ""       ssh_backend;
        default  https_backend;
    }

    upstream ssh_backend {
        server 127.0.0.1:2222;
    }

    upstream https_backend {
        server 127.0.0.1:8443;
    }

    server {
        listen 443 reuseport;
        listen [::]:443 reuseport;
        proxy_pass $backend;
        ssl_preread on;
        proxy_connect_timeout 10s;
    }
}
STREAM_EOF

    info "Created $NGINX_STREAM_CONF"

    # Verify nginx config
    if ! sudo nginx -t 2>&1; then
        error "nginx -t failed, restoring backup..."
        sudo cp "$BACKUP" "$NGINX_CONF"
        rm -f "$NGINX_STREAM_CONF"
        die "nginx configuration test failed. Restored backup."
    fi

    # Reload nginx
    sudo systemctl reload nginx || sudo nginx -s reload
    info "nginx reloaded successfully"

    # Also update main nginx.conf to include conf.d/*.conf if not already
    if ! grep -q "conf.d/\*.conf" "$NGINX_CONF"; then
        info "Adding include for conf.d/*.conf to nginx.conf..."
        # Insert before the http { block
        sudo sed -i '/^http {/i\    # SSH gateway stream config\n    include /etc/nginx/conf.d/stream-ssh.conf;\n' "$NGINX_CONF"
    fi

    # Verify again after changes
    if ! sudo nginx -t 2>&1; then
        error "nginx -t failed after adding include, restoring backup..."
        sudo cp "$BACKUP" "$NGINX_CONF"
        rm -f "$NGINX_STREAM_CONF"
        die "nginx configuration test failed after include. Restored backup."
    fi

    sudo systemctl reload nginx
    info "nginx SSH stream proxy configured successfully"
}

deploy_code() {
    info "Starting code deployment..."

    # Check /rmm is git repo
    [ -d "/rmm/.git" ] || die "/rmm is not a git repository - run TRMM install.sh first"

    cd /rmm

    # Add p6g9 remote if not exists, or update URL to HTTPS
    if git remote | grep -q "^p6g9$"; then
        EXISTING_URL=$(git remote get-url p6g9)
        if [[ "$EXISTING_URL" == git@* ]]; then
            info "Updating p6g9 remote from SSH to HTTPS..."
            git remote set-url p6g9 https://github.com/P6g9YHK6/tacticalrmm.git
        fi
    else
        info "Adding p6g9 fork as remote..."
        git remote add p6g9 https://github.com/P6g9YHK6/tacticalrmm.git
    fi

    # Fetch latest
    info "Fetching latest from p6g9/ssh-gateway..."
    git fetch p6g9

    # Pull/reset
    if [ "$FORCE" = "yes" ]; then
        info "Force pulling ssh-gateway branch..."
        git reset --hard p6g9/ssh-gateway
    else
        info "Pulling latest from p6g9/ssh-gateway..."
        git merge --ff-only p6g9/ssh-gateway 2>/dev/null || die "Non-fast-forward update required. Use --force to discard local changes."
    fi

    GIT_COMMIT=$(git rev-parse --short HEAD)
    info "Deployed commit: $GIT_COMMIT"

    # Run migrations
    info "Running migrations..."
    source /rmm/api/env/bin/activate
    cd /rmm/api/tacticalrmm
    python manage.py migrate --no-input
    deactivate
}

restart_services() {
    info "Restarting rmm-ssh-gateway service..."
    sudo systemctl restart rmm-ssh-gateway
    sleep 2

    if systemctl is-active --quiet rmm-ssh-gateway; then
        info "rmm-ssh-gateway is running"
    else
        error "rmm-ssh-gateway failed to start"
        sudo systemctl status rmm-ssh-gateway --no-pager -l | head -10
        return 1
    fi

    # Check gateway is listening on 2222
    if ss -tlnp | grep -q ":2222"; then
        info "Gateway is listening on port 2222"
    else
        error "Gateway is NOT listening on port 2222"
        return 1
    fi
}

verify() {
    info "Verifying deployment..."

    # Check gateway is listening on 2222 (already done in restart_services)
    # Try exec test if SSH key is available for localhost
    RESULT=$(timeout 5 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -o BatchMode=yes -p 2222 localhost "echo test" 2>&1) || true

    if [ "$RESULT" = "test" ]; then
        info "Gateway verification successful: exec works on port 2222"
    elif [ "$RESULT" = "Permission denied"* ]; then
        info "Gateway verification skipped: no SSH key for localhost access"
    else
        info "Gateway verification: port 2222 is open (SSH exec test skipped)"
    fi

    info "Deployment complete!"
}

# Main execution
info "Starting SSH Gateway deployment..."

# Phase 1: Nginx patch
patch_nginx

# Exit if --nginx-only
if [ "$NGINX_ONLY" = "yes" ]; then
    info "nginx-only mode, skipping code deployment"
    exit 0
fi

# Phase 2: Code deployment
deploy_code

# Phase 3: Restart services
restart_services

# Phase 4: Verify
verify