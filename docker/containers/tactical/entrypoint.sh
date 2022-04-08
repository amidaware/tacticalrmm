#!/usr/bin/env bash

set -e

: "${TRMM_USER:=tactical}"
: "${TRMM_PASS:=tactical}"
: "${POSTGRES_HOST:=tactical-postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=tactical}"
: "${POSTGRES_PASS:=tactical}"
: "${POSTGRES_DB:=tacticalrmm}"
: "${MESH_SERVICE:=tactical-meshcentral}"
: "${MESH_WS_URL:=ws://${MESH_SERVICE}:4443}"
: "${MESH_USER:=meshcentral}"
: "${MESH_PASS:=meshcentralpass}"
: "${MESH_HOST:=tactical-meshcentral}"
: "${API_HOST:=tactical-backend}"
: "${APP_HOST:=tactical-frontend}"
: "${REDIS_HOST:=tactical-redis}"

: "${CERT_PRIV_PATH:=${TACTICAL_DIR}/certs/privkey.pem}"
: "${CERT_PUB_PATH:=${TACTICAL_DIR}/certs/fullchain.pem}"

function check_tactical_ready {
  sleep 15
  until [ -f "${TACTICAL_READY_FILE}" ]; do
    echo "waiting for init container to finish install or update..."
    sleep 10
  done
}

# tactical-init
if [ "$1" = 'tactical-init' ]; then

  test -f "${TACTICAL_READY_FILE}" && rm "${TACTICAL_READY_FILE}"

  # copy container data to volume
  rsync -a --no-perms --no-owner --delete --exclude "tmp/*" --exclude "certs/*" --exclude="api/tacticalrmm/private/*" "${TACTICAL_TMP_DIR}/" "${TACTICAL_DIR}/"

  mkdir -p /meshcentral-data
  mkdir -p ${TACTICAL_DIR}/tmp
  mkdir -p ${TACTICAL_DIR}/certs
  mkdir -p /mongo/data/db
  mkdir -p /redis/data
  touch /meshcentral-data/.initialized && chown -R 1000:1000 /meshcentral-data
  touch ${TACTICAL_DIR}/tmp/.initialized && chown -R 1000:1000 ${TACTICAL_DIR}
  touch ${TACTICAL_DIR}/certs/.initialized && chown -R 1000:1000 ${TACTICAL_DIR}/certs
  touch /mongo/data/db/.initialized && chown -R 1000:1000 /mongo/data/db
  touch /redis/data/.initialized && chown -R 1000:1000 /redis/data
  mkdir -p ${TACTICAL_DIR}/api/tacticalrmm/private/exe
  mkdir -p ${TACTICAL_DIR}/api/tacticalrmm/private/log
  touch ${TACTICAL_DIR}/api/tacticalrmm/private/log/django_debug.log
  
  until (echo > /dev/tcp/"${POSTGRES_HOST}"/"${POSTGRES_PORT}") &> /dev/null; do
    echo "waiting for postgresql container to be ready..."
    sleep 5
  done

  until (echo > /dev/tcp/"${MESH_SERVICE}"/4443) &> /dev/null; do
    echo "waiting for meshcentral container to be ready..."
    sleep 5
  done

  # configure django settings
  MESH_TOKEN=$(cat ${TACTICAL_DIR}/tmp/mesh_token)
  ADMINURL=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 70 | head -n 1)
  DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 80 | head -n 1)
  
  localvars="$(cat << EOF
SECRET_KEY = '${DJANGO_SEKRET}'

DEBUG = False

DOCKER_BUILD = True

CERT_FILE = '${CERT_PUB_PATH}'
KEY_FILE = '${CERT_PRIV_PATH}'

EXE_DIR = '/opt/tactical/api/tacticalrmm/private/exe'
LOG_DIR = '/opt/tactical/api/tacticalrmm/private/log'

SCRIPTS_DIR = '/opt/tactical/community-scripts'

ALLOWED_HOSTS = ['${API_HOST}', 'tactical-backend']

ADMIN_URL = '${ADMINURL}/'

CORS_ORIGIN_WHITELIST = [
    'https://${APP_HOST}'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${POSTGRES_DB}',
        'USER': '${POSTGRES_USER}',
        'PASSWORD': '${POSTGRES_PASS}',
        'HOST': '${POSTGRES_HOST}',
        'PORT': '${POSTGRES_PORT}',
    }
}

MESH_USERNAME = '${MESH_USER}'
MESH_SITE = 'https://${MESH_HOST}'
MESH_TOKEN_KEY = '${MESH_TOKEN}'
REDIS_HOST    = '${REDIS_HOST}'
MESH_WS_URL = '${MESH_WS_URL}'
ADMIN_ENABLED = False
EOF
)"

  echo "${localvars}" > ${TACTICAL_DIR}/api/tacticalrmm/local_settings.py

  numprocs=$(nproc)
  uwsgiprocs=4
  if [[ "$numprocs" == "1" ]]; then
    uwsgiprocs=2
  else
    uwsgiprocs=$numprocs
  fi

uwsgiconf="$(cat << EOF
[uwsgi]
chdir = /opt/tactical/api
module = tacticalrmm.wsgi
home = /opt/venv
master = true
processes = ${uwsgiprocs}
threads = ${uwsgiprocs}
enable-threads = true
socket = 0.0.0.0:8080
harakiri = 300
chmod-socket = 660
buffer-size = 65535
vacuum = true
die-on-term = true
max-requests = 500
disable-logging = true
EOF
)"

  echo "${uwsgiconf}" > ${TACTICAL_DIR}/api/uwsgi.ini


  # run migrations and init scripts
  python manage.py pre_update_tasks
  python manage.py migrate --no-input
  python manage.py collectstatic --no-input
  python manage.py initial_db_setup
  python manage.py initial_mesh_setup
  python manage.py load_chocos
  python manage.py load_community_scripts
  python manage.py reload_nats
  python manage.py create_natsapi_conf
  python manage.py create_installer_user
  python manage.py post_update_tasks

  # create super user 
  echo "Creating dashboard user if it doesn't exist"
  echo "from accounts.models import User; User.objects.create_superuser('${TRMM_USER}', 'admin@example.com', '${TRMM_PASS}') if not User.objects.filter(username='${TRMM_USER}').exists() else 0;" | python manage.py shell

  # chown everything to tactical user
  echo "Updating permissions on files"
  chown -R "${TACTICAL_USER}":"${TACTICAL_USER}" "${TACTICAL_DIR}"

  # create install ready file
  echo "Creating install ready file"
  su -c "echo 'tactical-init' > ${TACTICAL_READY_FILE}" "${TACTICAL_USER}"

fi

# backend container
if [ "$1" = 'tactical-backend' ]; then
  check_tactical_ready

  uwsgi ${TACTICAL_DIR}/api/uwsgi.ini
fi

if [ "$1" = 'tactical-celery' ]; then
  check_tactical_ready
  celery -A tacticalrmm worker -l info
fi

if [ "$1" = 'tactical-celerybeat' ]; then
  check_tactical_ready
  test -f "${TACTICAL_DIR}/api/celerybeat.pid" && rm "${TACTICAL_DIR}/api/celerybeat.pid"
  celery -A tacticalrmm beat -l info
fi

# websocket container
if [ "$1" = 'tactical-websockets' ]; then
  check_tactical_ready

  export DJANGO_SETTINGS_MODULE=tacticalrmm.settings

  daphne tacticalrmm.asgi:application --port 8383 -b 0.0.0.0
fi
