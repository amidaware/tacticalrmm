#!/usr/bin/env bash

SCRIPT_VERSION="86"
SCRIPT_URL="https://raw.githubusercontent.com/amidaware/tacticalrmm/master/install.sh"

ID_LIKE=$(grep ^ID_LIKE /etc/os-release | awk -F'[="]' '{print $3}')

if [[ "${ID_LIKE}" == *rhel* ]]; then
  if command -v dnf >/dev/null 2>&1; then
    RHEL_PKG_MGR="dnf"
  else
    RHEL_PKG_MGR="yum"
  fi
fi

if [[ "${ID_LIKE}" == *debian* ]]; then
  sudo apt install -y curl wget dirmngr gnupg lsb-release ca-certificates
  sudo apt install -y software-properties-common
  sudo apt update
  sudo apt install -y openssl
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  sudo $RHEL_PKG_MGR install -y epel-release
  sudo $RHEL_PKG_MGR install -y curl wget gnupg2 ca-certificates openssl lsb_release
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.11.8'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'
local_settings='/rmm/api/tacticalrmm/tacticalrmm/local_settings.py'

TMP_FILE=$(mktemp -p "" "rmminstall_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" >${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" -ne "${NEW_VER}" ]; then
  printf >&2 "${YELLOW}Old install script detected, downloading and replacing with the latest version...${NC}\n"
  wget -q "${SCRIPT_URL}" -O install.sh
  printf >&2 "${YELLOW}Script updated! Please re-run ./install.sh${NC}\n"
  rm -f $TMP_FILE
  exit 1
fi

rm -f $TMP_FILE

if [[ "${ID_LIKE}" == *debian* ]]; then
  export DEBIAN_FRONTEND=noninteractive
fi

if [ -d /rmm/api/tacticalrmm ]; then
  echo -ne "${RED}ERROR: Existing trmm installation found. The install script must be run on a clean server.${NC}\n"
  exit 1
fi

arch=$(uname -m)
if [[ "$arch" != "x86_64" ]] && [[ "$arch" != "aarch64" ]]; then
  echo -ne "${RED}ERROR: Only x86_64 and aarch64 is supported, not ${arch}${NC}\n"
  exit 1
fi

memTotal=$(grep -i memtotal /proc/meminfo | awk '{print $2}')
if [[ $memTotal -lt 3627528 ]]; then
  echo -ne "${RED}ERROR: A minimum of 4GB of RAM is required.${NC}\n"
  exit 1
fi

osname=$(lsb_release -si)
osname=${osname^}
osname=$(echo "$osname" | tr '[A-Z]' '[a-z]')
fullrel=$(lsb_release -sd)
codename=$(lsb_release -sc)
relno=$(lsb_release -sr | cut -d. -f1)
fullrelno=$(lsb_release -sr)

not_supported() {
  echo -ne "${RED}ERROR: Only Debian 11, Debian 12, Ubuntu 22.04, and RHEL 7+ (and compatible derivatives) are supported.${NC}\n"
}

if [[ "$osname" == "debian" ]]; then
  if [[ "$relno" -ne 11 && "$relno" -ne 12 ]]; then
    not_supported
    exit 1
  fi
elif [[ "$osname" == "ubuntu" ]]; then
  if [[ "$fullrelno" != "22.04" ]]; then
    not_supported
    exit 1
  fi
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  if [[ "$relno" -lt 7 ]]; then
    not_supported
    exit 1
  fi
else
  not_supported
  exit 1
fi

if dpkg -l | grep -qi turnkey; then
  echo -ne "${RED}Turnkey linux is not supported. Please use the official debian/ubuntu ISO.${NC}\n"
  exit 1
fi

if ps aux | grep -v grep | grep -qi webmin; then
  echo -ne "${RED}Webmin running, should not be installed. Please use the official debian/ubuntu or RHEL ISO.${NC}\n"
  exit 1
fi

if [ $EUID -eq 0 ]; then
  echo -ne "${RED}Do NOT run this script as root. Exiting.${NC}\n"
  exit 1
fi

if [[ "$LANG" != *".UTF-8" ]]; then
  printf >&2 "\n${RED}System locale must be ${GREEN}<some language>.UTF-8${RED} not ${YELLOW}${LANG}${NC}\n"
  printf >&2 "${RED}Run the following command and change the default locale to your language of choice${NC}\n\n"
  if [[ "${ID_LIKE}" == *debian* ]]; then
    printf >&2 "${GREEN}sudo dpkg-reconfigure locales${NC}\n\n"
  elif [[ "${ID_LIKE}" == *rhel* ]]; then
    printf >&2 "${GREEN}sudo localectl set-locale LANG=<some language>.UTF-8${NC}\n\n"
  fi
  printf >&2 "${RED}You will need to log out and back in for changes to take effect, then re-run this script.${NC}\n\n"
  exit 1
fi

if [ "$arch" = "x86_64" ]; then
  pgarch='amd64'
else
  pgarch='arm64'
fi

# prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service

DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 80 | head -n 1)
ADMINURL=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 70 | head -n 1)
MESHPASSWD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 25 | head -n 1)
pgusername=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
pgpw=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)
meshusername=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
MESHPGUSER=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
MESHPGPWD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)

