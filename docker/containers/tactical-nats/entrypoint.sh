#!/usr/bin/env bash

set -e

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
command=nats-server -DVV --config "${TACTICAL_DIR}/api/nats-rmm.conf"
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true

[program:config-watcher]
command="inotifywait -m -e close_write ${TACTICAL_DIR}/api/nats-rmm.conf"; | while read events; do "nats-server --signal reload"; done;
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

# run supervised processes
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisor.conf