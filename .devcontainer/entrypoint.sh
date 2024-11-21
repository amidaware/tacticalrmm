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
: "${REDIS_HOST:=tactical-redis}"
: "${API_PORT:=8000}"

: "${CERT_PRIV_PATH:=${TACTICAL_DIR}/certs/privkey.pem}"
: "${CERT_PUB_PATH:=${TACTICAL_DIR}/certs/fullchain.pem}"

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
  until (echo >/dev/tcp/"${POSTGRES_HOST}"/"${POSTGRES_PORT}") &>/dev/null; do
    echo "waiting for postgresql container to be ready..."
    sleep 5
  done

  until (echo >/dev/tcp/"${MESH_SERVICE}"/4443) &>/dev/null; do
    echo "waiting for meshcentral container to be ready..."
    sleep 5
  done

  echo "setting up django environment"

  # configure django settings
  MESH_TOKEN="$(cat ${TACTICAL_DIR}/tmp/mesh_token)"

  DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 80 | head -n 1)

  BASE_DOMAIN=$(echo "import tldextract; no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=()); extracted = no_fetch_extract('${API_HOST}'); print(f'{extracted.domain}.{extracted.suffix}')" | python)

  localvars="$(
    cat <<EOF
SECRET_KEY = '${DJANGO_SEKRET}'

DEBUG = True

DOCKER_BUILD = True

SWAGGER_ENABLED = True

CERT_FILE = '${CERT_PUB_PATH}'
KEY_FILE = '${CERT_PRIV_PATH}'

SCRIPTS_DIR = '/community-scripts'

ADMIN_URL = 'admin/'

ALLOWED_HOSTS = ['${API_HOST}', '${APP_HOST}', '*']

CORS_ORIGIN_WHITELIST = ['https://${APP_HOST}']

SESSION_COOKIE_DOMAIN = '${BASE_DOMAIN}'
CSRF_COOKIE_DOMAIN = '${BASE_DOMAIN}'
CSRF_TRUSTED_ORIGINS = ['https://${API_HOST}', 'https://${APP_HOST}']

HEADLESS_FRONTEND_URLS = {'socialaccount_login_error': 'https://${APP_HOST}/account/provider/callback'}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${POSTGRES_DB}',
        'USER': '${POSTGRES_USER}',
        'PASSWORD': '${POSTGRES_PASS}',
        'HOST': '${POSTGRES_HOST}',
        'PORT': '${POSTGRES_PORT}',
    },
    'reporting': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${POSTGRES_DB}',
        'USER': 'reporting_user',
        'PASSWORD': 'read_password',
        'HOST': '${POSTGRES_HOST}',
        'PORT': '${POSTGRES_PORT}',
        'OPTIONS': {
            'options': '-c default_transaction_read_only=on'
        }
    }
}

MESH_USERNAME = '${MESH_USER}'
MESH_SITE = 'https://${MESH_HOST}'
MESH_TOKEN_KEY = '${MESH_TOKEN}'
REDIS_HOST    = '${REDIS_HOST}'
MESH_WS_URL = '${MESH_WS_URL}'
ADMIN_ENABLED = True
TRMM_INSECURE = True
EOF
  )"

  echo "${localvars}" >${WORKSPACE_DIR}/api/tacticalrmm/tacticalrmm/local_settings.py

  # run migrations and init scripts
  "${VIRTUAL_ENV}"/bin/python manage.py pre_update_tasks
  "${VIRTUAL_ENV}"/bin/python manage.py migrate --no-input
  "${VIRTUAL_ENV}"/bin/python manage.py generate_json_schemas
  "${VIRTUAL_ENV}"/bin/python manage.py collectstatic --no-input
  "${VIRTUAL_ENV}"/bin/python manage.py initial_db_setup
  "${VIRTUAL_ENV}"/bin/python manage.py initial_mesh_setup
  "${VIRTUAL_ENV}"/bin/python manage.py load_chocos
  "${VIRTUAL_ENV}"/bin/python manage.py load_community_scripts
  "${VIRTUAL_ENV}"/bin/python manage.py reload_nats
  "${VIRTUAL_ENV}"/bin/python manage.py create_natsapi_conf
  "${VIRTUAL_ENV}"/bin/python manage.py create_installer_user
  "${VIRTUAL_ENV}"/bin/python manage.py post_update_tasks

  # create super user
  echo "from accounts.models import User; User.objects.create_superuser('${TRMM_USER}', 'admin@example.com', '${TRMM_PASS}') if not User.objects.filter(username='${TRMM_USER}').exists() else 0;" | python manage.py shell
}