cls() {
  printf "\033c"
}

print_green() {
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
  printf >&2 "${GREEN}${1}${NC}\n"
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
}

print_error() {
  printf >&2 "${RED}${1}${NC}\n"
}

print_yellow() {
  printf >&2 "${YELLOW}${1}${NC}\n"
}

cls

while [[ $rmmdomain != *[.]*[.]* ]]; do
  echo -ne "${YELLOW}Enter the subdomain for the backend (e.g. api.example.com)${NC}: "
  read rmmdomain
done

while [[ $frontenddomain != *[.]*[.]* ]]; do
  echo -ne "${YELLOW}Enter the subdomain for the frontend (e.g. rmm.example.com)${NC}: "
  read frontenddomain
done

while [[ $meshdomain != *[.]*[.]* ]]; do
  echo -ne "${YELLOW}Enter the subdomain for meshcentral (e.g. mesh.example.com)${NC}: "
  read meshdomain
done

echo -ne "${YELLOW}Enter the root domain (e.g. example.com or example.co.uk)${NC}: "
read rootdomain

while [[ $letsemail != *[@]*[.]* ]]; do
  echo -ne "${YELLOW}Enter a valid email address for django and meshcentral${NC}: "
  read letsemail
done

byocert=false
if [[ $* == *--use-own-cert* ]]; then
  byocert=true
fi

if [[ "$byocert" = true ]]; then
  while true; do

    print_yellow "Please enter the full path to your fullchain.pem file:"
    read -r fullchain_path
    print_yellow "Please enter the full path to your privkey.pem file:"
    read -r privkey_path

    if [[ ! -f "$fullchain_path" || ! -f "$privkey_path" ]]; then
      print_error "One or both files do not exist. Please try again."
      continue
    fi

    openssl x509 -in "$fullchain_path" -noout >/dev/null
    if [[ $? -ne 0 ]]; then
      print_error "ERROR: The provided file is not a valid certificate."
      exit 1
    fi

    break
  done
fi

if grep -q manage_etc_hosts /etc/hosts; then
  sudo sed -i '/manage_etc_hosts: true/d' /etc/cloud/cloud.cfg >/dev/null
  echo -e "\nmanage_etc_hosts: false" | sudo tee --append /etc/cloud/cloud.cfg >/dev/null
  sudo systemctl restart cloud-init >/dev/null
fi

CHECK_HOSTS=$(grep 127.0.1.1 /etc/hosts | grep "$rmmdomain" | grep "$meshdomain" | grep "$frontenddomain")
HAS_11=$(grep 127.0.1.1 /etc/hosts)

if ! [[ $CHECK_HOSTS ]]; then
  print_green 'Adding subdomains to hosts file'
  if [[ $HAS_11 ]]; then
    sudo sed -i "/127.0.1.1/s/$/ ${rmmdomain} ${frontenddomain} ${meshdomain}/" /etc/hosts
  else
    echo "127.0.1.1 ${rmmdomain} ${frontenddomain} ${meshdomain}" | sudo tee --append /etc/hosts >/dev/null
  fi
fi

BEHIND_NAT=false
IPV4=$(ip -4 addr | sed -ne 's|^.* inet \([^/]*\)/.* scope global.*$|\1|p' | head -1)
if echo "$IPV4" | grep -qE '^(10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.|192\.168)'; then
  BEHIND_NAT=true
fi

insecure=false
if [[ $* == *--insecure* ]]; then
  insecure=true
fi

if [[ "$insecure" = true ]]; then
  print_green 'Generating self-signed cert'
  certdir='/etc/ssl/tactical'
  sudo mkdir -p $certdir
  sudo chown ${USER}:${USER} $certdir
  sudo chmod 770 $certdir
  CERT_PRIV_KEY=${certdir}/key.pem
  CERT_PUB_KEY=${certdir}/cert.pem
  openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 \
    -nodes -keyout ${CERT_PRIV_KEY} -out ${CERT_PUB_KEY} -subj "/CN=${rootdomain}" \
    -addext "subjectAltName=DNS:${rootdomain},DNS:*.${rootdomain}"

