#!/usr/bin/env bash

set -euo pipefail

# ---------------------------------------------------------------------------
# Environment variable defaults
# ---------------------------------------------------------------------------
# Dockerfile ENV values listed here as fallbacks so the script is safe to run
# and test outside of a Docker container (e.g. in CI or locally).
: "${TACTICAL_DIR:=/opt/tactical}"
: "${TACTICAL_TMP_DIR:=/tmp/tactical}"
: "${TACTICAL_USER:=tactical}"
: "${CUSTOM_CODE_DIR:=/tmp/custom_code_dir}"
: "${TACTICAL_READY_FILE:=${TACTICAL_DIR}/tmp/tactical.ready}"
: "${VIRTUAL_ENV:=/opt/venv}"
: "${TRMM_USER:=tactical}"
: "${TRMM_PASS:=tactical}"
: "${POSTGRES_HOST:=tactical-postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=tactical}"
: "${POSTGRES_PASSWORD:=tactical}"
: "${POSTGRES_DATABASE:=tacticalrmm}"
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
: "${TRMM_DISABLE_MESH_SYNC_TASK:=True}"
: "${SWAGGER_ENABLED:=False}"
: "${BETA_API_ENABLED:=False}"
: "${CELERY_AUTOSCALE:=20,2}"
: "${CERT_PRIV_PATH:=${TACTICAL_DIR}/certs/privkey.pem}"
: "${CERT_PUB_PATH:=${TACTICAL_DIR}/certs/fullchain.pem}"
: "${NATS_HOST:=tactical-nats}"
: "${NATS_PORT:=4222}"
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
  export SECRET_KEY ADMINURL DEBUG TRMM_PROTO TACTICAL_DIR VIRTUAL_ENV
  export POSTGRES_DATABASE POSTGRES_USER POSTGRES_PASSWORD POSTGRES_HOST POSTGRES_PORT
  export REDIS_HOST REDIS_PORT
  export NATS_HOST NATS_PORT
  export APP_HOST
  export TRMM_DISABLE_WEB_TERMINAL TRMM_DISABLE_SERVER_SCRIPTS TRMM_DISABLE_SSO TRMM_DISABLE_2FA TRMM_DISABLE_MESH_SYNC_TASK
  export OPENFRAME_MODE SWAGGER_ENABLED BETA_API_ENABLED
  export CERT_PUB_PATH CERT_PRIV_PATH
  export SESSION_COOKIE_SECURE CSRF_COOKIE_SECURE
  export TACTICAL_BACKEND_PORT

  # Format list-valued vars as Python list items.
  # Assignment before export keeps set -e effective: `export X=$(cmd)` masks
  # cmd's failure because bash exempts export-as-assignment from immediate exit,
  # while `X=$(cmd); export X` aborts immediately if cmd returns non-zero.
  ALLOWED_HOSTS=$(to_python_list "${ALLOWED_HOSTS}")
  export ALLOWED_HOSTS
  CORS_ALLOWED_ORIGINS=$(to_python_list "${CORS_ALLOWED_ORIGINS}")
  export CORS_ALLOWED_ORIGINS
  CSRF_TRUSTED_ORIGINS=$(to_python_list "${CSRF_TRUSTED_ORIGINS}")
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
  local vars='$SECRET_KEY $ADMINURL $DEBUG $TRMM_PROTO $TACTICAL_DIR $VIRTUAL_ENV'
  vars+=' $POSTGRES_DATABASE $POSTGRES_USER $POSTGRES_PASSWORD $POSTGRES_HOST $POSTGRES_PORT'
  vars+=' $REDIS_HOST $REDIS_PORT $NATS_HOST $NATS_PORT'
  vars+=' $APP_HOST'
  vars+=' $TRMM_DISABLE_WEB_TERMINAL $TRMM_DISABLE_SERVER_SCRIPTS $TRMM_DISABLE_SSO $TRMM_DISABLE_2FA $TRMM_DISABLE_MESH_SYNC_TASK'
  vars+=' $OPENFRAME_MODE $SWAGGER_ENABLED $BETA_API_ENABLED'
  vars+=' $CERT_PUB_PATH $CERT_PRIV_PATH'
  vars+=' $ALLOWED_HOSTS $CORS_ALLOWED_ORIGINS $CSRF_TRUSTED_ORIGINS'
  vars+=' $SESSION_COOKIE_DOMAIN_PY $CSRF_COOKIE_DOMAIN_PY $SESSION_COOKIE_SECURE $CSRF_COOKIE_SECURE'
  vars+=' $TACTICAL_BACKEND_PORT'

  rm -f "${TACTICAL_DIR}/api/tacticalrmm/local_settings.py"
  rm -f "${TACTICAL_DIR}/api/app.ini"

  envsubst "${vars}" < "${CUSTOM_CODE_DIR}/local_settings.py.template" > "${TACTICAL_DIR}/api/tacticalrmm/local_settings.py"
  envsubst "${vars}" < "${CUSTOM_CODE_DIR}/app.ini.template"           > "${TACTICAL_DIR}/api/app.ini"

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
  # Written 0600: the key is a credential; world-readable (default 0644) is wrong.
  (umask 0177
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
  )
}

