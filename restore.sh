#!/usr/bin/env bash

SCRIPT_VERSION="61"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/restore.sh'

sudo apt update
sudo apt install -y curl wget dirmngr gnupg lsb-release ca-certificates

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.11.8'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'
local_settings='/rmm/api/tacticalrmm/tacticalrmm/local_settings.py'

TMP_FILE=$(mktemp -p "" "rmmrestore_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" >${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" -ne "${NEW_VER}" ]; then
  printf >&2 "${YELLOW}A newer version of this restore script is available.${NC}\n"
  printf >&2 "${YELLOW}Please download the latest version from ${GREEN}${SCRIPT_URL}${YELLOW} and re-run.${NC}\n"
  rm -f $TMP_FILE
  exit 1
fi

rm -f $TMP_FILE

export DEBIAN_FRONTEND=noninteractive

if [ -d /rmm/api/tacticalrmm ]; then
  echo -ne "${RED}ERROR: Existing trmm installation found. The restore script must be run on a clean server, please re-read the docs.${NC}\n"
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
  echo -ne "${RED}ERROR: Only Debian 11, Debian 12 and Ubuntu 22.04 are supported.${NC}\n"
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
else
  not_supported
  exit 1
fi

if dpkg -l | grep -qi turnkey; then
  echo -ne "${RED}Turnkey linux is not supported. Please use the official debian/ubuntu ISO.${NC}\n"
  exit 1
fi

if ps aux | grep -v grep | grep -qi webmin; then
  echo -ne "${RED}Webmin running, should not be installed. Please use the official debian/ubuntu ISO.${NC}\n"
  exit 1
fi

if [ $EUID -eq 0 ]; then
  echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
  exit 1
fi

if [[ "$LANG" != *".UTF-8" ]]; then
  printf >&2 "\n${RED}System locale must be ${GREEN}<some language>.UTF-8${RED} not ${YELLOW}${LANG}${NC}\n"
  printf >&2 "${RED}Run the following command and change the default locale to your language of choice${NC}\n\n"
  printf >&2 "${GREEN}sudo dpkg-reconfigure locales${NC}\n\n"
  printf >&2 "${RED}You will need to log out and back in for changes to take effect, then re-run this script.${NC}\n\n"
  exit 1
fi

if [ "$arch" = "x86_64" ]; then
  pgarch='amd64'
else
  pgarch='arm64'
fi
postgresql_repo="deb [arch=${pgarch} signed-by=/etc/apt/keyrings/postgresql-archive-keyring.gpg] https://apt.postgresql.org/pub/repos/apt/ $codename-pgdg main"

if [ ! -f "${1}" ]; then
  echo -ne "\n${RED}usage: ./restore.sh rmm-backup-xxxx.tar${NC}\n"
  exit 1
fi

print_green() {
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
  printf >&2 "${GREEN}${1}${NC}\n"
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
}

print_green 'Unpacking backup'
tmp_dir=$(mktemp -d -t tacticalrmm-XXXXXXXXXXXXXXXXXXXXX)

tar -xf ${1} -C $tmp_dir

strip="User="
ORIGUSER=$(grep ${strip} $tmp_dir/systemd/rmm.service | sed -e "s/^${strip}//")

if [ "$ORIGUSER" != "$USER" ]; then
  printf >&2 "${RED}ERROR: You must run this restore script from the same user account used on your old server: ${GREEN}${ORIGUSER}${NC}\n"
  rm -rf $tmp_dir
  exit 1
fi

# prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service

sudo apt update

print_green 'Installing NodeJS'

sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
NODE_MAJOR=20
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt update
sudo apt install -y gcc g++ make
sudo apt install -y nodejs
sudo npm install -g npm

print_green 'Restoring Nginx'

wget -qO - https://nginx.org/keys/nginx_signing.key | sudo gpg --dearmor -o /etc/apt/keyrings/nginx-archive-keyring.gpg

nginxrepo="$(
  cat <<EOF
deb [signed-by=/etc/apt/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/$osname $codename nginx
EOF
)"
echo "${nginxrepo}" | sudo tee /etc/apt/sources.list.d/nginx.list >/dev/null

sudo apt update
sudo apt install -y nginx
sudo systemctl stop nginx

nginxdefaultconf='/etc/nginx/nginx.conf'

nginxconf="$(
  cat <<EOF
worker_rlimit_nofile 1000000;
user www-data;
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

for i in sites-available sites-enabled; do
  sudo mkdir -p /etc/nginx/$i
done

print_green 'Restoring certbot'

sudo apt install -y software-properties-common
sudo apt install -y certbot openssl

print_green 'Restoring certs'

if [ -f "$tmp_dir/certs/etc-letsencrypt.tar.gz" ]; then
  sudo rm -rf /etc/letsencrypt
  sudo mkdir /etc/letsencrypt
  sudo tar -xzf $tmp_dir/certs/etc-letsencrypt.tar.gz -C /etc/letsencrypt
  sudo chown ${USER}:${USER} -R /etc/letsencrypt
fi

if [ -d "${tmp_dir}/certs/custom" ]; then
  CERT_FILE=$(grep "^CERT_FILE" "$tmp_dir/rmm/local_settings.py" | awk -F'[= "]' '{print $5}')
  KEY_FILE=$(grep "^KEY_FILE" "$tmp_dir/rmm/local_settings.py" | awk -F'[= "]' '{print $5}')

  sudo mkdir -p $(dirname $CERT_FILE) $(dirname $KEY_FILE)
  sudo chown ${USER}:${USER} $(dirname $CERT_FILE) $(dirname $KEY_FILE)

  cp -p ${tmp_dir}/certs/custom/cert $CERT_FILE
  cp -p ${tmp_dir}/certs/custom/key $KEY_FILE
elif [ -d "${tmp_dir}/certs/selfsigned" ]; then
  certdir='/etc/ssl/tactical'
  sudo mkdir -p $certdir
  sudo chown ${USER}:${USER} $certdir
  sudo chmod 770 $certdir
  cp -p ${tmp_dir}/certs/selfsigned/key.pem $certdir
  cp -p ${tmp_dir}/certs/selfsigned/cert.pem $certdir
fi

print_green 'Restoring assets'
if [ -f "$tmp_dir/opt/opt-tactical.tar.gz" ]; then
  sudo mkdir -p /opt/tactical
  sudo tar -xzf $tmp_dir/opt/opt-tactical.tar.gz -C /opt/tactical
  sudo chown ${USER}:${USER} -R /opt/tactical
else
  sudo mkdir -p /opt/tactical/reporting/assets
  sudo mkdir -p /opt/tactical/reporting/schemas
  sudo chown -R ${USER}:${USER} /opt/tactical
fi

print_green 'Restoring celery configs'

sudo mkdir /etc/conf.d
sudo tar -xzf $tmp_dir/confd/etc-confd.tar.gz -C /etc/conf.d
sudo chown ${USER}:${USER} -R /etc/conf.d

print_green 'Restoring systemd services'

sudo cp $tmp_dir/systemd/* /etc/systemd/system/

# migrate daphne to uvicorn for older systems
if ! grep -q uvicorn /etc/systemd/system/daphne.service; then
  sudo rm -f /etc/systemd/system/daphne.service

  uviservice="$(
    cat <<EOF
[Unit]
Description=uvicorn daemon v1
After=network.target

[Service]
User=${USER}
Group=www-data
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PATH=/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
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
fi

sudo systemctl daemon-reload

print_green "Installing Python ${PYTHON_VER}"

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

print_green 'Installing redis and git'
sudo apt install -y redis git

print_green 'Installing postgresql'

echo "$postgresql_repo" | sudo tee /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/postgresql-archive-keyring.gpg
sudo apt update
sudo apt install -y postgresql-15
sleep 2
sudo systemctl enable --now postgresql

until pg_isready >/dev/null; do
  echo -ne "${GREEN}Waiting for PostgreSQL to be ready${NC}\n"
  sleep 3
done

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

print_green 'Restoring NATS'

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

print_green 'Restoring MeshCentral'

sudo apt install -y jq

MESH_VER=$(grep "^MESH_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
sudo tar -xzf $tmp_dir/meshcentral/mesh.tar.gz -C /
sudo chown ${USER}:${USER} -R /meshcentral
rm -f /meshcentral/package.json /meshcentral/package-lock.json

FROM_MONGO=false
if grep -q postgres "/meshcentral/meshcentral-data/config.json"; then
  MESH_POSTGRES_USER=$(jq '.settings.postgres.user' /meshcentral/meshcentral-data/config.json -r)
  MESH_POSTGRES_PW=$(jq '.settings.postgres.password' /meshcentral/meshcentral-data/config.json -r)
else
  FROM_MONGO=true
  MESH_POSTGRES_USER=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
  MESH_POSTGRES_PW=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)
fi

print_green 'Creating MeshCentral DB'

sudo -iu postgres psql -c "CREATE DATABASE meshcentral"
sudo -iu postgres psql -c "CREATE USER ${MESH_POSTGRES_USER} WITH PASSWORD '${MESH_POSTGRES_PW}'"
sudo -iu postgres psql -c "ALTER ROLE ${MESH_POSTGRES_USER} SET client_encoding TO 'utf8'"
sudo -iu postgres psql -c "ALTER ROLE ${MESH_POSTGRES_USER} SET default_transaction_isolation TO 'read committed'"
sudo -iu postgres psql -c "ALTER ROLE ${MESH_POSTGRES_USER} SET timezone TO 'UTC'"
sudo -iu postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE meshcentral TO ${MESH_POSTGRES_USER}"
sudo -iu postgres psql -c "ALTER DATABASE meshcentral OWNER TO ${MESH_POSTGRES_USER}"
sudo -iu postgres psql -c "GRANT USAGE, CREATE ON SCHEMA PUBLIC TO ${MESH_POSTGRES_USER}"

if [ "$FROM_MONGO" = true ]; then
  print_green 'Converting mesh mongo to postgres'

  # https://github.com/amidaware/trmm-awesome/blob/main/scripts/migrate-mesh-to-postgres.sh
  mesh_data='/meshcentral/meshcentral-data'
  if [[ ! -f "${mesh_data}/meshcentral.db.json" ]]; then
    echo -ne "${RED}ERROR: meshcentral.db.json was not found${NC}\n"
    echo -ne "${RED}Unable to convert mongo to postgres${NC}\n"
    echo -ne "${RED}You probably didn't download the lastest backup.sh file before doing a backup and were using an outdated version${NC}\n"
    echo -ne "${RED}You will need to download the latest backup script, run a fresh backup on your old server, wipe this server and attempt a fresh restore.${NC}\n"
    exit 1
  fi
  MESH_PG_PORT='5432'
  MESH_PG_HOST='localhost'
  cp ${mesh_data}/config.json ${mesh_data}/config-mongodb-$(date "+%Y%m%dT%H%M%S").bak

  cat ${mesh_data}/config.json |
    jq '.settings |= with_entries(select((.key | ascii_downcase) as $key | $key != "mongodb" and $key != "mongodbname"))' |
    jq " .settings.postgres.user |= \"${MESH_POSTGRES_USER}\" " |
    jq " .settings.postgres.password |= \"${MESH_POSTGRES_PW}\" " |
    jq " .settings.postgres.port |= \"${MESH_PG_PORT}\" " |
    jq " .settings.postgres.host |= \"${MESH_PG_HOST}\" " >${mesh_data}/config-postgres.json

  mv ${mesh_data}/config-postgres.json ${mesh_data}/config.json
else
  gzip -d $tmp_dir/postgres/mesh-db*.psql.gz
  PGPASSWORD=${MESH_POSTGRES_PW} psql -h localhost -U ${MESH_POSTGRES_USER} -d meshcentral -f $tmp_dir/postgres/mesh-db*.psql
fi

cd /meshcentral
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
npm install

if [ "$FROM_MONGO" = true ]; then
  node node_modules/meshcentral --dbimport >/dev/null
fi

print_green 'Restoring the backend'

cp $tmp_dir/rmm/local_settings.py /rmm/api/tacticalrmm/tacticalrmm/

if [ "$arch" = "x86_64" ]; then
  natsapi='nats-api'
else
  natsapi='nats-api-arm64'
fi

sudo cp /rmm/natsapi/bin/${natsapi} /usr/local/bin/nats-api
sudo chown ${USER}:${USER} /usr/local/bin/nats-api
sudo chmod +x /usr/local/bin/nats-api

print_green 'Restoring the trmm database'

pgusername=$(grep -w USER $local_settings | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')
pgpw=$(grep -w PASSWORD $local_settings | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')

sudo -iu postgres psql -c "CREATE DATABASE tacticalrmm"
sudo -iu postgres psql -c "CREATE USER ${pgusername} WITH PASSWORD '${pgpw}'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET client_encoding TO 'utf8'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET default_transaction_isolation TO 'read committed'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET timezone TO 'UTC'"
sudo -iu postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tacticalrmm TO ${pgusername}"
sudo -iu postgres psql -c "ALTER DATABASE tacticalrmm OWNER TO ${pgusername}"
sudo -iu postgres psql -c "GRANT USAGE, CREATE ON SCHEMA PUBLIC TO ${pgusername}"

gzip -d $tmp_dir/postgres/db*.psql.gz
PGPASSWORD=${pgpw} psql -h localhost -U ${pgusername} -d tacticalrmm -f $tmp_dir/postgres/db*.psql

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

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

cd /rmm/api
python3.11 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools==${SETUPTOOLS_VER} wheel==${WHEEL_VER}
pip install --no-cache-dir -r /rmm/api/tacticalrmm/requirements.txt
python manage.py migrate
python manage.py generate_json_schemas
python manage.py collectstatic --no-input
python manage.py create_natsapi_conf
python manage.py create_uwsgi_conf
python manage.py reload_nats
python manage.py post_update_tasks
echo "Running management commands...please wait..."
API=$(python manage.py get_config api)
WEB_VERSION=$(python manage.py get_config webversion)
FRONTEND=$(python manage.py get_config webdomain)
meshdomain=$(python manage.py get_config meshdomain)
WEBTAR_URL=$(python manage.py get_webtar_url)
CERT_PUB_KEY=$(python manage.py get_config certfile)
CERT_PRIV_KEY=$(python manage.py get_config keyfile)
deactivate

print_green 'Restoring hosts file'

if grep -q manage_etc_hosts /etc/hosts; then
  sudo sed -i '/manage_etc_hosts: true/d' /etc/cloud/cloud.cfg >/dev/null
  echo -e "\nmanage_etc_hosts: false" | sudo tee --append /etc/cloud/cloud.cfg >/dev/null
  sudo systemctl restart cloud-init >/dev/null
fi

print_green 'Restoring nginx configs'

for i in frontend meshcentral; do
  sudo cp ${tmp_dir}/nginx/${i}.conf /etc/nginx/sites-available/
  sudo ln -s /etc/nginx/sites-available/${i}.conf /etc/nginx/sites-enabled/${i}.conf
done

if ! grep -q "location /assets/" $tmp_dir/nginx/rmm.conf; then
  if [ -d "${tmp_dir}/certs/selfsigned" ]; then
    CERT_PUB_KEY="${certdir}/cert.pem"
    CERT_PRIV_KEY="${certdir}/key.pem"
  fi
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
    server_name ${API};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl reuseport;
    listen [::]:443 ssl;
    server_name ${API};
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
        add_header "Access-Control-Allow-Origin" "https://${FRONTEND}";
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${FRONTEND}";
        alias /rmm/api/tacticalrmm/tacticalrmm/private/;
    }

    location /assets/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${FRONTEND}";
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
  echo "${nginxrmm}" | sudo tee /etc/nginx/sites-available/rmm.conf >/dev/null
else
  sudo cp ${tmp_dir}/nginx/rmm.conf /etc/nginx/sites-available/
fi
sudo ln -s /etc/nginx/sites-available/rmm.conf /etc/nginx/sites-enabled/rmm.conf

HAS_11=$(grep 127.0.1.1 /etc/hosts)
if [[ $HAS_11 ]]; then
  sudo sed -i "/127.0.1.1/s/$/ ${API} ${FRONTEND} ${meshdomain}/" /etc/hosts
else
  echo "127.0.1.1 ${API} ${FRONTEND} ${meshdomain}" | sudo tee --append /etc/hosts >/dev/null
fi

sudo systemctl enable nats.service
sudo systemctl start nats.service

print_green 'Restoring the frontend'

webtar="trmm-web-v${WEB_VERSION}.tar.gz"
wget -q ${WEBTAR_URL} -O /tmp/${webtar}
sudo mkdir -p /var/www/rmm
sudo tar -xzf /tmp/${webtar} -C /var/www/rmm
echo "window._env_ = {PROD_URL: \"https://${API}\"}" | sudo tee /var/www/rmm/dist/env-config.js >/dev/null
sudo chown www-data:www-data -R /var/www/rmm/dist
rm -f /tmp/${webtar}

# reset perms
sudo chown ${USER}:${USER} -R /rmm
sudo chown ${USER}:${USER} /var/log/celery
sudo chown ${USER}:${USER} -R /etc/conf.d/
sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config
sudo chown -R $USER:$GROUP /home/${USER}/.cache

print_green 'Enabling and starting services'

HAS_OLD_MONGO_DEP=$(grep mongod /etc/systemd/system/meshcentral.service)
if [[ $HAS_OLD_MONGO_DEP ]]; then
  sudo sed -i 's/mongod.service/postgresql.service/g' /etc/systemd/system/meshcentral.service
fi

sudo systemctl daemon-reload

for i in celery.service celerybeat.service rmm.service daphne.service nats-api.service nginx; do
  sudo systemctl enable ${i}
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done
sleep 5

print_green 'Starting meshcentral'
sudo systemctl enable meshcentral
sudo systemctl start meshcentral

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n\n"
printf >&2 "${YELLOW}Restore complete!${NC}\n\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