elif [[ "$byocert" = true ]]; then
  CERT_PRIV_KEY=$privkey_path
  CERT_PUB_KEY=$fullchain_path
  sudo chown ${USER}:${USER} $CERT_PRIV_KEY $CERT_PUB_KEY
else
  if [[ "${ID_LIKE}" == *debian* ]]; then
    sudo apt install -y certbot
  elif [[ "${ID_LIKE}" == *rhel* ]]; then
    sudo $RHEL_PKG_MGR install -y certbot
  fi

  print_green 'Getting wildcard cert'

  sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --no-bootstrap --preferred-challenges dns -m ${letsemail} --no-eff-email
  while [[ $? -ne 0 ]]; do
    sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --no-bootstrap --preferred-challenges dns -m ${letsemail} --no-eff-email
  done
  CERT_PRIV_KEY=/etc/letsencrypt/live/${rootdomain}/privkey.pem
  CERT_PUB_KEY=/etc/letsencrypt/live/${rootdomain}/fullchain.pem
  sudo chown ${USER}:${USER} -R /etc/letsencrypt
fi

print_green 'Installing Nginx'

if [[ "${ID_LIKE}" == *debian* ]]; then
  sudo mkdir -p /etc/apt/keyrings
  wget -qO - https://nginx.org/keys/nginx_signing.key | sudo gpg --dearmor -o /etc/apt/keyrings/nginx-archive-keyring.gpg

  nginxrepo="$(
    cat <<EOF
deb [signed-by=/etc/apt/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/$osname $codename nginx
EOF
  )"
  echo "${nginxrepo}" | sudo tee /etc/apt/sources.list.d/nginx.list >/dev/null

  sudo apt update
  sudo apt install -y nginx
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  nginxrepo="$(
    cat <<EOF
[nginx]
name=nginx repo
baseurl=http://nginx.org/packages/rhel/\$releasever/\$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
EOF
  )"
  echo "${nginxrepo}" | sudo tee /etc/yum.repos.d/nginx.repo >/dev/null
  sudo $RHEL_PKG_MGR makecache
  sudo $RHEL_PKG_MGR install -y nginx
fi

sudo systemctl stop nginx

if [[ "${ID_LIKE}" == *debian* ]]; then
  NGINX_USER="www-data"
  NGINX_GROUP="www-data"
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  NGINX_USER="nginx"
  NGINX_GROUP="nginx"
fi

nginxdefaultconf='/etc/nginx/nginx.conf'

nginxconf="$(
  cat <<EOF
worker_rlimit_nofile 1000000;
user ${NGINX_USER};
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
        worker_connections 4096;
}

