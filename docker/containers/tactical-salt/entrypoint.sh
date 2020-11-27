#!/usr/bin/env bash

set -e

: "${SALT_USER:='saltapi'}"

sleep 15
until [ -f "${TACTICAL_READY_FILE}" ]; do
  echo "waiting for init container to finish install or update..."
  sleep 10
done

SALT_PASS=$(cat ${TACTICAL_DIR}/tmp/salt_pass)

echo "${SALT_USER}:${SALT_PASS}" | chpasswd

cherrypy_config="$(cat << EOF
file_roots:
  base:
    - /srv/salt
    - ${TACTICAL_DIR}
timeout: 20
gather_job_timeout: 25
max_event_size: 30485760
external_auth:
    pam:
        ${SALT_USER}:
        - .*
        - '@runner'
        - '@wheel'
        - '@jobs'
rest_cherrypy:
    port: 8123
    disable_ssl: True
    max_request_body_size: 30485760
EOF
)"

echo "${cherrypy_config}" > /etc/salt/master.d/rmm-salt.conf

supervisor_config="$(cat << EOF
[supervisord]
nodaemon=true
[include]
files = /etc/supervisor/conf.d/*.conf

[program:salt-master]
command=/bin/bash -c "salt-master -l info"
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true

[program:salt-api]
command=/bin/bash -c "salt-api -l info"
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

# run salt and salt master
/usr/bin/supervisord