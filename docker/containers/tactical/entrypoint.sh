#!/usr/bin/env bash

set -euo pipefail

# ---------------------------------------------------------------------------
# Environment variable defaults
# ---------------------------------------------------------------------------
: "${VIRTUAL_ENV:=/opt/venv}"
: "${TRMM_USER:=tactical}"
: "${TRMM_PASS:=tactical}"
: "${POSTGRES_HOST:=tactical-postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=tactical}"
: "${POSTGRES_PASS:=tactical}"
: "${POSTGRES_DB:=tacticalrmm}"
# Honor POSTGRES_PASSWORD if passed directly (e.g. from a secrets manager),
# otherwise fall back to POSTGRES_PASS (the name used throughout this project).
: "${POSTGRES_PASSWORD:=${POSTGRES_PASS}}"
: "${API_HOST:=tactical-backend}"
: "${APP_HOST:=tactical-frontend}"
: "${REDIS_HOST:=tactical-redis}"
: "${REDIS_PORT:=6379}"
: "${TACTICAL_BACKEND_PORT:=8080}"
: "${DEBUG:=False}"
: "${OPENFRAME_MODE:=True}"
: "${TRMM_PROTO:=https}"
: "${TRMM_DISABLE_WEB_TERMINAL:=False}"
: "${TRMM_DISABLE_SERVER_SCRIPTS:=False}"
: "${TRMM_DISABLE_SSO:=False}"
: "${TRMM_DISABLE_2FA:=True}"
: "${SWAGGER_ENABLED:=False}"
: "${BETA_API_ENABLED:=False}"
: "${CELERY_AUTOSCALE:=20,2}"
: "${CERT_PRIV_PATH:=${TACTICAL_DIR}/certs/privkey.pem}"
: "${CERT_PUB_PATH:=${TACTICAL_DIR}/certs/fullchain.pem}"
: "${NATS_CONNECT_HOST:=tactical-nats}"
: "${NATS_CONFIG:=${TACTICAL_DIR}/api/nats-rmm.conf}"
: "${NATS_API_CONFIG:=${TACTICAL_DIR}/api/nats-api.conf}"
: "${SESSION_COOKIE_DOMAIN:=}"
: "${CSRF_COOKIE_DOMAIN:=}"
: "${SESSION_COOKIE_SECURE:=True}"
: "${CSRF_COOKIE_SECURE:=True}"
: "${ALLOWED_HOSTS:=${API_HOST},${APP_HOST},tactical-backend}"
: "${CORS_ALLOWED_ORIGINS:=${TRMM_PROTO}://${APP_HOST}}"
: "${CSRF_TRUSTED_ORIGINS:=${TRMM_PROTO}://${API_HOST},${TRMM_PROTO}://${APP_HOST}}"

# ---------------------------------------------------------------------------
# Helper: format comma-separated values as Python list items
#   "a,b,c" → "'a','b','c'"
# ---------------------------------------------------------------------------
to_python_list() {
  echo "$1" | tr ',' '\n' | sed "s/^[[:space:]]*//;s/[[:space:]]*$//;s/.*/'&'/" | paste -sd, -
}

# ---------------------------------------------------------------------------
# create_directories — set up the tactical directory tree
# ---------------------------------------------------------------------------
create_directories() {
  echo "Creating directories"
  mkdir -p "${TACTICAL_DIR}/api/tacticalrmm"
  mkdir -p "${TACTICAL_DIR}/api/tacticalrmm/private/exe"
  mkdir -p "${TACTICAL_DIR}/api/tacticalrmm/private/log"
  mkdir -p "${TACTICAL_DIR}/tmp"
  mkdir -p "${TACTICAL_DIR}/certs"
  mkdir -p "${TACTICAL_DIR}/reporting/assets"
  mkdir -p "${TACTICAL_DIR}/logs"
  touch "${TACTICAL_DIR}/api/tacticalrmm/private/log/django_debug.log"
}

