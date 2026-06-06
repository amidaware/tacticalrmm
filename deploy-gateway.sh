#!/bin/bash
set -e

# SSH Gateway deploy script
# Pulls latest from ssh-gateway branch, runs migrations, restarts services
# Works on vanilla TRMM install (assumes /rmm git repo exists from initial setup)

FORCE=""
DEPLOY_USER="tactical"

usage() {
    echo "Usage: $0 [--force] [--user <username>]"
    echo "  --force    Hard reset to origin/ssh-gateway (discards local changes)"
    echo "  --user     Server user to deploy as (default: tactical)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE="yes"
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

# Check if running as correct user
if [ "$(whoami)" != "$DEPLOY_USER" ]; then
    error "Must run as $DEPLOY_USER"
    exit 1
fi

info "Starting SSH Gateway deployment..."

# Ensure we're in the TRMM directory
cd /rmm

# Verify this is a git repo
if [ ! -d .git ]; then
    error "/rmm is not a git repository. Run TRMM install.sh first."
    exit 1
fi

# Check if our fork remote exists, if not add it
if ! git remote | grep -q "^p6g9$"; then
    info "Adding p6g9 fork as remote..."
    git remote add p6g9 git@github.com:P6g9YHK6/tacticalrmm.git
fi

# Fetch latest from fork
info "Fetching latest from p6g9/ssh-gateway..."
git fetch p6g9

# Pull latest from ssh-gateway branch
if [ "$FORCE" = "yes" ]; then
    info "Force pulling ssh-gateway branch (discard local changes)..."
    git reset --hard p6g9/ssh-gateway
else
    info "Pulling latest from p6g9/ssh-gateway..."
    # Try fast-forward only, fail if not possible
    git merge --ff-only p6g9/ssh-gateway 2>/dev/null || {
        info "Non-fast-forward update required. Use --force to discard local changes."
        exit 1
    }
fi

GIT_COMMIT=$(git rev-parse --short HEAD)
info "Deployed commit: $GIT_COMMIT"

# Run migrations
info "Running migrations..."
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
python manage.py migrate --no-input

# Collect static files
info "Collecting static files..."
python manage.py collectstatic --noinput --clear

deactivate

# Restart services
info "Restarting services..."
sudo systemctl restart trmm-api trmm-gateway trmm celery >/dev/null 2>&1 || true

# Verify gateway is running
sleep 2
if systemctl is-active --quiet trmm-gateway; then
    info "Gateway service is running"
else
    error "Gateway service may not have started properly"
fi

info "Deployment complete (commit: $GIT_COMMIT)"