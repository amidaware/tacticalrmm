#!/usr/bin/env bash

set -e

: "${SALT_USER:=saltapi}"
: "${SALT_USER:=saltpass}"

# create sal user
groupadd -g 1000 "${SALT_USER}" 
useradd -M -d "/opt/tactical" -s /bin/bash -u 1000 -g 1000 "${SALT_USER}"
echo "${SALT_USER}:${SALT_PASS}" | chpasswd

cherrypy_config="$(cat << EOF
module_dirs: ["/opt/tactical/_modules"]
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
command=/bin/bash -c "salt-master -l debug"
redirect_stderr=true

[program:salt-api]
command=/bin/bash -c "salt-api -l debug"
redirect_stderr=true
EOF
)"

echo "${supervisor_config}" > /etc/supervisor/conf.d/supervisor.conf

# run salt and salt master
/usr/bin/supervisord