http {
        sendfile on;
        tcp_nopush on;
        types_hash_max_size 2048;
        server_names_hash_bucket_size 256;
        include /etc/nginx/mime.types;
        default_type application/octet-stream;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;
        gzip on;
        include /etc/nginx/conf.d/*.conf;
        include /etc/nginx/sites-enabled/*;
}
EOF
)"
echo "${nginxconf}" | sudo tee $nginxdefaultconf >/dev/null

if [[ "${ID_LIKE}" == *debian* ]]; then
  for i in sites-available sites-enabled; do
    sudo mkdir -p /etc/nginx/$i
  done
fi

print_green 'Installing NodeJS'

NODE_MAJOR=20
if [[ "${ID_LIKE}" == *debian* ]]; then
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
  echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
  sudo apt update
  sudo apt install -y gcc g++ make
  sudo apt install -y nodejs
  sudo npm install -g npm
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  curl -fsSL https://rpm.nodesource.com/setup_$NODE_MAJOR.x | sudo -E bash - && sudo $RHEL_PKG_MGR install -y nodejs gcc-c++ make
  sudo npm install -g npm
fi

print_green "Installing Python ${PYTHON_VER}"

if [[ "${ID_LIKE}" == *debian* ]]; then
  sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev
  numprocs=$(nproc)
  cd ~
  wget https://www.python.org/ftp/python/${PYTHON_VER}/Python-${PYTHON_VER}.tgz
  tar -xf Python-${PYTHON_VER}.tgz
  cd Python-${PYTHON_VER}
  ./configure --enable-optimizations
  make -j $numprocs
  sudo make altinstall
  cd ~
  sudo rm -rf Python-${PYTHON_VER} Python-${PYTHON_VER}.tgz
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  REQUIRED_PACKAGES=("ncurses" "ncurses-devel" "ncurses-libs" "readline" "readline-devel" "sqlite" "sqlite-devel" "libsqlite3x" "libsqlite3x-devel")
  for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! sudo $RHEL_PKG_MGR list installed "${pkg}" >/dev/null 2>&1; then
      sudo $RHEL_PKG_MGR install -y "${pkg}"
    fi
  done

  curl https://pyenv.run | bash

  if ! grep -Fxq 'export PYENV_ROOT="$HOME/.pyenv"' ~/.bashrc; then
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >>~/.bashrc
  fi
  if ! grep -Fxq 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' ~/.bashrc; then
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >>~/.bashrc
  fi
  # https://github.com/pyenv/pyenv/issues/264
  if [ "$BASH_ENV" != "$HOME/.bashrc" ]; then
    if ! grep -Fxq 'eval "$(pyenv init -)"' ~/.bashrc; then
      echo 'eval "$(pyenv init -)"' >>~/.bashrc
    fi
  else
    if ! grep -Fxq 'eval "$(pyenv init -)"' ~/.bash_profile; then
      echo 'eval "$(pyenv init -)"' >>~/.bash_profile
    fi
  fi

  export PYENV_ROOT="$HOME/.pyenv"
  command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init -)"

  pyenv install ${PYTHON_VER}
  pyenv global ${PYTHON_VER}
fi

print_green 'Installing redis and git'
if [[ "${ID_LIKE}" == *debian* ]]; then
  sudo apt install -y redis git
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  sudo $RHEL_PKG_MGR install -y redis git
fi
sudo systemctl enable --now redis

print_green 'Installing postgresql'

if [[ "${ID_LIKE}" == *debian* ]]; then
  POSTGRESQL_SERVICE="postgresql"

  postgresql_repo="deb [arch=${pgarch} signed-by=/etc/apt/keyrings/postgresql-archive-keyring.gpg] https://apt.postgresql.org/pub/repos/apt/ $codename-pgdg main"
  echo "$postgresql_repo" | sudo tee /etc/apt/sources.list.d/pgdg.list

  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/postgresql-archive-keyring.gpg
  sudo apt update
  sudo apt install -y postgresql-15
  sleep 2
  sudo systemctl enable --now $POSTGRESQL_SERVICE

  until pg_isready >/dev/null; do
    echo -ne "${GREEN}Waiting for PostgreSQL to be ready${NC}\n"
    sleep 3
  done
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  POSTGRESQL_SERVICE="postgresql-15"

  sudo $RHEL_PKG_MGR install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-${relno}-$(uname -m)/pgdg-redhat-repo-latest.noarch.rpm
  sudo $RHEL_PKG_MGR install -y postgresql15-server postgresql15
  sudo /usr/pgsql-15/bin/postgresql-15-setup initdb
  sudo systemctl enable --now $POSTGRESQL_SERVICE

  until /usr/pgsql-15/bin/pg_isready -h localhost -p 5432 >/dev/null; do
    echo -ne "${GREEN}Waiting for PostgreSQL to be ready${NC}\n"
    sleep 3
  done
fi

print_green 'Creating database for trmm'

sudo -iu postgres psql -c "CREATE DATABASE tacticalrmm"
sudo -iu postgres psql -c "CREATE USER ${pgusername} WITH PASSWORD '${pgpw}'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET client_encoding TO 'utf8'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET default_transaction_isolation TO 'read committed'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET timezone TO 'UTC'"
sudo -iu postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tacticalrmm TO ${pgusername}"
sudo -iu postgres psql -c "ALTER DATABASE tacticalrmm OWNER TO ${pgusername}"
sudo -iu postgres psql -c "GRANT USAGE, CREATE ON SCHEMA PUBLIC TO ${pgusername}"

print_green 'Creating database for meshcentral'

sudo -iu postgres psql -c "CREATE DATABASE meshcentral"
sudo -iu postgres psql -c "CREATE USER ${MESHPGUSER} WITH PASSWORD '${MESHPGPWD}'"
sudo -iu postgres psql -c "ALTER ROLE ${MESHPGUSER} SET client_encoding TO 'utf8'"
sudo -iu postgres psql -c "ALTER ROLE ${MESHPGUSER} SET default_transaction_isolation TO 'read committed'"
sudo -iu postgres psql -c "ALTER ROLE ${MESHPGUSER} SET timezone TO 'UTC'"
sudo -iu postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE meshcentral TO ${MESHPGUSER}"
sudo -iu postgres psql -c "ALTER DATABASE meshcentral OWNER TO ${MESHPGUSER}"
sudo -iu postgres psql -c "GRANT USAGE, CREATE ON SCHEMA PUBLIC TO ${MESHPGUSER}"

print_green 'Cloning repos'

sudo mkdir /rmm
sudo chown ${USER}:${USER} /rmm
sudo mkdir -p /var/log/celery
sudo chown ${USER}:${USER} /var/log/celery
git clone https://github.com/amidaware/tacticalrmm.git /rmm/
cd /rmm
git config user.email "admin@example.com"
git config user.name "Bob"
git checkout master

sudo mkdir -p ${SCRIPTS_DIR}
sudo chown ${USER}:${USER} ${SCRIPTS_DIR}
git clone https://github.com/amidaware/community-scripts.git ${SCRIPTS_DIR}/
cd ${SCRIPTS_DIR}
git config user.email "admin@example.com"
git config user.name "Bob"
git checkout main

print_green 'Downloading NATS'

if [ "$arch" = "x86_64" ]; then
  natsarch='amd64'
else
  natsarch='arm64'
fi

NATS_SERVER_VER=$(grep "^NATS_SERVER_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
nats_tmp=$(mktemp -d -t nats-XXXXXXXXXX)
wget https://github.com/nats-io/nats-server/releases/download/v${NATS_SERVER_VER}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}.tar.gz -P ${nats_tmp}
tar -xzf ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}.tar.gz -C ${nats_tmp}
sudo mv ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}/nats-server /usr/local/bin/
sudo chmod +x /usr/local/bin/nats-server
sudo chown ${USER}:${USER} /usr/local/bin/nats-server
rm -rf ${nats_tmp}

print_green 'Installing MeshCentral'

MESH_VER=$(grep "^MESH_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

sudo mkdir -p /meshcentral/meshcentral-data
sudo chown ${USER}:${USER} -R /meshcentral
cd /meshcentral
sudo chown ${USER}:${USER} -R /meshcentral

mesh_pkg="$(
  cat <<EOF
{
  "dependencies": {
    "archiver": "7.0.1",
    "meshcentral": "${MESH_VER}",
    "otplib": "10.2.3",
    "pg": "8.7.1",
    "pgtools": "0.3.2"
  }
}
EOF
)"
echo "${mesh_pkg}" >/meshcentral/package.json

meshcfg="$(
  cat <<EOF
{
  "settings": {
    "cert": "${meshdomain}",
    "WANonly": true,
    "minify": 1,
    "port": 4430,
    "aliasPort": 443,
    "redirPort": 800,
    "allowLoginToken": true,
    "allowFraming": true,
    "agentPing": 35,
    "allowHighQualityDesktop": true,
    "tlsOffload": "127.0.0.1",
    "agentCoreDump": false,
    "compression": true,
    "wsCompression": true,
    "agentWsCompression": true,
    "maxInvalidLogin": { "time": 5, "count": 5, "coolofftime": 30 },
    "postgres": {
      "user": "${MESHPGUSER}",
      "password": "${MESHPGPWD}",
      "port": "5432",
      "host": "localhost"
    }
  },
  "domains": {
    "": {
      "title": "Tactical RMM",
      "title2": "Tactical RMM",
      "newAccounts": false,
      "certUrl": "https://${meshdomain}:443/",
      "geoLocation": true,
      "cookieIpCheck": false,
      "mstsc": true
    }
  }
}
EOF
)"
echo "${meshcfg}" >/meshcentral/meshcentral-data/config.json

npm install

localvars="$(
  cat <<EOF
SECRET_KEY = "${DJANGO_SEKRET}"

DEBUG = False

ALLOWED_HOSTS = ['${rmmdomain}']

ADMIN_URL = "${ADMINURL}/"

CORS_ORIGIN_WHITELIST = [
    "https://${frontenddomain}"
]

CORS_ALLOW_HEADERS = [
    'authorization',
    'content-type',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tacticalrmm',
        'USER': '${pgusername}',
        'PASSWORD': '${pgpw}',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

MESH_USERNAME = "${meshusername}"
MESH_SITE = "https://${meshdomain}"
ADMIN_ENABLED = True
EOF
)"
echo "${localvars}" >$local_settings

if [[ "$insecure" = true ]]; then
  echo "TRMM_INSECURE = True" | tee --append $local_settings >/dev/null
fi

if [[ "$byocert" = true ]]; then
  owncerts="$(
    cat <<EOF
CERT_FILE = "${CERT_PUB_KEY}"
KEY_FILE = "${CERT_PRIV_KEY}"
EOF
  )"
  echo "${owncerts}" | tee --append $local_settings >/dev/null
fi

if [ "$arch" = "x86_64" ]; then
  natsapi='nats-api'
else
  natsapi='nats-api-arm64'
fi

sudo cp /rmm/natsapi/bin/${natsapi} /usr/local/bin/nats-api
sudo chown ${USER}:${USER} /usr/local/bin/nats-api
sudo chmod +x /usr/local/bin/nats-api

print_green 'Installing the backend'

if [[ "${ID_LIKE}" == *debian* ]]; then
  # for weasyprint
  if [[ "$osname" == "debian" ]]; then
    count=$(dpkg -l | grep -E "libpango-1.0-0|libpangoft2-1.0-0" | wc -l)
    if ! [ "$count" -eq 2 ]; then
      sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0
    fi
  elif [[ "$osname" == "ubuntu" ]]; then
    count=$(dpkg -l | grep -E "libpango-1.0-0|libharfbuzz0b|libpangoft2-1.0-0" | wc -l)
    if ! [ "$count" -eq 3 ]; then
      sudo apt install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
    fi
  fi
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  REQUIRED_PACKAGES=("pango" "pango-devel" "cairo" "cairo-devel" "libffi-devel")
  for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! sudo $RHEL_PKG_MGR list installed "${pkg}" >/dev/null 2>&1; then
      sudo $RHEL_PKG_MGR install -y "${pkg}"
    fi
  done
fi

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

sudo mkdir -p /opt/tactical/reporting/assets
sudo mkdir -p /opt/tactical/reporting/schemas
sudo chown -R ${USER}:${USER} /opt/tactical

cd /rmm/api
python3.11 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools==${SETUPTOOLS_VER} wheel==${WHEEL_VER}
pip install --no-cache-dir -r /rmm/api/tacticalrmm/requirements.txt
python3.11 manage.py migrate
python3.11 manage.py generate_json_schemas
python3.11 manage.py collectstatic --no-input
python3.11 manage.py create_natsapi_conf
python3.11 manage.py create_uwsgi_conf
python3.11 manage.py load_chocos
python3.11 manage.py load_community_scripts
WEB_VERSION=$(python3.11 manage.py get_config webversion)
WEBTAR_URL=$(python3.11 manage.py get_webtar_url)
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
printf >&2 "${YELLOW}Please create your login for the RMM website${NC}\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
echo -ne "Username: "
read djangousername
python3.11 manage.py createsuperuser --username ${djangousername} --email ${letsemail}
python3.11 manage.py create_installer_user
RANDBASE=$(python3.11 manage.py generate_totp)
cls
python3.11 manage.py generate_barcode ${RANDBASE} ${djangousername} ${frontenddomain}
deactivate
read -n 1 -s -r -p "Press any key to continue..."

rmmservice="$(
  cat <<EOF
[Unit]
Description=tacticalrmm uwsgi daemon
After=network.target ${POSTGRESQL_SERVICE}.service

[Service]
User=${USER}
Group=${NGINX_GROUP}
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PYENV_ROOT=%h/.pyenv"
Environment="PATH=%h/.pyenv/shims:%h/.pyenv/bin:/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/rmm/api/env/bin/uwsgi --ini app.ini
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${rmmservice}" | sudo tee /etc/systemd/system/rmm.service >/dev/null

uviservice="$(
  cat <<EOF
[Unit]
Description=uvicorn daemon v1
After=network.target

[Service]
User=${USER}
Group=${NGINX_GROUP}
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PYENV_ROOT=%h/.pyenv"
Environment="PATH=%h/.pyenv/shims:%h/.pyenv/bin:/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/rmm/api/env/bin/uvicorn --uds /rmm/daphne.sock --forwarded-allow-ips='*' tacticalrmm.asgi:application
ExecStartPre=rm -f /rmm/daphne.sock
ExecStartPre=rm -f /rmm/daphne.sock.lock
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${uviservice}" | sudo tee /etc/systemd/system/daphne.service >/dev/null

natsservice="$(
  cat <<EOF
[Unit]
Description=NATS Server
After=network.target

[Service]
PrivateTmp=true
Type=simple
ExecStart=/usr/local/bin/nats-server -c /rmm/api/tacticalrmm/nats-rmm.conf
ExecReload=/usr/bin/kill -s HUP \$MAINPID
ExecStop=/usr/bin/kill -s SIGINT \$MAINPID
User=${USER}
Group=${USER}
Restart=always
RestartSec=5s
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsservice}" | sudo tee /etc/systemd/system/nats.service >/dev/null

natsapi="$(
  cat <<EOF
[Unit]
Description=TacticalRMM Nats Api v1
After=nats.service

[Service]
Type=simple
ExecStart=/usr/local/bin/nats-api
User=${USER}
Group=${USER}
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsapi}" | sudo tee /etc/systemd/system/nats-api.service >/dev/null

nginxrmm="$(
  cat <<EOF
server_tokens off;

upstream tacticalrmm {
    server unix:////rmm/api/tacticalrmm/tacticalrmm.sock;
}

map \$http_user_agent \$ignore_ua {
    "~python-requests.*" 0;
    "~go-resty.*" 0;
    default 1;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${rmmdomain};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl reuseport;
    listen [::]:443 ssl;
    server_name ${rmmdomain};
    client_max_body_size 300M;
    access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log combined if=\$ignore_ua;
    error_log /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log;
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
        root /rmm/api/tacticalrmm;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /rmm/api/tacticalrmm/tacticalrmm/private/;
    }

    location /assets/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /opt/tactical/reporting/assets/;
    }

    location ~ ^/ws/ {
        proxy_pass http://unix:/rmm/daphne.sock;

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
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 300s;
        uwsgi_ignore_client_abort on;
    }
}
EOF
)"
if [[ "${ID_LIKE}" == *debian* ]]; then
  echo "${nginxrmm}" | sudo tee /etc/nginx/sites-available/rmm.conf >/dev/null
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  echo "${nginxrmm}" | sudo tee /etc/nginx/conf.d/rmm.conf >/dev/null
fi

nginxmesh="$(
  cat <<EOF
server {
  listen 80;
  listen [::]:80;
  server_name ${meshdomain};
  return 301 https://\$server_name\$request_uri;
}

server {

    listen 443 ssl;
    listen [::]:443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${meshdomain};
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
if [[ "${ID_LIKE}" == *debian* ]]; then
  echo "${nginxmesh}" | sudo tee /etc/nginx/sites-available/meshcentral.conf >/dev/null
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  echo "${nginxmesh}" | sudo tee /etc/nginx/conf.d/meshcentral.conf >/dev/null
fi

if [[ "${ID_LIKE}" == *debian* ]]; then
  sudo ln -s /etc/nginx/sites-available/rmm.conf /etc/nginx/sites-enabled/rmm.conf
  sudo ln -s /etc/nginx/sites-available/meshcentral.conf /etc/nginx/sites-enabled/meshcentral.conf
fi

sudo mkdir /etc/conf.d

celeryservice="$(
  cat <<EOF
[Unit]
Description=Celery Service V2
After=network.target redis-server.service ${POSTGRESQL_SERVICE}.service

[Service]
Type=forking
User=${USER}
Group=${USER}
Environment="PYENV_ROOT=%h/.pyenv"
Environment="PATH=%h/.pyenv/shims:%h/.pyenv/bin"
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi start \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --loglevel="\${CELERYD_LOG_LEVEL}"'
ExecReload=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi restart \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celeryservice}" | sudo tee /etc/systemd/system/celery.service >/dev/null

celeryconf="$(
  cat <<EOF
CELERYD_NODES="w1"

CELERY_BIN="/rmm/api/env/bin/celery"

CELERY_APP="tacticalrmm"

CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=86400 --autoscale=20,2"

CELERYD_PID_FILE="/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="ERROR"

CELERYBEAT_PID_FILE="/rmm/api/tacticalrmm/beat.pid"
CELERYBEAT_LOG_FILE="/var/log/celery/beat.log"
EOF
)"
echo "${celeryconf}" | sudo tee /etc/conf.d/celery.conf >/dev/null

celerybeatservice="$(
  cat <<EOF
[Unit]
Description=Celery Beat Service V3
After=network.target redis-server.service ${POSTGRESQL_SERVICE}.service

[Service]
Type=simple
User=${USER}
Group=${USER}
Environment="PYENV_ROOT=%h/.pyenv"
Environment="PATH=%h/.pyenv/shims:%h/.pyenv/bin"
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \${CELERY_APP} beat --pidfile=\${CELERYBEAT_PID_FILE} --logfile=\${CELERYBEAT_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL}'
ExecStartPre=rm -f /rmm/api/tacticalrmm/beat.pid
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerybeatservice}" | sudo tee /etc/systemd/system/celerybeat.service >/dev/null

sudo chown ${USER}:${USER} -R /etc/conf.d/

meshservice="$(
  cat <<EOF
[Unit]
Description=MeshCentral Server
After=network.target ${POSTGRESQL_SERVICE}.service nginx.service
[Service]
Type=simple
LimitNOFILE=1000000
ExecStart=/usr/bin/node node_modules/meshcentral
Environment=NODE_ENV=production
WorkingDirectory=/meshcentral
User=${USER}
Group=${USER}
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${meshservice}" | sudo tee /etc/systemd/system/meshcentral.service >/dev/null

sudo systemctl daemon-reload

if [ -d ~/.npm ]; then
  sudo chown -R $USER:$GROUP ~/.npm
fi

if [ -d ~/.config ]; then
  sudo chown -R $USER:$GROUP ~/.config
fi

print_green 'Installing the frontend'

webtar="trmm-web-v${WEB_VERSION}.tar.gz"
wget -q ${WEBTAR_URL} -O /tmp/${webtar}
sudo mkdir -p /var/www/rmm
sudo tar -xzf /tmp/${webtar} -C /var/www/rmm
echo "window._env_ = {PROD_URL: \"https://${rmmdomain}\"}" | sudo tee /var/www/rmm/dist/env-config.js >/dev/null
sudo chown $NGINX_USER:$NGINX_GROUP -R /var/www/rmm/dist
rm -f /tmp/${webtar}

nginxfrontend="$(
  cat <<EOF
server {
    server_name ${frontenddomain};
    charset utf-8;
    location / {
        root /var/www/rmm/dist;
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
    if (\$host = ${frontenddomain}) {
        return 301 https://\$host\$request_uri;
    }

    listen 80;
    listen [::]:80;
    server_name ${frontenddomain};
    return 404;
}
EOF
)"
if [[ "${ID_LIKE}" == *debian* ]]; then
  echo "${nginxfrontend}" | sudo tee /etc/nginx/sites-available/frontend.conf >/dev/null
elif [[ "${ID_LIKE}" == *rhel* ]]; then
  echo "${nginxfrontend}" | sudo tee /etc/nginx/conf.d/frontend.conf >/dev/null
fi

if [[ "${ID_LIKE}" == *debian* ]]; then
  sudo ln -s /etc/nginx/sites-available/frontend.conf /etc/nginx/sites-enabled/frontend.conf
fi

print_green 'Enabling Services'

for i in rmm.service daphne.service celery.service celerybeat.service nginx; do
  sudo systemctl enable ${i}
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done
sleep 5
sudo systemctl enable meshcentral

print_green 'Starting meshcentral and waiting for it to be ready'

sudo systemctl restart meshcentral

sleep 3

# The first time we start meshcentral, it will need some time to generate certs and install plugins.
# This will take anywhere from a few seconds to a few minutes depending on the server's hardware
# We will know it's ready once the last line of the systemd service stdout is 'MeshCentral HTTP server running on port.....'
while ! [[ $CHECK_MESH_READY ]]; do
  CHECK_MESH_READY=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
  sleep 5
done

print_green 'Generating meshcentral login token key'

MESHTOKENKEY=$(node /meshcentral/node_modules/meshcentral --logintokenkey)

meshtoken="$(
  cat <<EOF
MESH_TOKEN_KEY = "${MESHTOKENKEY}"
EOF
)"
echo "${meshtoken}" | tee --append $local_settings >/dev/null

print_green 'Creating meshcentral account and group'

sudo systemctl stop meshcentral
sleep 1
cd /meshcentral

node node_modules/meshcentral --createaccount ${meshusername} --pass ${MESHPASSWD} --email ${letsemail}
sleep 1
node node_modules/meshcentral --adminaccount ${meshusername}

sudo systemctl start meshcentral
sleep 5

while ! [[ $CHECK_MESH_READY2 ]]; do
  CHECK_MESH_READY2=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
  sleep 5
done

node node_modules/meshcentral/meshctrl.js --url wss://${meshdomain}:443 --loginuser ${meshusername} --loginpass ${MESHPASSWD} AddDeviceGroup --name TacticalRMM
sleep 1

sudo systemctl enable nats.service
cd /rmm/api/tacticalrmm
source /rmm/api/env/bin/activate
python3.11 manage.py initial_db_setup
python3.11 manage.py reload_nats
python3.11 manage.py sync_mesh_with_trmm
deactivate
sudo systemctl start nats.service

sleep 1
sudo systemctl enable nats-api.service
sudo systemctl start nats-api.service

## disable django admin
sed -i 's/ADMIN_ENABLED = True/ADMIN_ENABLED = False/g' $local_settings

sudo chmod 755 /rmm/api/tacticalrmm
sudo chmod 755 /rmm/api
sudo chmod 755 /rmm

print_green 'Restarting services'
for i in rmm.service daphne.service celery.service celerybeat.service; do
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n\n"
printf >&2 "${YELLOW}Installation complete!${NC}\n\n"
printf >&2 "${YELLOW}Access your rmm at: ${GREEN}https://${frontenddomain}${NC}\n\n"
printf >&2 "${YELLOW}MeshCentral username: ${GREEN}${meshusername}${NC}\n"
printf >&2 "${YELLOW}MeshCentral password: ${GREEN}${MESHPASSWD}${NC}\n\n"

if [ "$BEHIND_NAT" = true ]; then
  echo -ne "${YELLOW}Read below if your router does NOT support Hairpin NAT${NC}\n\n"
  echo -ne "${GREEN}If you will be accessing the web interface of the RMM from the same LAN as this server,${NC}\n"
  echo -ne "${GREEN}you'll need to make sure your 3 subdomains resolve to ${IPV4}${NC}\n"
  echo -ne "${GREEN}This also applies to any agents that will be on the same local network as the rmm.${NC}\n"
  echo -ne "${GREEN}You'll also need to setup port forwarding in your router on port 443${NC}\n\n"
fi

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
