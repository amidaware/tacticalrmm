#!/usr/bin/env bash

set -euo pipefail

: "${DEV:=0}"
: "${NATS_CONFIG_CHECK_INTERVAL:=1}"

if [ "${DEV}" = 1 ]; then
  NATS_CONFIG=/workspace/api/tacticalrmm/nats-rmm.conf
  NATS_API_CONFIG=/workspace/api/tacticalrmm/nats-api.conf
else
  NATS_CONFIG="${TACTICAL_DIR}/api/nats-rmm.conf"
  NATS_API_CONFIG="${TACTICAL_DIR}/api/nats-api.conf"
fi

sleep 15
nats_attempts=0
nats_max=60  # 60 × 10 s = 10 minutes
until [ -f "${TACTICAL_READY_FILE}" ]; do
  nats_attempts=$((nats_attempts + 1))
  if [ "${nats_attempts}" -ge "${nats_max}" ]; then
    echo "ERROR: timed out after $((nats_max * 10))s waiting for tactical-backend to finish init"
    exit 1
  fi
  echo "Waiting for tactical-backend init... (${nats_attempts}/${nats_max})"
  sleep 10
done

config_watcher="$(cat << EOF
while true; do
    sleep ${NATS_CONFIG_CHECK_INTERVAL};
    if [[ ! -z \${NATS_CHECK} ]]; then
        NATS_RELOAD=\$(stat -c %Y '${NATS_CONFIG}')
        if [[ \$NATS_RELOAD == \$NATS_CHECK ]]; then
            :
        else
            nats-server --signal reload;
            NATS_CHECK=\$(stat -c %Y '${NATS_CONFIG}');
        fi
    else NATS_CHECK=\$(stat -c %Y '${NATS_CONFIG}');
    fi
done

EOF
)"

echo "${config_watcher}" > /usr/local/bin/config_watcher.sh
chmod +x /usr/local/bin/config_watcher.sh

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

[program:config-watcher]
command=/bin/bash /usr/local/bin/config_watcher.sh
startsecs=10
autorestart=true
startretries=1
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true

[program:nats-api]
command=/bin/bash -c "/usr/local/bin/nats-api -config ${NATS_API_CONFIG}"
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true

EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

# run supervised processes
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisor.conf
