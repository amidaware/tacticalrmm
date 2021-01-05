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

# Add python venv to path
export PATH="${VIRTUAL_ENV}/bin:$PATH"

function check_tactical_ready {
  sleep 15
  until [ -f "${TACTICAL_READY_FILE}" ]; do
    echo "waiting for init container to finish install or update..."
    sleep 10
  done
}

function django_setup {
  until (echo > /dev/tcp/"${POSTGRES_HOST}"/"${POSTGRES_PORT}") &> /dev/null; do
    echo "waiting for postgresql container to be ready..."
    sleep 5
  done

  until (echo > /dev/tcp/"${MESH_CONTAINER}"/443) &> /dev/null; do
    echo "waiting for meshcentral container to be ready..."
    sleep 5
  done

  echo "setting up django environment"

  # configure django settings
  MESH_TOKEN=$(cat ${TACTICAL_DIR}/tmp/mesh_token)

  DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 80 | head -n 1)

  # write salt pass to tmp dir
  if [ ! -f "${TACTICAL__DIR}/tmp/salt_pass" ]; then
    SALT_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1) 
    echo "${SALT_PASS}" > ${TACTICAL_DIR}/tmp/salt_pass
  else
    SALT_PASS=$(cat ${TACTICAL_DIR}/tmp/salt_pass)
  fi
  
  localvars="$(cat << EOF
SECRET_KEY = '${DJANGO_SEKRET}'

DEBUG = True

DOCKER_BUILD = True

CERT_FILE = '/opt/tactical/certs/fullchain.pem'
KEY_FILE = '/opt/tactical/certs/privkey.pem'

SCRIPTS_DIR = '${WORKSPACE_DIR}/scripts'

ALLOWED_HOSTS = ['${API_HOST}']

ADMIN_URL = 'admin/'

CORS_ORIGIN_ALLOW_ALL = True

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
EOF
)"

  echo "${localvars}" > ${WORKSPACE_DIR}/api/tacticalrmm/tacticalrmm/local_settings.py

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

}

if [ "$1" = 'tactical-init-dev' ]; then

  # make directories if they don't exist
  mkdir -p ${TACTICAL_DIR}/tmp

  test -f "${TACTICAL_READY_FILE}" && rm "${TACTICAL_READY_FILE}"

  # setup Python virtual env and install dependencies
  python -m venv --copies ${VIRTUAL_ENV}
  pip install --no-cache-dir -r /requirements.txt

  django_setup

  # create .env file for frontend
  webenv="$(cat << EOF
PROD_URL = "http://${API_HOST}:8000"
DEV_URL = "http://${API_HOST}:8000"
DEV_HOST = 0.0.0.0
DEV_PORT = 8080
EOF
)"
  echo "${webenv}" | tee ${WORKSPACE_DIR}/web/.env > /dev/null

  # chown everything to tactical user
  chown -R "${TACTICAL_USER}":"${TACTICAL_USER}" "${WORKSPACE_DIR}"
  chown -R "${TACTICAL_USER}":"${TACTICAL_USER}" "${TACTICAL_DIR}"

  # create install ready file
  su -c "echo 'tactical-init' > ${TACTICAL_READY_FILE}" "${TACTICAL_USER}"
fi

if [ "$1" = 'tactical-api' ]; then
  check_tactical_ready
  python manage.py runserver 0.0.0.0:8000
fi

if [ "$1" = 'tactical-celery-dev' ]; then
  check_tactical_ready
  celery -A tacticalrmm worker -l debug
fi

if [ "$1" = 'tactical-celerybeat-dev' ]; then
  check_tactical_ready
  test -f "${WORKSPACE_DIR}/api/tacticalrmm/celerybeat.pid" && rm "${WORKSPACE_DIR}/api/tacticalrmm/celerybeat.pid"
  celery -A tacticalrmm beat -l debug
fi

if [ "$1" = 'tactical-celerywinupdate-dev' ]; then
  check_tactical_ready
  celery -A tacticalrmm worker -Q wupdate -l debug
fi