# ---------------------------------------------------------------------------
# copy_custom_code — envsubst config templates into place
# ---------------------------------------------------------------------------
copy_custom_code() {
  echo "Processing config templates"

  # Export all vars needed by envsubst
  export DJANGO_SEKRET ADMINURL DEBUG TRMM_PROTO TACTICAL_DIR VIRTUAL_ENV
  export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD POSTGRES_HOST POSTGRES_PORT
  export REDIS_HOST
  export NATS_CONNECT_HOST
  export APP_HOST API_HOST
  export TRMM_DISABLE_WEB_TERMINAL TRMM_DISABLE_SERVER_SCRIPTS TRMM_DISABLE_SSO TRMM_DISABLE_2FA
  export OPENFRAME_MODE SWAGGER_ENABLED BETA_API_ENABLED
  export CERT_PUB_PATH CERT_PRIV_PATH
  export SESSION_COOKIE_SECURE CSRF_COOKIE_SECURE
  export TACTICAL_BACKEND_PORT

  # Format list-valued vars as Python list items
  export ALLOWED_HOSTS
  export CORS_ALLOWED_ORIGINS
  export CSRF_TRUSTED_ORIGINS

  # Convert cookie domain values to valid Python literals.
  # An empty string is falsy in Python but Django expects None, not ''.
  # Using an explicit conditional here avoids the fragile "'' or None" pattern
  # in the template, which would also coerce any other falsy value (e.g. '0') to None.
  if [ -z "${SESSION_COOKIE_DOMAIN}" ]; then
    export SESSION_COOKIE_DOMAIN_PY="None"
  else
    export SESSION_COOKIE_DOMAIN_PY="'${SESSION_COOKIE_DOMAIN}'"
  fi
  if [ -z "${CSRF_COOKIE_DOMAIN}" ]; then
    export CSRF_COOKIE_DOMAIN_PY="None"
  else
    export CSRF_COOKIE_DOMAIN_PY="'${CSRF_COOKIE_DOMAIN}'"
  fi

  # Explicit variable list to avoid clobbering Python {var} in f-strings
  local vars='$DJANGO_SEKRET $ADMINURL $DEBUG $TRMM_PROTO $TACTICAL_DIR $VIRTUAL_ENV'
  vars+=' $POSTGRES_DB $POSTGRES_USER $POSTGRES_PASSWORD $POSTGRES_HOST $POSTGRES_PORT'
  vars+=' $REDIS_HOST $NATS_CONNECT_HOST'
  vars+=' $APP_HOST $API_HOST'
  vars+=' $TRMM_DISABLE_WEB_TERMINAL $TRMM_DISABLE_SERVER_SCRIPTS $TRMM_DISABLE_SSO $TRMM_DISABLE_2FA'
  vars+=' $OPENFRAME_MODE $SWAGGER_ENABLED $BETA_API_ENABLED'
  vars+=' $CERT_PUB_PATH $CERT_PRIV_PATH'
  vars+=' $ALLOWED_HOSTS $CORS_ALLOWED_ORIGINS $CSRF_TRUSTED_ORIGINS'
  vars+=' $SESSION_COOKIE_DOMAIN_PY $CSRF_COOKIE_DOMAIN_PY $SESSION_COOKIE_SECURE $CSRF_COOKIE_SECURE'
  vars+=' $TACTICAL_BACKEND_PORT'

  rm -f "${TACTICAL_DIR}/api/tacticalrmm/local_settings.py"
  rm -f "${TACTICAL_DIR}/api/app.ini"

  envsubst "${vars}" < "${CUSTOM_CODE_DIR}/local_settings.py" > "${TACTICAL_DIR}/api/tacticalrmm/local_settings.py"
  envsubst "${vars}" < "${CUSTOM_CODE_DIR}/app.ini"           > "${TACTICAL_DIR}/api/app.ini"

  # Guard: a zero-byte settings file causes a cryptic ImportError; fail loudly instead.
  [ -s "${TACTICAL_DIR}/api/tacticalrmm/local_settings.py" ] || \
    { echo "ERROR: local_settings.py was not generated by envsubst"; exit 1; }
  [ -s "${TACTICAL_DIR}/api/app.ini" ] || \
    { echo "ERROR: app.ini was not generated by envsubst"; exit 1; }
}