if [ "$1" = 'tactical-init-dev' ]; then

  # make directories if they don't exist
  mkdir -p "${TACTICAL_DIR}/tmp"

  test -f "${TACTICAL_READY_FILE}" && rm "${TACTICAL_READY_FILE}"

  mkdir -p /meshcentral-data
  mkdir -p ${TACTICAL_DIR}/tmp
  mkdir -p ${TACTICAL_DIR}/certs
  mkdir -p ${TACTICAL_DIR}/reporting
  mkdir -p ${TACTICAL_DIR}/reporting/assets
  mkdir -p /mongo/data/db
  mkdir -p /redis/data
  touch /meshcentral-data/.initialized && chown -R 1000:1000 /meshcentral-data
  touch ${TACTICAL_DIR}/tmp/.initialized && chown -R 1000:1000 ${TACTICAL_DIR}
  touch ${TACTICAL_DIR}/certs/.initialized && chown -R 1000:1000 ${TACTICAL_DIR}/certs
  touch /mongo/data/db/.initialized && chown -R 1000:1000 /mongo/data/db
  touch /redis/data/.initialized && chown -R 1000:1000 /redis/data
  touch ${TACTICAL_DIR}/reporting && chown -R 1000:1000 ${TACTICAL_DIR}/reporting
  mkdir -p ${TACTICAL_DIR}/api/tacticalrmm/private/exe
  mkdir -p ${TACTICAL_DIR}/api/tacticalrmm/private/log
  touch ${TACTICAL_DIR}/api/tacticalrmm/private/log/django_debug.log

  # setup Python virtual env and install dependencies
  ! test -e "${VIRTUAL_ENV}" && python -m venv ${VIRTUAL_ENV}
  "${VIRTUAL_ENV}"/bin/python -m pip install --upgrade pip
  "${VIRTUAL_ENV}"/bin/pip install --no-cache-dir setuptools wheel
  "${VIRTUAL_ENV}"/bin/pip install --no-cache-dir -r /requirements.txt

  django_setup

  # chown everything to tactical user
  chown -R "${TACTICAL_USER}":"${TACTICAL_USER}" "${WORKSPACE_DIR}"
  chown -R "${TACTICAL_USER}":"${TACTICAL_USER}" "${TACTICAL_DIR}"

  # create install ready file
  su -c "echo 'tactical-init' > ${TACTICAL_READY_FILE}" "${TACTICAL_USER}"
fi

if [ "$1" = 'tactical-api' ]; then
  check_tactical_ready
  "${VIRTUAL_ENV}"/bin/python manage.py runserver 0.0.0.0:"${API_PORT}"
fi

if [ "$1" = 'tactical-celery-dev' ]; then
  check_tactical_ready
  "${VIRTUAL_ENV}"/bin/celery -A tacticalrmm worker -l debug
fi

if [ "$1" = 'tactical-celerybeat-dev' ]; then
  check_tactical_ready
  test -f "${WORKSPACE_DIR}/api/tacticalrmm/celerybeat.pid" && rm "${WORKSPACE_DIR}/api/tacticalrmm/celerybeat.pid"
  "${VIRTUAL_ENV}"/bin/celery -A tacticalrmm beat -l debug
fi

if [ "$1" = 'tactical-websockets-dev' ]; then
  check_tactical_ready
  "${VIRTUAL_ENV}"/bin/daphne tacticalrmm.asgi:application --port 8383 -b 0.0.0.0
fi
