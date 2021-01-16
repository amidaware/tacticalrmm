#!/usr/bin/env bash

set -e

: "${DEV:=0}"
: "${API_CONTAINER:=tactical-backend}"
: "${API_PORT:=80}"

if [ "${DEV}" = 1 ]; then
  NATS_CONFIG=/workspace/api/tacticalrmm/nats-rmm.conf
else
  NATS_CONFIG="${TACTICAL_DIR}/api/nats-rmm.conf"
fi
sleep 15
until [ -f "${TACTICAL_READY_FILE}" ]; do
  echo "waiting for init container to finish install or update..."
  sleep 10
done

mkdir -p /var/log/supervisor
mkdir -p /etc/supervisor/conf.d

supervisor_config="$(cat << EOF
[supervisord]
nodaemon=true
[include]
files = /etc/supervisor/conf.d/*.conf

[program:nats-server]
command=nats-server --config ${NATS_CONFIG}
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true

[program:config-watcher]
command=/bin/bash -c "inotifywait -mq -e modify "${NATS_CONFIG}" | while read event; do nats-server --signal reload; done;"
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true

[program:nats-api]
command=/bin/bash -c "/usr/local/bin/nats-api -api-host http://${API_CONTAINER}:${API_PORT}/natsapi -nats-host tls://${API_HOST}:4222"
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

# run supervised processes
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisor.conf
