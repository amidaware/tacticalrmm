#!/usr/bin/env bash

set -e


# wait until nats config file is available
until [ -f "${TACTICAL_DIR}/api/nats-rmm.conf" ]; do
echo "waiting for nats config to be generated..."
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
command=nats-server --config ${TACTICAL_DIR}/api/nats-rmm.conf
redirect_stderr=true

[program:config-watcher]
command=inotifywait -q -m -e close_write ${TACTICAL_DIR}/api/nats-rmm.conf | while read events; do nats-server --signal reload; done;
redirect_stderr=true
EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

# run supervised processes
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisor.conf