# ---------------------------------------------------------------------------
# run_migrations — Django management commands
# ---------------------------------------------------------------------------
run_migrations() {
  echo "Running migrations and init scripts"

  # reload_nats and create_natsapi_conf write to NATS_CONFIG / NATS_API_CONFIG;
  # set correct paths so tactical-nats finds the files on the shared volume
  export NATS_CONFIG NATS_API_CONFIG

  python manage.py pre_update_tasks
  python manage.py migrate --no-input
  python manage.py generate_json_schemas
  python manage.py get_webtar_url > "${TACTICAL_DIR}/tmp/web_tar_url"
  python manage.py collectstatic --no-input
  python manage.py initial_db_setup
  python manage.py load_chocos
  python manage.py load_community_scripts
  python manage.py reload_nats
  python manage.py create_natsapi_conf
  python manage.py create_installer_user
  python manage.py clear_redis_celery_locks
  python manage.py post_update_tasks
}

# ---------------------------------------------------------------------------
# create_superuser_and_api_key
# ---------------------------------------------------------------------------
create_superuser_and_api_key() {
  echo "Creating dashboard user if it doesn't exist"

  # Export so Python subprocesses can read via os.environ — avoids shell
  # interpolation into Python string literals, which breaks on special chars
  # (single quotes, backslashes, newlines) in TRMM_USER or TRMM_PASS.
  export TRMM_USER TRMM_PASS

  local totp_clear=""
  if [ "${TRMM_DISABLE_2FA}" = "True" ]; then
    totp_clear="user.totp_key = ''; "
  fi
  echo "import os; from accounts.models import User, Role; \
u = os.environ['TRMM_USER']; p = os.environ['TRMM_PASS']; \
user = User.objects.create_superuser(u, 'admin@example.com', p) \
  if not User.objects.filter(username=u).exists() \
  else User.objects.get(username=u); \
${totp_clear}\
role = Role.objects.create(name='Default Admin', is_superuser=True, can_manage_api_keys=True) \
  if not Role.objects.filter(name='Default Admin').exists() \
  else Role.objects.get(name='Default Admin'); \
user.role = role; user.save();" | python manage.py shell --skip-checks

  echo "Creating default organization and API key"
  echo "import os; from accounts.models import User, APIKey; \
from clients.models import Client, Site; \
from django.utils.crypto import get_random_string; \
user = User.objects.get(username=os.environ['TRMM_USER']); \
client = Client.objects.create(name='Default Organization', created_by=user) \
  if not Client.objects.exists() else Client.objects.first(); \
site = Site.objects.create(client=client, name='Default Site', created_by=user) \
  if not Site.objects.filter(client=client).exists() \
  else Site.objects.filter(client=client).first(); \
api_key = APIKey.objects.create(name='Default', key=get_random_string(length=32).upper(), user=user) \
  if not APIKey.objects.filter(user=user).exists() \
  else APIKey.objects.filter(user=user).first(); \
print(f'{api_key.key}')" | python manage.py shell --skip-checks > "${TACTICAL_DIR}/api_key.txt"
}

# ---------------------------------------------------------------------------
# set_ready_status — file-based readiness signal
# ---------------------------------------------------------------------------
set_ready_status() {
  local service_name=$1
  echo "Setting ready status for ${service_name}"
  mkdir -p "$(dirname "${TACTICAL_READY_FILE}")"
  echo "${service_name}" > "${TACTICAL_READY_FILE}"
}

# ---------------------------------------------------------------------------
# check_tactical_ready — wait for the init ready file
# ---------------------------------------------------------------------------
check_tactical_ready() {
  sleep 15
  local attempts=0
  local max_attempts=60  # 60 × 10 s = 10 minutes
  until [ -f "${TACTICAL_READY_FILE}" ]; do
    attempts=$((attempts + 1))
    if [ "${attempts}" -ge "${max_attempts}" ]; then
      echo "ERROR: timed out after $((max_attempts * 10))s waiting for tactical-backend to finish init"
      exit 1
    fi
    echo "Waiting for init to finish... (${attempts}/${max_attempts})"
    sleep 10
  done
}

