#!/usr/bin/env bash

SCRIPT_VERSION="154"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/update.sh'
LATEST_SETTINGS_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
THIS_SCRIPT=$(readlink -f "$0")

SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.11.8'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'
local_settings='/rmm/api/tacticalrmm/tacticalrmm/local_settings.py'

TMP_FILE=$(mktemp -p "" "rmmupdate_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" >${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" -ne "${NEW_VER}" ]; then
  printf >&2 "${YELLOW}Old update script detected, downloading and replacing with the latest version...${NC}\n"
  wget -q "${SCRIPT_URL}" -O update.sh
  exec ${THIS_SCRIPT}
fi

rm -f $TMP_FILE

export DEBIAN_FRONTEND=noninteractive

force=false
if [[ $* == *--force* ]]; then
  force=true
fi

if [ $EUID -eq 0 ]; then
  echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
  exit 1
fi

sudo apt update

strip="User="
ORIGUSER=$(grep ${strip} /etc/systemd/system/rmm.service | sed -e "s/^${strip}//")

if [ "$ORIGUSER" != "$USER" ]; then
  printf >&2 "${RED}ERROR: You must run this update script from the same user account used during install: ${GREEN}${ORIGUSER}${NC}\n"
  exit 1
fi

TMP_SETTINGS=$(mktemp -p "" "rmmsettings_XXXXXXXXXX")
curl -s -L "${LATEST_SETTINGS_URL}" >${TMP_SETTINGS}

LATEST_TRMM_VER=$(grep "^TRMM_VERSION" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
CURRENT_TRMM_VER=$(grep "^TRMM_VERSION" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

if [[ "${CURRENT_TRMM_VER}" == "${LATEST_TRMM_VER}" ]] && ! [[ "$force" = true ]]; then
  printf >&2 "${GREEN}Already on latest version. Current version: ${CURRENT_TRMM_VER} Latest version: ${LATEST_TRMM_VER}${NC}\n"
  rm -f $TMP_SETTINGS
  exit 0
fi

LATEST_MESH_VER=$(grep "^MESH_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
LATEST_PIP_VER=$(grep "^PIP_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
NATS_SERVER_VER=$(grep "^NATS_SERVER_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')

CURRENT_PIP_VER=$(grep "^PIP_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

cls() {
  printf "\033c"
}

if [ ! -d /etc/apt/keyrings ]; then
  sudo mkdir -p /etc/apt/keyrings
fi

CHECK_NATS_LIMITNOFILE=$(grep LimitNOFILE /etc/systemd/system/nats.service)
if ! [[ $CHECK_NATS_LIMITNOFILE ]]; then

  sudo rm -f /etc/systemd/system/nats.service

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
Group=www-data
Restart=always
RestartSec=5s
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
  )"
  echo "${natsservice}" | sudo tee /etc/systemd/system/nats.service >/dev/null
  sudo systemctl daemon-reload
fi

printf >&2 "${GREEN}Stopping celery and celerybeat services (this might take a while)...${NC}\n"
for i in celerybeat celery; do
  sudo systemctl stop ${i}
done

for i in nginx nats-api nats rmm daphne; do
  printf >&2 "${GREEN}Stopping ${i} service...${NC}\n"
  sudo systemctl stop ${i}
done

if ! grep -q V3 /etc/systemd/system/celerybeat.service; then
  sudo rm -f /etc/systemd/system/celerybeat.service

  celerybeatservice="$(
    cat <<EOF
[Unit]
Description=Celery Beat Service V3
After=network.target redis-server.service postgresql.service

[Service]
Type=simple
User=${USER}
Group=${USER}
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
  sudo systemctl daemon-reload
fi

# migrate daphne to uvicorn
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
  sudo systemctl daemon-reload
fi

osname=$(lsb_release -si)
osname=${osname^}
osname=$(echo "$osname" | tr '[A-Z]' '[a-z]')

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

if [ ! -f /etc/apt/sources.list.d/nginx.list ]; then
  codename=$(lsb_release -sc)
  nginxrepo="$(
    cat <<EOF
deb [signed-by=/etc/apt/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/$osname $codename nginx
EOF
  )"
  echo "${nginxrepo}" | sudo tee /etc/apt/sources.list.d/nginx.list >/dev/null
  wget -qO - https://nginx.org/keys/nginx_signing.key | sudo gpg --dearmor -o /etc/apt/keyrings/nginx-archive-keyring.gpg
  sudo apt update
  sudo apt install -y nginx
fi

if [ -f /etc/apt/keyrings/nginx-archive-keyring.gpg ]; then
  NGINX_KEY_EXPIRED=$(gpg --dry-run --quiet --no-keyring --import --import-options import-show /etc/apt/keyrings/nginx-archive-keyring.gpg | grep -B 1 573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62 | grep expired)
  if [[ $NGINX_KEY_EXPIRED ]]; then
    sudo rm -f /etc/apt/keyrings/nginx-archive-keyring.gpg
    wget -qO - https://nginx.org/keys/nginx_signing.key | sudo gpg --dearmor -o /etc/apt/keyrings/nginx-archive-keyring.gpg
    sudo apt update
  fi
fi

nginxdefaultconf='/etc/nginx/nginx.conf'
CHECK_NGINX_WORKER_CONN=$(grep "worker_connections 4096" $nginxdefaultconf)
if ! [[ $CHECK_NGINX_WORKER_CONN ]]; then
  printf >&2 "${GREEN}Changing nginx worker connections to 4096${NC}\n"
  sudo sed -i 's/worker_connections.*/worker_connections 4096;/g' $nginxdefaultconf
fi

CHECK_NGINX_NOLIMIT=$(grep "worker_rlimit_nofile 1000000" $nginxdefaultconf)
if ! [[ $CHECK_NGINX_NOLIMIT ]]; then
  sudo sed -i '/worker_rlimit_nofile.*/d' $nginxdefaultconf
  printf >&2 "${GREEN}Increasing nginx open file limit${NC}\n"
  sudo sed -i '1s/^/worker_rlimit_nofile 1000000;\
/' $nginxdefaultconf
fi

sudo sed -i 's/# server_names_hash_bucket_size.*/server_names_hash_bucket_size 256;/g' $nginxdefaultconf

if ! sudo nginx -t >/dev/null 2>&1; then
  sudo nginx -t
  echo -ne "\n"
  echo -ne "${RED}You have syntax errors in your nginx configs. See errors above. Please fix them and re-run this script.${NC}\n"
  echo -ne "${RED}Aborting...${NC}\n"
  exit 1
fi

HAS_PY311=$(python3.11 --version | grep ${PYTHON_VER})
if ! [[ $HAS_PY311 ]]; then
  printf >&2 "${GREEN}Updating to ${PYTHON_VER}${NC}\n"
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
fi

arch=$(uname -m)
nats_server='/usr/local/bin/nats-server'

HAS_LATEST_NATS=$(/usr/local/bin/nats-server -version | grep "${NATS_SERVER_VER}")
if ! [[ $HAS_LATEST_NATS ]]; then
  printf >&2 "${GREEN}Updating nats to v${NATS_SERVER_VER}${NC}\n"
  nats_tmp=$(mktemp -d -t nats-XXXXXXXXXX)
  if [ "$arch" = "x86_64" ]; then
    natsarch='amd64'
  else
    natsarch='arm64'
  fi
  wget https://github.com/nats-io/nats-server/releases/download/v${NATS_SERVER_VER}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}.tar.gz -P ${nats_tmp}
  tar -xzf ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}.tar.gz -C ${nats_tmp}
  sudo rm -f $nats_server
  sudo mv ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}/nats-server /usr/local/bin/
  sudo chmod +x $nats_server
  sudo chown ${USER}:${USER} $nats_server
  rm -rf ${nats_tmp}
fi

if [ -d ~/.npm ]; then
  sudo rm -rf ~/.npm
fi

if [ -d ~/.cache ]; then
  sudo rm -rf ~/.cache
fi

if [ -d ~/.config ]; then
  sudo chown -R $USER:$GROUP ~/.config
fi

if ! which npm >/dev/null; then
  sudo apt install -y npm
fi

# older distros still might not have npm after above command, due to recent changes to node apt packages which replaces nodesource with official node
# if we still don't have npm, force a switch to nodesource
if ! which npm >/dev/null; then
  sudo systemctl stop meshcentral
  sudo chown ${USER}:${USER} -R /meshcentral
  sudo apt remove -y nodejs
  sudo rm -rf /usr/lib/node_modules

  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs
  sudo npm install -g npm

  cd /meshcentral
  rm -rf node_modules/ package-lock.json
  npm install
  sudo systemctl start meshcentral
fi

sudo npm install -g npm

CURRENT_MESH_VER=$(cd /meshcentral/node_modules/meshcentral && node -p -e "require('./package.json').version")
if [[ "${CURRENT_MESH_VER}" != "${LATEST_MESH_VER}" ]] || [[ "$force" = true ]]; then
  printf >&2 "${GREEN}Updating meshcentral from ${CURRENT_MESH_VER} to ${LATEST_MESH_VER}${NC}\n"
  sudo systemctl stop meshcentral
  sudo chown ${USER}:${USER} -R /meshcentral
  cd /meshcentral
  rm -rf node_modules/ package.json package-lock.json
  mesh_pkg="$(
    cat <<EOF
{
  "dependencies": {
    "archiver": "7.0.1",
    "meshcentral": "${LATEST_MESH_VER}",
    "otplib": "10.2.3",
    "pg": "8.7.1",
    "pgtools": "0.3.2"
  }
}
EOF
  )"
  echo "${mesh_pkg}" >/meshcentral/package.json
  npm install
  sudo systemctl start meshcentral
fi

# update from main repo
cd /rmm
git config user.email "admin@example.com"
git config user.name "Bob"
git fetch
git checkout master
git reset --hard FETCH_HEAD
git clean -df
git pull

# update from community-scripts repo
if [[ ! -d ${SCRIPTS_DIR} ]]; then
  sudo mkdir -p ${SCRIPTS_DIR}
  sudo chown ${USER}:${USER} ${SCRIPTS_DIR}
  git clone https://github.com/amidaware/community-scripts.git ${SCRIPTS_DIR}/
  cd ${SCRIPTS_DIR}
  git config user.email "admin@example.com"
  git config user.name "Bob"
else
  cd ${SCRIPTS_DIR}
  git config user.email "admin@example.com"
  git config user.name "Bob"
  git fetch
  git checkout main
  git reset --hard FETCH_HEAD
  git clean -df
  git pull
fi

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

sudo chown ${USER}:${USER} -R /rmm
sudo chown ${USER}:${USER} -R ${SCRIPTS_DIR}
sudo chown ${USER}:${USER} /var/log/celery
sudo chown ${USER}:${USER} -R /etc/conf.d/
sudo chown ${USER}:${USER} -R /etc/letsencrypt

if [ -d /rmmbackups ]; then
  sudo chown ${USER}:${USER} -R /rmmbackups
fi

CHECK_CELERY_CONFIG=$(grep "autoscale=20,2" /etc/conf.d/celery.conf)
if ! [[ $CHECK_CELERY_CONFIG ]]; then
  sed -i 's/CELERYD_OPTS=.*/CELERYD_OPTS="--time-limit=86400 --autoscale=20,2"/g' /etc/conf.d/celery.conf
fi

CHECK_ADMIN_ENABLED=$(grep ADMIN_ENABLED $local_settings)
if ! [[ $CHECK_ADMIN_ENABLED ]]; then
  adminenabled="$(
    cat <<EOF
ADMIN_ENABLED = False
EOF
  )"
  echo "${adminenabled}" | tee --append $local_settings >/dev/null
fi

if [ "$arch" = "x86_64" ]; then
  natsapi='nats-api'
else
  natsapi='nats-api-arm64'
fi

nats_api='/usr/local/bin/nats-api'
sudo cp /rmm/natsapi/bin/${natsapi} $nats_api
sudo chown ${USER}:${USER} $nats_api
sudo chmod +x $nats_api

if [[ "${CURRENT_PIP_VER}" != "${LATEST_PIP_VER}" ]] || [[ "$force" = true ]]; then
  rm -rf /rmm/api/env
  cd /rmm/api
  python3.11 -m venv env
  source /rmm/api/env/bin/activate
  cd /rmm/api/tacticalrmm
  pip install --no-cache-dir --upgrade pip
  pip install --no-cache-dir setuptools==${SETUPTOOLS_VER} wheel==${WHEEL_VER}
  pip install --no-cache-dir -r requirements.txt
else
  source /rmm/api/env/bin/activate
  cd /rmm/api/tacticalrmm
  pip install -r requirements.txt
fi

if [ ! -d /opt/tactical/reporting/assets ]; then
  sudo mkdir -p /opt/tactical/reporting/assets
fi

if [ ! -d /opt/tactical/reporting/schemas ]; then
  sudo mkdir /opt/tactical/reporting/schemas
fi

sed -i '/^REDIS_HOST/d' $local_settings

sudo chown -R ${USER}:${USER} /opt/tactical

python manage.py pre_update_tasks
celery -A tacticalrmm purge -f
printf >&2 "${GREEN}Running database migrations (this might take a long time)...${NC}\n"
python manage.py migrate
python manage.py generate_json_schemas
python manage.py delete_tokens
python manage.py collectstatic --no-input
python manage.py reload_nats
python manage.py load_chocos
python manage.py create_installer_user
python manage.py create_natsapi_conf
python manage.py create_uwsgi_conf
python manage.py clear_redis_celery_locks
python manage.py post_update_tasks
echo "Running management commands...please wait..."
API=$(python manage.py get_config api)
WEB_VERSION=$(python manage.py get_config webversion)
FRONTEND=$(python manage.py get_config webdomain)
MESHDOMAIN=$(python manage.py get_config meshdomain)
WEBTAR_URL=$(python manage.py get_webtar_url)
CERT_PUB_KEY=$(python manage.py get_config certfile)
CERT_PRIV_KEY=$(python manage.py get_config keyfile)
deactivate

if grep -q manage_etc_hosts /etc/hosts; then
  sudo sed -i '/manage_etc_hosts: true/d' /etc/cloud/cloud.cfg >/dev/null
  if ! grep -q "manage_etc_hosts: false" /etc/cloud/cloud.cfg; then
    echo -e "\nmanage_etc_hosts: false" | sudo tee --append /etc/cloud/cloud.cfg >/dev/null
    sudo systemctl restart cloud-init >/dev/null
  fi
fi

rmmconf='/etc/nginx/sites-available/rmm.conf'
if ! grep -q "location /assets/" $rmmconf; then
  printf >&2 "${YELLOW}WARNING!!!!\n\n"
  printf >&2 "${rmmconf} will now be replaced due to changes needed for this update.\n\n"
  printf >&2 "A backup of the existing config will be created in your home directory at ~/rmm.conf.nginx.bak\n\n"
  printf >&2 "If you have made any custom or unsupported changes to this file please add them back in after this update.\n\n"
  read -n 1 -s -r -p "Press any key to confirm you have read the above and continue..."
  printf >&2 "\n${NC}\n"
  cp $rmmconf ~/rmm.conf.nginx.bak
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
fi

CHECK_HOSTS=$(grep 127.0.1.1 /etc/hosts | grep "$API" | grep "$FRONTEND" | grep "$MESHDOMAIN")
HAS_11=$(grep 127.0.1.1 /etc/hosts)

if ! [[ $CHECK_HOSTS ]]; then
  if [[ $HAS_11 ]]; then
    sudo sed -i "/127.0.1.1/s/$/ ${API} ${FRONTEND} ${MESHDOMAIN}/" /etc/hosts
  else
    echo "127.0.1.1 ${API} ${FRONTEND} ${MESHDOMAIN}" | sudo tee --append /etc/hosts >/dev/null
  fi
fi

if [ -d /rmm/web ]; then
  rm -rf /rmm/web
fi

if [ ! -d /var/www/rmm ]; then
  sudo mkdir -p /var/www/rmm
fi

webtar="trmm-web-v${WEB_VERSION}.tar.gz"
wget -q ${WEBTAR_URL} -O /tmp/${webtar}
sudo rm -rf /var/www/rmm/dist
sudo tar -xzf /tmp/${webtar} -C /var/www/rmm
echo "window._env_ = {PROD_URL: \"https://${API}\"}" | sudo tee /var/www/rmm/dist/env-config.js >/dev/null
sudo chown www-data:www-data -R /var/www/rmm/dist
rm -f /tmp/${webtar}

for i in nats nats-api rmm daphne celery celerybeat nginx; do
  printf >&2 "${GREEN}Starting ${i} service${NC}\n"
  sudo systemctl start ${i}
done

rm -f $TMP_SETTINGS
printf >&2 "${GREEN}Update finished!${NC}\n"
