#!/usr/bin/env bash
# Tactical RMM - Install script
# See https://docs.tacticalrmm.com/install_server/ for more information.
#

## Script modifiers (e.g. run: export TRMM_SCRIPT_DEBUG="YES")
## Enable verbose script output
: "${TRMM_SCRIPT_DEBUG:="NO"}"
## Switch between production and development branches
: "${TRMM_SCRIPT_BRANCH:="master"}"
## Switch between 'live' and 'staging' ACME servers
: "${TRMM_SCRIPT_ACME_SERVER:="live"}"
## Additional parameters to pass ACME ("--keep-until-expiring")
: "${ACME_ADDITIONAL_PARAMS:=""}"

readonly LOGFILE="install-$(date --iso-8601).log"
## 2022-07-08: Capture script I/O and remove colour codes in the log file.
## This unfortunately requires bash due to '>(...)'. To be improved upon (mkfifo?).
exec 4<&1 5<&2 1>&2 >& >(tee -a >(sed -r 's/\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]//g' >> "${LOGFILE}"))

readonly SCRIPT_EXEC_TS="$(date --iso-8601=seconds)"
printf "%0.s*" {1..80}
printf "\n"
printf "Installation started at %s\n" "${SCRIPT_EXEC_TS}"

readonly SCRIPT_VERSION="66"
readonly SCRIPT_URL="https://raw.githubusercontent.com/amidaware/tacticalrmm/${TRMM_SCRIPT_BRANCH}/install.sh"
readonly TRMM_SERVER_REPO='https://github.com/amidaware/tacticalrmm.git'
readonly TRMM_FRONTEND_REPO='https://github.com/amidaware/tacticalrmm-web'
readonly COMMUNITY_SCRIPTS_REPO='https://github.com/amidaware/community-scripts.git'

readonly TRMM_USER="${USER}"
readonly TRMM_GROUP="${USER}"
readonly TRMM_DB_NAME='tacticalrmm'
readonly WWW_USER="www-data"
readonly WWW_GROUP="www-data"

readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN="\033[0;36m"
readonly RED='\033[0;31m'
readonly NC='\033[0m'

REQ_PYTHON_VER='3.10.4'
TRMM_COMMSCRIPTS_PATH='/opt/trmm-community-scripts'
TRMM_ROOT_PATH='/rmm'
TRMM_SETTINGS_FILE="${TRMM_ROOT_PATH}/api/tacticalrmm/tacticalrmm/settings.py"
TRMM_LOCAL_CONF="${TRMM_ROOT_PATH}/api/tacticalrmm/tacticalrmm/local_settings.py"
TRMM_WEB_PATH="/var/www/rmm"
MESH_ROOT_PATH="/meshcentral"
MESH_CONF_FILE="${MESH_ROOT_PATH}/meshcentral-data/config.json"
NGINX_PATH="/etc/nginx"
NGINX_CONF="${NGINX_PATH}/nginx.conf"
NGINX_PID="/var/run/nginx.pid"
LETS_ENCRYPT_PATH="/etc/letsencrypt"
ETC_CONFD="/etc/conf.d"
CELERY_CONF_FILE="${ETC_CONFD}/celery.conf"
CELERY_LOG_PATH="/var/log/celery"
HOSTS_FILE="/etc/hosts"
SYSTEMD_PATH="/etc/systemd"

## Runtime discovery
CPU_CORES=$(nproc)
NODE_BIN=$(which node)
PYTHON_BIN=$(which python3.10)

################################################################################
## Convert string to lowercase
################################################################################

lc() {
  local char="$*"
  local out
  out="$(echo "$char" | tr "[:upper:]" "[:lower:]")"
  local retval=$?
  echo "$out"
  unset out
  unset char
  return $retval
}

################################################################################
## Convert string to uppercase
################################################################################

uc() {
  local char="$*"
  local out
  out="$(echo "$char" | tr "[:lower:]" "[:upper:]")"
  local retval=$?
  echo "$out"
  unset out char
  return $retval
}

################################################################################
## Random text for password generation
################################################################################

random_text() {
    local min_length="$1"
    local alphanumeric="${2:-"YES"}"
    local transmod='a-zA-Z0-9'
    if [ "$(uc "${alphanumeric}")" = "NO" ]; then
      transmod='a-zA-Z'
    fi
    cat /dev/urandom | tr -dc $transmod | fold -w "${min_length}" | head -n 1
    return
}

################################################################################
## Print info/warnings/errors
################################################################################

print_info() {
  printf "${GREEN}%s${NC}\n" "${1}"
}

print_warn() {
  printf "${YELLOW}%s${NC}\n" "${1}"
}

print_error() {
  printf "${RED}%s${NC}\n" "${1}"
}

print_debug() {
  ## This is currently redundant, I know. Temp workaround. :)
  if [ "$TRMM_SCRIPT_DEBUG" = "YES" ]; then
    printf "${CYAN}%s${NC}\n" "${1}"
  ## todo: log to file when debug is off (mkfifo?)
  # else
  #   printf >&1 "${CYAN}%s${NC}\n" "${1}"
  fi
}

print_header() {
  printf "${GREEN}%0.s-${NC}" {1..80}
  printf "\n"
  print_info "${1}"
  printf "${GREEN}%0.s-${NC}" {1..80}
  printf "\n"
}

################################################################################
## Update Script
################################################################################