# ---------------------------------------------------------------------------
# tactical_init — master initialization
# ---------------------------------------------------------------------------
tactical_init() {
  local role=$1

  # Copy source to working directory.
  # Exclude celerybeat-schedule* so Celery Beat's timing state survives restarts;
  # without this, --delete removes it and beat re-runs tasks that already ran.
  rsync -a --no-perms --no-owner --delete \
    --exclude "tmp/*" \
    --exclude "certs/*" \
    --exclude "api/tacticalrmm/private/*" \
    --exclude "api/celerybeat-schedule*" \
    "${TACTICAL_TMP_DIR}/" "${TACTICAL_DIR}/"

  create_directories

  # Persist secret values across restarts so Django's SECRET_KEY never changes.
  # Written with mode 0600 (owner-read-only) to protect the key at rest.
  local sekret_file="${TACTICAL_DIR}/tmp/.django_sekret"
  local adminurl_file="${TACTICAL_DIR}/tmp/.adminurl"
  if [ -f "${sekret_file}" ]; then
    DJANGO_SEKRET=$(cat "${sekret_file}")
  else
    DJANGO_SEKRET=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 80 | head -n 1)
    (umask 0177; echo "${DJANGO_SEKRET}" > "${sekret_file}")
  fi
  if [ -f "${adminurl_file}" ]; then
    ADMINURL=$(cat "${adminurl_file}")
  else
    ADMINURL=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 70 | head -n 1)
    (umask 0177; echo "${ADMINURL}" > "${adminurl_file}")
  fi
  export DJANGO_SEKRET ADMINURL

  # Format list-valued env vars as Python literals
  export ALLOWED_HOSTS=$(to_python_list "${ALLOWED_HOSTS}")
  export CORS_ALLOWED_ORIGINS=$(to_python_list "${CORS_ALLOWED_ORIGINS}")
  export CSRF_TRUSTED_ORIGINS=$(to_python_list "${CSRF_TRUSTED_ORIGINS}")

  copy_custom_code

  if [ "${role}" = "backend" ]; then
    run_migrations
    create_superuser_and_api_key
  fi

  # Set ownership
  chown -R "${TACTICAL_USER}:${TACTICAL_USER}" "${TACTICAL_DIR}"

  set_ready_status "init"
}

# ===========================================================================
# Entrypoint dispatch
# ===========================================================================

if [ "${1:-}" = 'tactical-backend' ]; then
  # Wait for postgres
  until (echo > /dev/tcp/"${POSTGRES_HOST}"/"${POSTGRES_PORT}") &>/dev/null; do
    echo "Waiting for PostgreSQL..."
    sleep 5
  done

  # Wait for redis (clear_redis_celery_locks runs during migrations)
  until (echo > /dev/tcp/"${REDIS_HOST}"/"${REDIS_PORT}") &>/dev/null; do
    echo "Waiting for Redis..."
    sleep 5
  done

  tactical_init "backend"
  exec uwsgi "${TACTICAL_DIR}/api/app.ini"
fi

if [ "${1:-}" = 'tactical-celery' ]; then
  check_tactical_ready
  exec celery -A tacticalrmm worker --autoscale="${CELERY_AUTOSCALE}" -l info
fi

if [ "${1:-}" = 'tactical-celerybeat' ]; then
  check_tactical_ready
  test -f "${TACTICAL_DIR}/api/celerybeat.pid" && rm "${TACTICAL_DIR}/api/celerybeat.pid"
  exec celery -A tacticalrmm beat -l info
fi

if [ "${1:-}" = 'tactical-websockets' ]; then
  check_tactical_ready
  export DJANGO_SETTINGS_MODULE=tacticalrmm.settings
  exec uvicorn --host 0.0.0.0 --port 8383 --forwarded-allow-ips='*' tacticalrmm.asgi:application
fi
