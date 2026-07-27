#!/usr/bin/env bash
#
# Pi.dev AI assistant bridge — idempotent setup.
# Called by install.sh (fresh install) and update.sh (upgrades).
#
# Deploys the Node bridge to /opt/pi-trmm-bridge, installs its npm deps
# (including the pi coding-agent SDK), writes the systemd unit and env file,
# ensures a TRMM service API key exists, injects the nginx /pi/ location block
# if missing, and (re)starts the service.
#
# Assumptions (match the TRMM installer environment):
#   - runs as the non-root TRMM user with passwordless sudo
#   - repo checked out at /rmm, api venv at /rmm/api/env
#   - nodejs + npm already installed (TRMM installer sets these up)
#   - redis reachable at 127.0.0.1:6379

set -euo pipefail

REPO_DIR="${REPO_DIR:-/rmm}"
BRIDGE_SRC="${REPO_DIR}/pibridge"
BRIDGE_DIR="/opt/pi-trmm-bridge"
ENV_FILE="/etc/pi-trmm-bridge.env"
UNIT_FILE="/etc/systemd/system/pi-trmm-bridge.service"
NGINX_CONF="/etc/nginx/sites-available/rmm.conf"
PY="${REPO_DIR}/api/env/bin/python"
MANAGE="${REPO_DIR}/api/tacticalrmm/manage.py"
TRMM_USER="$(whoami)"

GREEN='\033[0;32m'; NC='\033[0m'
info() { printf "${GREEN}%s${NC}\n" "$1"; }

# --- 1. deploy bridge code -------------------------------------------------
info "Deploying Pi bridge to ${BRIDGE_DIR}"
sudo mkdir -p "${BRIDGE_DIR}"
sudo cp -r "${BRIDGE_SRC}/src" "${BRIDGE_DIR}/"
sudo cp "${BRIDGE_SRC}/package.json" "${BRIDGE_DIR}/"
sudo chown -R "${TRMM_USER}:${TRMM_USER}" "${BRIDGE_DIR}"

# --- 2. install npm deps (pi SDK, ws, ioredis) -----------------------------
info "Installing Pi bridge npm dependencies"
cd "${BRIDGE_DIR}"
npm install --omit=dev --no-audit --no-fund
# the pi coding-agent SDK provides the AI runtime the bridge embeds
npm install --no-audit --no-fund @earendil-works/pi-coding-agent

# --- 3. service API key (idempotent) ---------------------------------------
info "Ensuring TRMM service API key for the bridge"
API_KEY="$(
  cd "${REPO_DIR}/api/tacticalrmm"
  "${PY}" "${MANAGE}" shell -c "
import secrets, string
from accounts.models import User, APIKey, Role
role, _ = Role.objects.get_or_create(name='pi-bridge-service')
for perm in ['can_list_agents','can_send_cmd','can_run_scripts','can_manage_procs','can_view_eventlogs','can_reboot_agents','can_list_software','can_list_scripts','can_list_checks','can_list_autotasks','can_use_ai']:
    setattr(role, perm, True)
role.save()
user, created = User.objects.get_or_create(username='pi-bridge-service', defaults={'is_active': True})
user.role = role; user.block_dashboard_login = True
if created: user.set_unusable_password()
user.save()
ak = APIKey.objects.filter(name='pi-bridge').first()
if not ak:
    key = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(48))
    ak = APIKey.objects.create(name='pi-bridge', key=key, user=user)
print(ak.key)
" 2>/dev/null | tail -1
)"

# --- 4. derive API url from allowed hosts ----------------------------------
API_URL="$(
  cd "${REPO_DIR}/api/tacticalrmm"
  "${PY}" "${MANAGE}" shell -c "
from django.conf import settings
h = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else '127.0.0.1'
print('https://' + h)
" 2>/dev/null | tail -1
)"

# --- 5. env file -----------------------------------------------------------
info "Writing ${ENV_FILE}"
sudo tee "${ENV_FILE}" >/dev/null <<EOF
PORT=8787
HOST=127.0.0.1
REDIS_URL=redis://127.0.0.1:6379
TRMM_API_URL=${API_URL}
TRMM_API_KEY=${API_KEY}
PI_SESSIONS_ROOT=${BRIDGE_DIR}/sessions
IDLE_TIMEOUT_MS=1800000
MAX_SESSIONS=10
EOF
sudo chmod 600 "${ENV_FILE}"
sudo mkdir -p "${BRIDGE_DIR}/sessions"
sudo chown -R "${TRMM_USER}:${TRMM_USER}" "${BRIDGE_DIR}/sessions"

# --- 6. systemd unit -------------------------------------------------------
info "Writing ${UNIT_FILE}"
NODE_BIN="$(command -v node)"
sudo tee "${UNIT_FILE}" >/dev/null <<EOF
[Unit]
Description=Pi.dev <-> Tactical RMM bridge (per-device AI assistant)
After=network.target redis-server.service nats.service
Wants=network.target

[Service]
Type=simple
User=${TRMM_USER}
Group=${TRMM_USER}
WorkingDirectory=${BRIDGE_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${NODE_BIN} ${BRIDGE_DIR}/src/server.js
Restart=always
RestartSec=3
StandardOutput=append:/var/log/pi-trmm-bridge.log
StandardError=append:/var/log/pi-trmm-bridge.log

[Install]
WantedBy=multi-user.target
EOF
sudo touch /var/log/pi-trmm-bridge.log
sudo chown "${TRMM_USER}:${TRMM_USER}" /var/log/pi-trmm-bridge.log

# --- 7. nginx /pi/ location (idempotent inject for existing installs) ------
if [ -f "${NGINX_CONF}" ] && ! grep -q "location ~ \^/pi/" "${NGINX_CONF}"; then
  info "Injecting nginx /pi/ location block"
  sudo python3 - "${NGINX_CONF}" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
block = '''    # Pi.dev AI assistant bridge (WebSocket + HTTP)
    location ~ ^/pi/ {
        proxy_pass http://127.0.0.1:8787;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location / {
        uwsgi_pass  tacticalrmm;'''
needle = '''    location / {
        uwsgi_pass  tacticalrmm;'''
if 'location ~ ^/pi/' not in s and needle in s:
    s = s.replace(needle, block, 1)
    open(p, 'w').write(s)
    print("injected")
else:
    print("skip")
PYEOF
  sudo nginx -t && sudo systemctl reload nginx || true
fi

# --- 8. enable + (re)start -------------------------------------------------
info "Enabling and starting pi-trmm-bridge.service"
sudo systemctl daemon-reload
sudo systemctl enable pi-trmm-bridge.service >/dev/null 2>&1 || true
sudo systemctl restart pi-trmm-bridge.service

info "Pi bridge setup complete."