update_script() {
  local tmp_file new_version
  tmp_file="$(mktemp -p "" "rmminstall_XXXXXXXXXX")"

  if [ -x "$(which wget)" ]; then
    if [[ "$(wget -q "${SCRIPT_URL}" -O "${tmp_file}")" -eq 0 ]]; then
      new_version=$(grep "SCRIPT_VERSION=" "$tmp_file" | awk -F'[="]' '{print $3}')

      if [ "$TRMM_SCRIPT_DEBUG" = "YES" ]; then
        print_debug "Script version: ${SCRIPT_VERSION}, latest online: ${new_version}"
      fi

      ## todo: 2022-06-17: maybe: change to 'less than' instead?
      if [ "${SCRIPT_VERSION}" -ne "${new_version}" ]; then
        print_warn "Install script is outdated, replacing with the latest version..."
        chmod +x "$tmp_file" && mv -f "$tmp_file" install.sh
        print_warn "Script updated! Please re-run ./install.sh"
        exit 0
      fi
    else
      print_warn "Script update check failed."
    fi

    rm -f "$tmp_file"
  else
    print_warn "wget was not found, skipping script update check."
  fi

  return
}

################################################################################
## Install nginx
################################################################################

install_nginx() {
  print_header 'Installing Nginx'

  wget -qO - https://nginx.org/packages/keys/nginx_signing.key | sudo apt-key add -

  printf "deb https://nginx.org/packages/$OS_NAME/ $OS_CODENAME nginx\ndeb-src https://nginx.org/packages/$OS_NAME/ $OS_CODENAME nginx\n" | sudo tee /etc/apt/sources.list.d/nginx.list

  sudo apt-get update
  sudo apt-get install -y nginx
  sudo systemctl stop nginx

  ## todo: 2022-07-26: redo:
  NGINX_CONF_DATA="$(
  cat << EOF
worker_rlimit_nofile 1000000;
user ${WWW_USER};
worker_processes auto;
pid ${NGINX_PID};
include ${NGINX_PATH}/modules-enabled/*.conf;

events {
    worker_connections 4096;
}

http {
    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;
    server_names_hash_bucket_size 64;
    include ${NGINX_PATH}/mime.types;
    default_type application/octet-stream;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    gzip on;
    include ${NGINX_PATH}/conf.d/*.conf;
    include ${NGINX_PATH}/sites-enabled/*;
}
EOF
  )"
  echo "${NGINX_CONF_DATA}" | sudo tee "${NGINX_CONF}" > /dev/null

  for i in sites-available sites-enabled; do
    sudo mkdir -p "${NGINX_PATH}/$i"
  done

  return
}

################################################################################
## Install NodeJS
################################################################################

install_nodejs() {
  print_header 'Installing NodeJS'

  wget -qO - https://deb.nodesource.com/setup_16.x | sudo -E bash -
  sudo apt-get update
  sudo apt-get install -y gcc g++ make
  sudo apt-get install -y nodejs
  sudo npm install -g npm

  ## todo: 2022-06-17: move
  NODE_BIN=$(which node)

  return
}

################################################################################
## Install MongoDB
################################################################################

install_mongodb() {
  print_header 'Installing MongoDB'

  wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
  echo "$MONGODB_REPO" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
  sudo apt-get update
  sudo apt-get install -y mongodb-org
  sudo systemctl enable mongod
  sudo systemctl restart mongod

  return
}

################################################################################
## Install Python
################################################################################

install_python() {
  ## todo: 2022-06-17: there must be a better way to do this (use 'packaging.version.parse'?)
  if [ ! -x "${PYTHON_BIN}" ] || [ "$(${PYTHON_BIN} --version | cut -d' ' -f2)" != "${REQ_PYTHON_VER}" ]; then
      print_header "Installing Python ${REQ_PYTHON_VER}"

      local python_distname="Python-${REQ_PYTHON_VER}"
      local python_distdir="${HOME}/${python_distname}"
      local python_distfile="${python_distname}.tgz"

      sudo apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev

      if [ ! -d "${python_distdir}" ]; then
        print_debug "Downloading ${python_distfile} to ${HOME}"
        wget -q "https://www.python.org/ftp/python/${REQ_PYTHON_VER}/Python-${REQ_PYTHON_VER}.tgz" -O ~/"${python_distfile}"
        print_debug "Extracting ${python_distfile}"
        cd "${HOME}" && tar -xf "${python_distfile}"
      else
        print_debug "Existing Python build directory found. Running 'make distclean'."
        sudo make --quiet -C "${python_distdir}" distclean
      fi

      cd "${python_distdir}" || exit 1
      ./configure --quiet --enable-optimizations
      make --quiet -j "$CPU_CORES"

      print_debug "Python build finished. Running 'make altinstall'."

      sudo make altinstall

      # if [ "$(sudo make altinstall)" = "0" ]; then
        print_debug "Python was installed successfully. Deleting build directory and source tarball."
        sudo rm -rf "${python_distdir}" "${python_distfile}"
        PYTHON_BIN=$(which python3.10) ## todo: move this
      # else
      #  print_error "Python installation failure, code $?"
      #  exit 1
      # fi
  elif [ "$(${PYTHON_BIN} --version | cut -d' ' -f2)" = "${REQ_PYTHON_VER}" ]; then
    print_info "Python ${REQ_PYTHON_VER} was found, skipping installation."
  else
    print_error "Python is missing."
    exit 1
  fi
  return
}

################################################################################
## Install PostgreSQL
################################################################################

install_postgresql() {
  print_header 'Installing PostgreSQL'

  wget -q -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
  echo "$POSTGRESQL_REPO" | sudo tee /etc/apt/sources.list.d/pgdg.list
  sudo apt-get update
  sudo apt-get install -y postgresql-14
  sleep 2
  sudo systemctl enable postgresql
  sudo systemctl restart postgresql
  sleep 5

  ################################################################################

  ## 2022-07-07: Look for an existing database instance.
  local existing_db existing_user
  existing_db=$(sudo -u postgres psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '${TRMM_DB_NAME}'" | grep -q 1)
  existing_user=$(sudo -u postgres psql -U postgres -tc " SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '${TRMM_DB_USER}'" | grep -q 1)

  if [ "${existing_db}" != "0" ]; then
    print_info 'Creating a new TRMM database instance.'
    sudo -u postgres psql -c "CREATE DATABASE ${TRMM_DB_NAME}"
  else
    print_debug "Found existing TRMM database instance."
  fi

  if [ "${existing_user}" != "0" ]; then
    print_info 'Creating a new TRMM database user.'
    sudo -u postgres psql -c "CREATE USER ${TRMM_DB_USER} WITH PASSWORD '${TRMM_DB_PASS}'"
  else
    print_debug "Found existing TRMM database user."
  fi

  sudo -u postgres psql -c "ALTER ROLE ${TRMM_DB_USER} SET client_encoding TO 'utf8'"
  sudo -u postgres psql -c "ALTER ROLE ${TRMM_DB_USER} SET default_transaction_isolation TO 'read committed'"
  sudo -u postgres psql -c "ALTER ROLE ${TRMM_DB_USER} SET timezone TO 'UTC'"
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${TRMM_DB_NAME} TO ${TRMM_DB_USER}"

  return
}

################################################################################
## Install NATS
################################################################################

install_nats() {
  print_header 'Installing NATS'

  NATS_SERVER_VER=$(grep "^NATS_SERVER_VER" "${TRMM_SETTINGS_FILE}" | awk -F'[= "]' '{print $5}')

  local nats_tmp
  nats_tmp=$(mktemp -d -t "nats-XXXXXXXXXX")
  wget -q "https://github.com/nats-io/nats-server/releases/download/v${NATS_SERVER_VER}/nats-server-v${NATS_SERVER_VER}-linux-amd64.tar.gz" -P "${nats_tmp}"
  tar -xzf "${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-amd64.tar.gz" -C "${nats_tmp}"
  sudo mv "${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-amd64/nats-server" /usr/local/bin/
  sudo chmod +x /usr/local/bin/nats-server
  sudo chown "${TRMM_USER}:${TRMM_GROUP}" /usr/local/bin/nats-server
  rm -rf "${nats_tmp}"

  return
}

################################################################################
## Clear screen (or why not just use 'clear'?)
################################################################################

cls() {
  printf "\033c"
}

################################################################################

update_script

OS_UNAME=$(uname)

## Install dependencies
## todo: 2022-06-17: remove lsb-release
sudo apt-get install -y wget dirmngr gnupg lsb-release

if [ "${OS_UNAME}" = "Linux" ]; then
  OS_NAME=$(lsb_release -si) ## "Ubuntu"
  OS_NAME="${OS_NAME^}" ## Why ^? needed?
  OS_NAME=$(lc "$OS_NAME")
  OS_FULL_REL=$(lsb_release -sd) ## "Ubuntu 20.04.2 LTS"
  OS_CODENAME=$(lsb_release -sc) ## "focal"
  OS_VERSION=$(lsb_release -sr) ## "20.04"
  OS_MAJOR=$(echo "$OS_VERSION" | cut -d. -f1 -) ## "20"
fi

if [ "$TRMM_SCRIPT_DEBUG" = "YES" ]; then
  printf "OS Name: %s (Codename: %s)\n" "${OS_NAME}" "${OS_CODENAME}"
  printf "OS Full Release: %s\n" "${OS_FULL_REL}"
  printf "OS Version: %s (Major: %s)\n" "${OS_VERSION}" "${OS_MAJOR}"
fi

# Fallback if lsb_release -si returns anything else than Ubuntu, Debian or Raspbian
if [ "${OS_NAME}" != "ubuntu" ] && [ "${OS_NAME}" != "debian" ]; then
  OS_NAME=$(grep -oP '(?<=^ID=).+' /etc/os-release | tr -d '"')
  OS_NAME=${OS_NAME^} ## needed? ^?
fi

MONGODB_REPO="deb [arch=amd64] https://repo.mongodb.org/apt/$OS_NAME $OS_CODENAME/mongodb-org/4.4 main"
POSTGRESQL_REPO="deb [arch=amd64] https://apt.postgresql.org/pub/repos/apt/ $OS_CODENAME-pgdg main"

# Determine system
case "${OS_NAME}" in
  "ubuntu")
    if [ "$OS_VERSION" = "20.04" ]; then
      echo "$OS_FULL_REL"
    fi
    MONGODB_REPO="deb [arch=amd64] https://repo.mongodb.org/apt/$OS_NAME $OS_CODENAME/mongodb-org/4.4 multiverse"
  ;;

  "debian")
    if [ "$OS_MAJOR" -ge 10 ]; then
      echo "$OS_FULL_REL"
    fi
    if [ "$OS_MAJOR" -eq 11 ]; then
      # There is no bullseye repo yet for mongo so just use buster on debian 11
      MONGODB_REPO="deb [arch=amd64] https://repo.mongodb.org/apt/$OS_NAME buster/mongodb-org/4.4 main"
    fi
  ;;

  *)
    echo "$OS_FULL_REL"
    print_error "This operating system is unsupported. Please use Ubuntu 20.04 or Debian 10/11"
    exit 1
  ;;
esac

## Check if root
## todo: 2022-06-17: instead of this, run the script as root and avoid sudo altogether
if [ $EUID -eq 0 ]; then
  print_error "Do NOT run this script as root. Exiting."
  exit 1
fi

## Check system locale
if [[ "$LANG" != *".UTF-8" ]]; then
  printf "\n${RED}System locale must be ${GREEN}<some language>.UTF-8${RED} not ${YELLOW}${LANG}${NC}\n"
  print_error "Run the following command and change the default locale to your language of choice\n\n"
  printf "\t"
  print_info "sudo dpkg-reconfigure locales"
  printf "\n\n"
  print_error "You will need to log out & back in for changes to take effect, then re-run this script."
  exit 1
fi

# Prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service

## 2022-07-07: Retrieve existing PGSQL credentials to resume or upgrade an installation (from restore.sh).
if [ -e "${TRMM_LOCAL_CONF}" ]; then
  print_debug "Existing local_settings.py file found; retrieving database credentials."
  TRMM_DB_USER=$(grep -w USER "${TRMM_LOCAL_CONF}" | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')
  TRMM_DB_PASS=$(grep -w PASSWORD "${TRMM_LOCAL_CONF}" | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')
fi

DJANGO_SEKRET=$(random_text 80)
MESH_ADMIN_URL=$(random_text 70)
MESH_USERNAME=$(lc "$(random_text 8 no)")
MESH_PASSWORD=$(random_text 25)
TRMM_DB_USER=${TRMM_DB_USER:=$(lc "$(random_text 8 no)")}
TRMM_DB_PASS=${TRMM_DB_PASS:=$(random_text 20)}

if [ "$TRMM_SCRIPT_DEBUG" = "YES" ]; then
  ## 2022-07-08: Redirecting passwords to >&4 (stdout) so they don't appear in the logfile.
  printf >&4 "Django Secret: %s\n" "${DJANGO_SEKRET}"
  printf >&4 "Mesh Admin URL: %s\n" "${MESH_ADMIN_URL}"
  printf "Mesh Username: %s\n" "${MESH_USERNAME}"
  printf >&4 "Mesh Password: %s\n" "${MESH_PASSWORD}"
  printf "TRMM DB Username: %s\n" "${TRMM_DB_USER}"
  printf >&4 "TRMM DB Password: %s\n" "${TRMM_DB_PASS}"
  printf "TRMM DB Database: %s\n" "${TRMM_DB_NAME}"
  print_debug "Script branch: ${TRMM_SCRIPT_BRANCH}"
else
  cls
fi

## 2022-07-05: Ask the user for the root FQDN first to (optionally) auto-fill the subdomains later.
while [[ $USER_ROOT_DOMAIN != *[.]* ]]; do
  read -p "Enter the root domain for your instance (e.g. example.com or example.co.uk): " USER_ROOT_DOMAIN
done

DEFAULT_BACKEND_DOMAIN="api.$USER_ROOT_DOMAIN"
DEFAULT_FRONTEND_DOMAIN="rmm.$USER_ROOT_DOMAIN"
DEFAULT_MESH_DOMAIN="mesh.$USER_ROOT_DOMAIN"

while [[ $USER_BACKEND_DOMAIN != *[.]*[.]* ]]; do
  read -p "Enter the subdomain for the backend [${DEFAULT_BACKEND_DOMAIN}]: " USER_BACKEND_DOMAIN
  if [ -z "$USER_BACKEND_DOMAIN" ]; then
    USER_BACKEND_DOMAIN=${USER_BACKEND_DOMAIN:-$DEFAULT_BACKEND_DOMAIN}
    break
  fi
done

while [[ $USER_FRONTEND_DOMAIN != *[.]*[.]* ]]; do
  read -p "Enter the subdomain for the frontend [${DEFAULT_FRONTEND_DOMAIN}]: " USER_FRONTEND_DOMAIN
  if [ -z "$USER_FRONTEND_DOMAIN" ]; then
    USER_FRONTEND_DOMAIN=${USER_FRONTEND_DOMAIN:-$DEFAULT_FRONTEND_DOMAIN}
    break
  fi
done

while [[ $USER_MESH_DOMAIN != *[.]*[.]* ]]; do
  read -p "Enter the subdomain for MeshCentral [${DEFAULT_MESH_DOMAIN}]: " USER_MESH_DOMAIN
  if [ -z "$USER_MESH_DOMAIN" ]; then
    USER_MESH_DOMAIN=${USER_MESH_DOMAIN:-$DEFAULT_MESH_DOMAIN}
    break
  fi
done

print_debug "Root domain: $USER_ROOT_DOMAIN"
print_debug "Backend domain: $USER_BACKEND_DOMAIN"
print_debug "Frontend domain: $USER_FRONTEND_DOMAIN"
print_debug "Mesh domain: $USER_MESH_DOMAIN"

while [[ $USER_EMAIL_ADDRESS != *[@]*[.]* ]]; do
  read -p "Enter a valid email address for Django and MeshCentral: " USER_EMAIL_ADDRESS
done

# If the server is behind NAT, we need to add the 3 subdomains to the host file
# so that nginx can properly route between the frontend, backend and MeshCentral
# EDIT 8-29-2020
# Running this even if the server is __not__ behind NAT just to make DNS resolving faster.
# This also allows the install script to properly finish even if DNS has not fully propagated
CHECK_HOSTS=$(grep '127.0.1.1' "$HOSTS_FILE" | grep "$USER_BACKEND_DOMAIN" | grep "$USER_MESH_DOMAIN" | grep "$USER_FRONTEND_DOMAIN")
HAS_LOCALHOST=$(grep '127.0.1.1' "$HOSTS_FILE")

if ! [[ $CHECK_HOSTS ]]; then
  print_header 'Adding subdomains to the hosts file'
  if [[ $HAS_LOCALHOST ]]; then
    sudo sed -i "/127.0.1.1/s/$/ ${USER_BACKEND_DOMAIN} ${USER_FRONTEND_DOMAIN} ${USER_MESH_DOMAIN}/" "$HOSTS_FILE"
  else
    echo "127.0.1.1 ${USER_BACKEND_DOMAIN} ${USER_FRONTEND_DOMAIN} ${USER_MESH_DOMAIN}" | sudo tee --append "$HOSTS_FILE" >/dev/null
  fi
fi

BEHIND_NAT=false
IPV4=$(ip -4 addr | sed -ne 's|^.* inet \([^/]*\)/.* scope global.*$|\1|p' | head -1)
if echo "$IPV4" | grep -qE '^(10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.|192\.168)'; then
  BEHIND_NAT=true
fi

################################################################################

print_header "Installing Let's Encrypt"

sudo apt-get install -y software-properties-common
sudo apt-get update
sudo apt-get install -y certbot openssl

print_header 'Preparing certificate request'

if [ "${TRMM_SCRIPT_ACME_SERVER}" = "staging" ]; then
  ACME_ADDITIONAL_PARAMS="${ACME_ADDITIONAL_PARAMS} --test-cert"
fi

CERTBOT_CMD="sudo certbot certonly --manual -d \"*.${USER_ROOT_DOMAIN}\" --agree-tos --no-bootstrap --preferred-challenges dns -m \"${USER_EMAIL_ADDRESS}\" --no-eff-email ${ACME_ADDITIONAL_PARAMS}"

print_debug "Certbot command: ${CERTBOT_CMD}"

eval "${CERTBOT_CMD}"

while [[ $? -ne 0 ]]; do
  eval "${CERTBOT_CMD}"
done

readonly CERT_PRIV_KEY="${LETS_ENCRYPT_PATH}/${TRMM_SCRIPT_ACME_SERVER}/${USER_ROOT_DOMAIN}/privkey.pem"
readonly CERT_PUB_KEY="${LETS_ENCRYPT_PATH}/${TRMM_SCRIPT_ACME_SERVER}/${USER_ROOT_DOMAIN}/fullchain.pem"

sudo chown "${TRMM_USER}:${TRMM_GROUP}" -R "${LETS_ENCRYPT_PATH}"
sudo chmod 775 -R "${LETS_ENCRYPT_PATH}"

################################################################################

install_nginx

install_nodejs

install_mongodb

install_python

################################################################################

print_header 'Installing redis and git'

sudo apt-get install -y ca-certificates redis git

################################################################################

install_postgresql

################################################################################

print_header 'Cloning repos'

sudo mkdir "${TRMM_ROOT_PATH}"
sudo chown "${TRMM_USER}:${TRMM_GROUP}" "${TRMM_ROOT_PATH}"
sudo mkdir -p "${CELERY_LOG_PATH}"
sudo chown "${TRMM_USER}:${TRMM_GROUP}" "${CELERY_LOG_PATH}"

git clone "${TRMM_SERVER_REPO}" "${TRMM_ROOT_PATH}/"
cd "${TRMM_ROOT_PATH}"
git config user.email "admin@example.com"
git config user.name "Bob"
git checkout "${TRMM_SCRIPT_BRANCH}"

sudo mkdir -p "${TRMM_COMMSCRIPTS_PATH}"
sudo chown "${TRMM_USER}:${TRMM_GROUP}" "${TRMM_COMMSCRIPTS_PATH}"
git clone "${COMMUNITY_SCRIPTS_REPO}" "${TRMM_COMMSCRIPTS_PATH}/"
cd "${TRMM_COMMSCRIPTS_PATH}"
git config user.email "admin@example.com"
git config user.name "Bob"
git checkout main

################################################################################

install_nats

################################################################################

print_header 'Installing MeshCentral'

MESH_VER=$(grep "^MESH_VER" "${TRMM_SETTINGS_FILE}" | awk -F'[= "]' '{print $5}')

sudo mkdir -p "${MESH_ROOT_PATH}/meshcentral-data"
sudo chown "${TRMM_USER}:${TRMM_GROUP}" -R "${MESH_ROOT_PATH}"
cd "${MESH_ROOT_PATH}"
npm install "meshcentral@${MESH_VER}"
sudo chown "${TRMM_USER}:${TRMM_GROUP}" -R "${MESH_ROOT_PATH}"

## todo: 2022-06-17: redo:
MESH_CONF_DATA="$(
  cat <<EOF
{
  "settings": {
    "Cert": "${USER_MESH_DOMAIN}",
    "MongoDb": "mongodb://127.0.0.1:27017",
    "MongoDbName": "meshcentral",
    "WANonly": true,
    "Minify": 1,
    "Port": 4430,
    "AliasPort": 443,
    "RedirPort": 800,
    "AllowLoginToken": true,
    "AllowFraming": true,
    "_AgentPing": 60,
    "AgentPong": 300,
    "AllowHighQualityDesktop": true,
    "TlsOffload": "127.0.0.1",
    "agentCoreDump": false,
    "Compression": true,
    "WsCompression": true,
    "AgentWsCompression": true,
    "MaxInvalidLogin": { "time": 5, "count": 5, "coolofftime": 30 }
  },
  "domains": {
    "": {
      "Title": "Tactical RMM",
      "Title2": "Tactical RMM",
      "NewAccounts": false,
      "CertUrl": "https://${USER_MESH_DOMAIN}:443/",
      "GeoLocation": true,
      "CookieIpCheck": false,
      "mstsc": true
    }
  }
}
EOF
)"
echo "${MESH_CONF_DATA}" >"${MESH_CONF_FILE}"

## todo: 2022-06-17: redo:
TRMM_LOCAL_CONF_DATA="$(
  cat <<EOF
SECRET_KEY = "${DJANGO_SEKRET}"

DEBUG = False

ALLOWED_HOSTS = ['${USER_BACKEND_DOMAIN}']

ADMIN_URL = "${MESH_ADMIN_URL}/"

CORS_ORIGIN_WHITELIST = [
    "https://${USER_FRONTEND_DOMAIN}"
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${TRMM_DB_NAME}',
        'USER': '${TRMM_DB_USER}',
        'PASSWORD': '${TRMM_DB_PASS}',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

MESH_USERNAME = "${MESH_USERNAME}"
MESH_SITE = "https://${USER_MESH_DOMAIN}"
REDIS_HOST    = "localhost"
ADMIN_ENABLED = True
EOF
)"
echo "${TRMM_LOCAL_CONF_DATA}" >"${TRMM_LOCAL_CONF}"

## todo: 2022-06-17: verify:
sudo cp "${TRMM_ROOT_PATH}/natsapi/bin/nats-api" /usr/local/bin
sudo chown "${TRMM_USER}:${TRMM_GROUP}" /usr/local/bin/nats-api
sudo chmod +x /usr/local/bin/nats-api

print_header 'Installing the backend'

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" "$TRMM_SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" "$TRMM_SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

cd "${TRMM_ROOT_PATH}/api"
${PYTHON_BIN} -m venv env
source "${TRMM_ROOT_PATH}/api/env/bin/activate"
cd "${TRMM_ROOT_PATH}/api/tacticalrmm"
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools=="${SETUPTOOLS_VER}" wheel=="${WHEEL_VER}"
pip install --no-cache-dir -r "${TRMM_ROOT_PATH}/api/tacticalrmm/requirements.txt"
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py create_natsapi_conf
python manage.py load_chocos
python manage.py load_community_scripts
WEB_VERSION=$(python manage.py get_config webversion)

printf "${YELLOW}%0.s*${NC}" {1..80}
printf "\n"
printf "${YELLOW}Please create your login for the RMM website and django admin${NC}\n"
printf "${YELLOW}%0.s*${NC}" {1..80}
printf "\n"

echo -ne "Username: "
read djangousername
python manage.py createsuperuser --username ${djangousername} --email ${USER_EMAIL_ADDRESS}
python manage.py create_installer_user
RANDBASE=$(python manage.py generate_totp)
cls
python manage.py generate_barcode ${RANDBASE} ${djangousername} ${USER_FRONTEND_DOMAIN}
deactivate
read -n 1 -s -r -p "Press any key to continue..."

## todo: 2022-06-17: redo:
uwsgini="$(
  cat <<EOF
[uwsgi]
chdir = ${TRMM_ROOT_PATH}/api/tacticalrmm
module = tacticalrmm.wsgi
home = ${TRMM_ROOT_PATH}/api/env
master = true
enable-threads = true
socket = ${TRMM_ROOT_PATH}/api/tacticalrmm/tacticalrmm.sock
harakiri = 300
chmod-socket = 660
buffer-size = 65535
vacuum = true
die-on-term = true
max-requests = 500
disable-logging = true
cheaper-algo = busyness
cheaper = 4
cheaper-initial = 4
workers = 20
cheaper-step = 2
cheaper-overload = 3
cheaper-busyness-min = 5
cheaper-busyness-max = 10
# stats = /tmp/stats.socket # uncomment when debugging
# cheaper-busyness-verbose = true # uncomment when debugging
EOF
)"
echo "${uwsgini}" >${TRMM_ROOT_PATH}/api/tacticalrmm/app.ini

## todo: 2022-06-17: redo:
rmmservice="$(
  cat <<EOF
[Unit]
Description=tacticalrmm uwsgi daemon
After=network.target postgresql.service

[Service]
User=${TRMM_USER}
Group=${WWW_GROUP}
WorkingDirectory=${TRMM_ROOT_PATH}/api/tacticalrmm
Environment="PATH=${TRMM_ROOT_PATH}/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${TRMM_ROOT_PATH}/api/env/bin/uwsgi --ini app.ini
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${rmmservice}" | sudo tee "${SYSTEMD_PATH}/system/rmm.service" >/dev/null

## todo: 2022-06-17: redo:
daphneservice="$(
  cat <<EOF
[Unit]
Description=django channels daemon
After=network.target

[Service]
User=${TRMM_USER}
Group=${WWW_GROUP}
WorkingDirectory=${TRMM_ROOT_PATH}/api/tacticalrmm
Environment="PATH=${TRMM_ROOT_PATH}/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${TRMM_ROOT_PATH}/api/env/bin/daphne -u ${TRMM_ROOT_PATH}/daphne.sock tacticalrmm.asgi:application
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${daphneservice}" | sudo tee "${SYSTEMD_PATH}/system/daphne.service" >/dev/null

## todo: 2022-06-17: redo:
natsservice="$(
  cat <<EOF
[Unit]
Description=NATS Server
After=network.target

[Service]
PrivateTmp=true
Type=simple
ExecStart=/usr/local/bin/nats-server -c ${TRMM_ROOT_PATH}/api/tacticalrmm/nats-rmm.conf
ExecReload=/usr/bin/kill -s HUP \$MAINPID
ExecStop=/usr/bin/kill -s SIGINT \$MAINPID
User=${TRMM_USER}
Group=${WWW_GROUP}
Restart=always
RestartSec=5s
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsservice}" | sudo tee "${SYSTEMD_PATH}/system/nats.service" >/dev/null

## todo: 2022-06-17: redo:
natsapi="$(
  cat <<EOF
[Unit]
Description=TacticalRMM Nats Api v1
After=nats.service

[Service]
Type=simple
ExecStart=/usr/local/bin/nats-api
User=${TRMM_USER}
Group=${TRMM_GROUP}
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsapi}" | sudo tee "${SYSTEMD_PATH}/system/nats-api.service" >/dev/null

## todo: 2022-06-17: redo:
nginxrmm="$(
  cat <<EOF
server_tokens off;

upstream tacticalrmm {
    server unix:///${TRMM_ROOT_PATH}/api/tacticalrmm/tacticalrmm.sock;
}

map \$http_user_agent \$ignore_ua {
    "~python-requests.*" 0;
    "~go-resty.*" 0;
    default 1;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${USER_BACKEND_DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl reuseport;
    listen [::]:443 ssl;
    server_name ${USER_BACKEND_DOMAIN};
    client_max_body_size 300M;
    access_log "${TRMM_ROOT_PATH}/api/tacticalrmm/tacticalrmm/private/log/access.log" combined if=\$ignore_ua;
    error_log "${TRMM_ROOT_PATH}/api/tacticalrmm/tacticalrmm/private/log/error.log";
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;
    
    location /static/ {
        root "${TRMM_ROOT_PATH}/api/tacticalrmm";
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${USER_FRONTEND_DOMAIN}";
        alias "${TRMM_ROOT_PATH}/api/tacticalrmm/tacticalrmm/private/";
    }

    location ~ ^/ws/ {
        proxy_pass http://unix:${TRMM_ROOT_PATH}/daphne.sock;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect     off;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host \$server_name;
    }

    location ~ ^/natsws {
        proxy_pass http://127.0.0.1:9235;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Host \$host:\$server_port;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        uwsgi_pass  tacticalrmm;
        include     ${NGINX_PATH}/uwsgi_params;
        uwsgi_read_timeout 300s;
        uwsgi_ignore_client_abort on;
    }
}
EOF
)"
echo "${nginxrmm}" | sudo tee "${NGINX_PATH}/sites-available/rmm.conf" >/dev/null

## todo: 2022-06-17: redo:
nginxmesh="$(
  cat <<EOF
server {
  listen 80;
  listen [::]:80;
  server_name ${USER_MESH_DOMAIN};
  return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${USER_MESH_DOMAIN};
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};

    ssl_session_cache shared:WEBSSL:10m;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://127.0.0.1:4430/;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Host \$host:\$server_port;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
)"
echo "${nginxmesh}" | sudo tee "${NGINX_PATH}/sites-available/meshcentral.conf" >/dev/null

sudo ln -s "${NGINX_PATH}/sites-available/rmm.conf" "${NGINX_PATH}/sites-enabled/rmm.conf"
sudo ln -s "${NGINX_PATH}/sites-available/meshcentral.conf" "${NGINX_PATH}/sites-enabled/meshcentral.conf"

sudo mkdir "${ETC_CONFD}"

## todo: 2022-06-17: redo:
celeryservice="$(
  cat <<EOF
[Unit]
Description=Celery Service V2
After=network.target redis-server.service postgresql.service

[Service]
Type=forking
User=${TRMM_USER}
Group=${TRMM_GROUP}
EnvironmentFile=${CELERY_CONF_FILE}
WorkingDirectory=${TRMM_ROOT_PATH}/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi start \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --loglevel="\${CELERYD_LOG_LEVEL}"'
ExecReload=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi restart \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celeryservice}" | sudo tee "${SYSTEMD_PATH}/system/celery.service" >/dev/null

## todo: 2022-06-17: redo:
celeryconf="$(
  cat <<EOF
CELERYD_NODES="w1"

CELERY_BIN="${TRMM_ROOT_PATH}/api/env/bin/celery"

CELERY_APP="tacticalrmm"

CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=86400 --autoscale=20,2"

CELERYD_PID_FILE="${TRMM_ROOT_PATH}/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="${CELERY_LOG_PATH}/%n%I.log"
CELERYD_LOG_LEVEL="ERROR"

CELERYBEAT_PID_FILE="${TRMM_ROOT_PATH}/api/tacticalrmm/beat.pid"
CELERYBEAT_LOG_FILE="${CELERY_LOG_PATH}/beat.log"
EOF
)"
echo "${celeryconf}" | sudo tee ${CELERY_CONF_FILE} >/dev/null

## todo: 2022-06-17: redo:
celerybeatservice="$(
  cat <<EOF
[Unit]
Description=Celery Beat Service V2
After=network.target redis-server.service postgresql.service

[Service]
Type=simple
User=${TRMM_USER}
Group=${TRMM_GROUP}
EnvironmentFile=${CELERY_CONF_FILE}
WorkingDirectory=${TRMM_ROOT_PATH}/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \${CELERY_APP} beat --pidfile=\${CELERYBEAT_PID_FILE} --logfile=\${CELERYBEAT_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL}'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerybeatservice}" | sudo tee "${SYSTEMD_PATH}/system/celerybeat.service" >/dev/null

sudo chown "${TRMM_USER}:${TRMM_GROUP}" -R "${ETC_CONFD}"

## todo: 2022-06-17: redo:
meshservice="$(
  cat <<EOF
[Unit]
Description=MeshCentral Server
After=network.target mongod.service nginx.service
[Service]
Type=simple
LimitNOFILE=1000000
ExecStart=${NODE_BIN} node_modules/meshcentral
Environment=NODE_ENV=production
WorkingDirectory=${MESH_ROOT_PATH}
User=${TRMM_USER}
Group=${TRMM_GROUP}
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${meshservice}" | sudo tee "${SYSTEMD_PATH}/system/meshcentral.service" >/dev/null

sudo systemctl daemon-reload

if [ -d ~/.npm ]; then
  sudo chown -R "${TRMM_USER}:${TRMM_GROUP}" ~/.npm
fi

if [ -d ~/.config ]; then
  sudo chown -R "${TRMM_USER}:${TRMM_GROUP}" ~/.config
fi

################################################################################

print_header 'Installing the frontend'

webtar="trmm-web-v${WEB_VERSION}.tar.gz"
wget -q "${TRMM_FRONTEND_REPO}/releases/download/v${WEB_VERSION}/${webtar}" -O "/tmp/${webtar}"
sudo mkdir -p "${TRMM_WEB_PATH}"
sudo tar -xzf /tmp/${webtar} -C ${TRMM_WEB_PATH}
echo "window._env_ = {PROD_URL: \"https://${USER_BACKEND_DOMAIN}\"}" | sudo tee "${TRMM_WEB_PATH}/dist/env-config.js" >/dev/null
sudo chown "${WWW_USER}:${WWW_GROUP}" -R "${TRMM_WEB_PATH}/dist"
rm -f "/tmp/${webtar}"

nginxfrontend="$(
  cat <<EOF
server {
    server_name ${USER_FRONTEND_DOMAIN};
    charset utf-8;
    location / {
        root "${TRMM_WEB_PATH}/dist";
        try_files \$uri \$uri/ /index.html;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
    }
    error_log  /var/log/nginx/frontend-error.log;
    access_log /var/log/nginx/frontend-access.log;

    listen 443 ssl;
    listen [::]:443 ssl;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;
}

server {
    if (\$host = ${USER_FRONTEND_DOMAIN}) {
        return 301 https://\$host\$request_uri;
    }

    listen 80;
    listen [::]:80;
    server_name ${USER_FRONTEND_DOMAIN};
    return 404;
}
EOF
)"
echo "${nginxfrontend}" | sudo tee "${NGINX_PATH}/sites-available/frontend.conf" >/dev/null

sudo ln -s "${NGINX_PATH}/sites-available/frontend.conf" "${NGINX_PATH}/sites-enabled/frontend.conf"

################################################################################

print_header 'Enabling Services'

for i in rmm.service daphne.service celery.service celerybeat.service nginx; do
  sudo systemctl enable ${i}
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done
sleep 5
sudo systemctl enable meshcentral

print_header 'Starting MeshCentral and waiting for it to install plugins'

sudo systemctl restart meshcentral

sleep 3

# The first time we start meshcentral, it will need some time to generate certs and install plugins.
# This will take anywhere from a few seconds to a few minutes depending on the server's hardware
# We will know it's ready once the last line of the systemd service stdout is 'MeshCentral HTTP server running on port.....'
while ! [[ $CHECK_MESH_READY ]]; do
  CHECK_MESH_READY=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  print_warn "MeshCentral is not ready yet..."
  sleep 3
done

print_header 'Generating MeshCentral login token key'

MESHTOKENKEY=$(${NODE_BIN} "${MESH_ROOT_PATH}/node_modules/meshcentral" --logintokenkey)

meshtoken="$(
  cat <<EOF
MESH_TOKEN_KEY = "${MESHTOKENKEY}"
EOF
)"
echo "${meshtoken}" | tee --append "${TRMM_LOCAL_CONF}" >/dev/null

print_header 'Creating MeshCentral account and group'

sudo systemctl stop meshcentral
sleep 1
cd "${MESH_ROOT_PATH}"

${NODE_BIN} node_modules/meshcentral --createaccount "${MESH_USERNAME}" --pass "${MESH_PASSWORD}" --email "${USER_EMAIL_ADDRESS}"
sleep 1
${NODE_BIN} node_modules/meshcentral --adminaccount "${MESH_USERNAME}"

sudo systemctl start meshcentral
sleep 5

while ! [[ $CHECK_MESH_READY2 ]]; do
  CHECK_MESH_READY2=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  print_warn "MeshCentral is not ready yet"
  sleep 3
done

${NODE_BIN} node_modules/meshcentral/meshctrl.js --url "wss://${USER_MESH_DOMAIN}:443" --loginuser "${MESH_USERNAME}" --loginpass "${MESH_PASSWORD}" AddDeviceGroup --name TacticalRMM
sleep 1

sudo systemctl enable nats.service
cd "${TRMM_ROOT_PATH}/api/tacticalrmm"
source "${TRMM_ROOT_PATH}/api/env/bin/activate"
python manage.py initial_db_setup
python manage.py reload_nats
deactivate
sudo systemctl start nats.service

sleep 1
sudo systemctl enable nats-api.service
sudo systemctl start nats-api.service

## disable django admin
sed -i 's/ADMIN_ENABLED = True/ADMIN_ENABLED = False/g' "${TRMM_SETTINGS_FILE}"

print_header 'Restarting services'

for i in rmm.service daphne.service celery.service celerybeat.service; do
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done

## 2022-07-08: Redirecting passwords to >&4 so they don't appear in the logfile.
printf "${YELLOW}%0.s*${NC}" {1..80}
printf "\n\n"
printf "${YELLOW}Installation complete!${NC}\n\n"
printf "${YELLOW}Access your rmm at: ${GREEN}https://${USER_FRONTEND_DOMAIN}${NC}\n\n"
printf >&4 "${YELLOW}Django admin url (disabled by default): ${GREEN}https://${USER_BACKEND_DOMAIN}/${MESH_ADMIN_URL}/${NC}\n\n"
printf "${YELLOW}MeshCentral username: ${GREEN}${MESH_USERNAME}${NC}\n"
printf >&4 "${YELLOW}MeshCentral password: ${GREEN}${MESH_PASSWORD}${NC}\n\n"

if [ "$BEHIND_NAT" = true ]; then
  echo -ne "${YELLOW}Read below if your router does NOT support Hairpin NAT${NC}\n\n"
  echo -ne "${GREEN}If you will be accessing the web interface of the RMM from the same LAN as this server,${NC}\n"
  echo -ne "${GREEN}you'll need to make sure your 3 subdomains resolve to ${IPV4}${NC}\n"
  echo -ne "${GREEN}This also applies to any agents that will be on the same local network as the rmm.${NC}\n"
  echo -ne "${GREEN}You'll also need to setup port forwarding in your router on port 443.${NC}\n\n"
fi

printf "${YELLOW}Please refer to the Github README for next steps${NC}\n\n"
printf "${YELLOW}%0.s*${NC}" {1..80}
printf "\n"

printf "Installation ended at %s\n" "$(date --iso-8601=seconds)"
printf "%0.s*" {1..80}
printf "\n"

## Sleep 1 second to flush, restore & close file descriptors
sleep 1
exec 1<&4 4>&- 2<&5 5>&-
