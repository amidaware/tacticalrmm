#!/usr/bin/env bash

set -euo pipefail

: "${DEV:=0}"

if [ "${DEV}" = 1 ]; then
  NATS_CONFIG=/workspace/api/tacticalrmm/nats-rmm.conf
  NATS_API_CONFIG=/workspace/api/tacticalrmm/nats-api.conf
else
  # Defaults match the backend's entrypoint defaults for Docker Compose
  # compatibility. In K8s, the tactical-backend ConfigMap overrides these
  # env vars to /opt/tactical/{nats-rmm,nats-api}.conf.
  : "${NATS_CONFIG:=${TACTICAL_DIR}/api/nats-rmm.conf}"
  : "${NATS_API_CONFIG:=${TACTICAL_DIR}/api/nats-api.conf}"
fi

export NATS_CONFIG NATS_API_CONFIG

# ---------------------------------------------------------------------------
# Wait for nats-rmm.conf to exist. Two paths land it on disk:
#   1. K8s: the bootstrap-nats-config init container runs `nats-api -bootstrap`
#      and writes the file before the main container starts. In the happy
#      path, this loop exits immediately on the first iteration.
#   2. Docker Compose: tactical-backend writes the file to the shared volume
#      during its init (`python manage.py reload_nats`). This loop gives the
#      backend time to finish its init before we fail.
# Either way, by the time we reach supervisord the file is present.
# ---------------------------------------------------------------------------
attempts=0
max_attempts=60
until [ -s "${NATS_CONFIG}" ]; do
  attempts=$((attempts + 1))
  if [ "${attempts}" -ge "${max_attempts}" ]; then
    echo "ERROR: timed out after $((max_attempts * 5))s waiting for ${NATS_CONFIG}"
    echo "Hint (K8s): check the bootstrap-nats-config init container logs"
    echo "Hint (Compose): check tactical-backend logs for reload_nats errors"
    exit 1
  fi
  echo "Waiting for ${NATS_CONFIG}... (${attempts}/${max_attempts})"
  sleep 5
done
echo "Found ${NATS_CONFIG}, starting supervisord"

# ---------------------------------------------------------------------------
# Supervisord: nats-server + nats-api only. Reloads arrive as NATS messages
# on the trmm.nats.reload subject, handled inside nats-api itself.
# ---------------------------------------------------------------------------
supervisor_config="$(cat << EOF
[supervisord]
nodaemon=true
logfile=/tmp/supervisord.log
pidfile=/tmp/supervisord.pid
[include]
files = /etc/supervisor/conf.d/*.conf

[program:nats-server]
command=nats-server --config ${NATS_CONFIG}
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
priority=10
autorestart=true

[program:nats-api]
command=/usr/local/bin/nats-api -config ${NATS_API_CONFIG}
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
priority=20
autorestart=true
startsecs=3
EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisor.conf