# ---------------------------------------------------------------------------
# set_ready_status — signals K8s liveness/readiness probes that init is done.
# Probes check existence only; file content is unused.
# ---------------------------------------------------------------------------
set_ready_status() {
  echo "Setting ready status"
  touch "${TACTICAL_READY_FILE}"
}

# ---------------------------------------------------------------------------
# worker_init — initialization for celery, celerybeat, websockets containers.
# Unlike tactical_init, these don't share the backend PVC and don't generate
# secrets; SECRET_KEY must be injected from a K8s Secret. ADMINURL is
# optional (ADMIN_ENABLED=False in the settings template, so the value is
# only used to render an unreachable URL prefix).
# ---------------------------------------------------------------------------
worker_init() {
  if [ -z "${SECRET_KEY:-}" ]; then
    echo "ERROR: worker_init requires SECRET_KEY env var"
    exit 1
  fi

  # Copy source to working directory (emptyDir is always fresh, no --delete needed)
  rsync -a --no-perms --no-owner \
    "${TACTICAL_TMP_DIR}/" "${TACTICAL_DIR}/"

  create_directories

  export SECRET_KEY ADMINURL
  copy_custom_code

  set_ready_status
}

# ---------------------------------------------------------------------------
# tactical_init — backend initialization: preserves state dirs across restarts,
#                 generates/restores SECRET_KEY + ADMINURL, runs migrations,
#                 creates the default superuser and API key.
# ---------------------------------------------------------------------------
tactical_init() {
  # Copy source to working dir. --exclude flags below protect runtime state
  # (secrets, certs, agent binaries, logs, reports, celerybeat schedule) from
  # being wiped by --delete on restart.
  rsync -a --no-perms --no-owner --delete \
    --exclude "tmp/*" \
    --exclude "certs/*" \
    --exclude "api/tacticalrmm/private/*" \
    --exclude "api/celerybeat-schedule*" \
    --exclude "reporting/*" \
    --exclude "logs/*" \
    "${TACTICAL_TMP_DIR}/" "${TACTICAL_DIR}/"

  create_directories

  # Persist secret values across restarts so Django's SECRET_KEY never changes.
  # When running in Kubernetes, SECRET_KEY and ADMINURL are injected as env
  # vars from a K8s Secret — skip file-based generation in that case.
  # Written with mode 0600 (owner-read-only) to protect the key at rest.
  if [ -z "${SECRET_KEY:-}" ]; then
    local sekret_file="${TACTICAL_DIR}/tmp/.django_sekret"
    if [ -f "${sekret_file}" ]; then
      SECRET_KEY=$(cat "${sekret_file}")
    else
      SECRET_KEY=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 80 | head -n 1)
      (umask 0177; echo "${SECRET_KEY}" > "${sekret_file}")
    fi
  fi
  if [ -z "${ADMINURL:-}" ]; then
    local adminurl_file="${TACTICAL_DIR}/tmp/.adminurl"
    if [ -f "${adminurl_file}" ]; then
      ADMINURL=$(cat "${adminurl_file}")
    else
      ADMINURL=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 70 | head -n 1)
      (umask 0177; echo "${ADMINURL}" > "${adminurl_file}")
    fi
  fi
  export SECRET_KEY ADMINURL

  copy_custom_code

  run_migrations
  create_superuser_and_api_key

  # Set ownership
  chown -R "${TACTICAL_USER}:${TACTICAL_USER}" "${TACTICAL_DIR}"

  set_ready_status
}

# ===========================================================================
# Entrypoint dispatch
# ===========================================================================

case "${1:-}" in
  tactical-backend)
    tactical_init
    exec uwsgi "${TACTICAL_DIR}/api/app.ini"
    ;;
  tactical-celery)
    worker_init
    exec celery -A tacticalrmm worker --autoscale="${CELERY_AUTOSCALE}" -l info
    ;;
  tactical-celerybeat)
    worker_init
    # rm -f is idiomatic for "remove if exists": unlike `test -f && rm`, it always
    # returns 0 so set -e does not abort when the file is absent on first start.
    rm -f "${TACTICAL_DIR}/api/celerybeat.pid"
    exec celery -A tacticalrmm beat -l info
    ;;
  tactical-websockets)
    worker_init
    export DJANGO_SETTINGS_MODULE=tacticalrmm.settings
    exec uvicorn --host 0.0.0.0 --port 8383 --forwarded-allow-ips='*' tacticalrmm.asgi:application
    ;;
  *)
    echo "ERROR: unknown entrypoint role: ${1:-<none>}"
    echo "Expected one of: tactical-backend, tactical-celery, tactical-celerybeat, tactical-websockets"
    exit 1
    ;;
esac
