#!/usr/bin/env bash

set -e

supervisor_config="$(cat << EOF
[supervisord]
nodaemon=true
[include]
files = /etc/supervisor/conf.d/*.conf

[program:nats-server]
command=nats-server --config ${TACTICAL_DIR}/api/nats-rmm.conf
redirect_stderr=true

[program:config watcher]
command=inotifywait -q -m -e close_write --format %e myfile.py | while read events; do ${TACTICAL_DIR}/api/nats-rmm.conf done;
redirect_stderr=true
EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

# supervised processes
/usr/bin/supervisord