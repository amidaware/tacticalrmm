#!/usr/bin/env bash

set -e

: "${TRMM_USER:=tactical}"
: "${TRMM_PASS:=tactical}"
: "${POSTGRES_HOST:=tactical-postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=tactical}"
: "${POSTGRES_PASS:=tactical}"
: "${POSTGRES_DB:=tacticalrmm}"
: "${SALT_HOST:=tactical-salt}"
: "${SALT_USER:=saltapi}"
: "${MESH_CONTAINER:=tactical-meshcentral}"
: "${MESH_USER:=meshcentral}"
: "${MESH_PASS:=meshcentralpass}"
: "${MESH_HOST:=tactical-meshcentral}"
: "${API_HOST:=tactical-backend}"
: "${APP_HOST:=tactical-frontend}"
: "${REDIS_HOST:=tactical-redis}"


function check_tactical_ready {
  sleep 15
  until [ -f "${TACTICAL_READY_FILE}" ]; do
    echo "waiting for init container to finish install or update..."
    sleep 10
  done
}

# tactical-init
if [ "$1" = 'tactical-init' ]; then

  mkdir -p ${TACTICAL_DIR}/tmp
  mkdir -p ${TACTICAL_DIR}/scripts/userdefined

  test -f "${TACTICAL_READY_FILE}" && rm "${TACTICAL_READY_FILE}"

  # copy container data to volume
  cp -af ${TACTICAL_TMP_DIR}/. ${TACTICAL_DIR}/

  until (echo > /dev/tcp/"${MESH_CONTAINER}"/443) &> /dev/null; do
    echo "waiting for meshcentral server to be ready..."
    sleep 5
  done

  until (echo > /dev/tcp/"${POSTGRES_HOST}"/"${POSTGRES_PORT}") &> /dev/null; do
    echo "waiting for postgresql server to be ready..."
    sleep 5
  done

  # check mesh setup and wait for mesh token
  until [ -f "${TACTICAL_DIR}/tmp/mesh_token" ]; do
    echo "waiting for mesh token to be generated..."
    sleep 10
  done

  # configure django settings
  MESH_TOKEN=$(cat ${TACTICAL_DIR}/tmp/mesh_token)
  DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 80 | head -n 1)
  ADMINURL=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 70 | head -n 1)

  # write salt pass to tmp dir
  if [ ! -f "${TACTICAL__DIR}/tmp/salt_pass" ]; then
    SALT_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1) 
    echo "${SALT_PASS}" > ${TACTICAL_DIR}/tmp/salt_pass
  else
    SALT_PASS=$(cat ${TACTICAL_DIR}/tmp/salt_pass)
  fi
  
  localvars="$(cat << EOF
SECRET_KEY = '${DJANGO_SEKRET}'

DEBUG = False

DOCKER_BUILD = True

SCRIPTS_DIR = '/opt/tactical/scripts'

ALLOWED_HOSTS = ['${API_HOST}']

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

REST_FRAMEWORK = {
    'DATETIME_FORMAT': '%b-%d-%Y - %H:%M',

    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'knox.auth.TokenAuthentication',
    ),
}

if not DEBUG:
    REST_FRAMEWORK.update({
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    })

SALT_USERNAME = '${SALT_USER}'
SALT_PASSWORD = '${SALT_PASS}'
SALT_HOST     = '${SALT_HOST}'
MESH_USERNAME = '${MESH_USER}'
MESH_SITE = 'https://${MESH_HOST}'
MESH_TOKEN_KEY = '${MESH_TOKEN}'
REDIS_HOST    = '${REDIS_HOST}'
MESH_WS_URL = 'ws://${MESH_CONTAINER}:443'
EOF
)"

  echo "${localvars}" > ${TACTICAL_DIR}/api/tacticalrmm/local_settings.py

  # run migrations and init scripts
  python manage.py migrate --no-input
  python manage.py collectstatic --no-input
  python manage.py initial_db_setup
  python manage.py initial_mesh_setup
  python manage.py load_chocos
  python manage.py load_community_scripts
  python manage.py reload_nats

  # create super user 
  echo "from accounts.models import User; User.objects.create_superuser('${TRMM_USER}', 'admin@example.com', '${TRMM_PASS}') if not User.objects.filter(username='${TRMM_USER}').exists() else 0;" | python manage.py shell

  # chown everything to tactical user
  chown -R "${TACTICAL_USER}":"${TACTICAL_USER}" "${TACTICAL_DIR}"

  # create install ready file
  su -c "echo 'tactical-init' > ${TACTICAL_READY_FILE}" "${TACTICAL_USER}"

fi

# backend container
if [ "$1" = 'tactical-backend' ]; then
  check_tactical_ready

  # Prepare log files and start outputting logs to stdout
  mkdir -p ${TACTICAL_DIR}/api/tacticalrmm/logs
  touch ${TACTICAL_DIR}/api/tacticalrmm/logs/gunicorn.log
  touch ${TACTICAL_DIR}/api/tacticalrmm/logs/gunicorn-access.log
  tail -n 0 -f ${TACTICAL_DIR}/api/tacticalrmm/logs/gunicorn*.log &

  export DJANGO_SETTINGS_MODULE=tacticalrmm.settings

  exec gunicorn tacticalrmm.wsgi:application \
    --name tactical-backend \
    --bind 0.0.0.0:80 \
    --workers 5 \
    --log-level=info \
    --log-file=${TACTICAL_DIR}/api/tacticalrmm/logs/gunicorn.log \
    --access-logfile=${TACTICAL_DIR}/api/tacticalrmm/logs/gunicorn-access.log \

fi

if [ "$1" = 'tactical-celery' ]; then
  check_tactical_ready
  celery -A tacticalrmm worker
fi

if [ "$1" = 'tactical-celerybeat' ]; then
  check_tactical_ready
  test -f "${TACTICAL_DIR}/api/celerybeat.pid" && rm "${TACTICAL_DIR}/api/celerybeat.pid"
  celery -A tacticalrmm beat
fi

if [ "$1" = 'tactical-celerywinupdate' ]; then
  check_tactical_ready
  celery -A tacticalrmm worker -Q wupdate
fi