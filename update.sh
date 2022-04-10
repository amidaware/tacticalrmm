#!/bin/bash

SCRIPT_VERSION="133"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/update.sh'
LATEST_SETTINGS_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
THIS_SCRIPT=$(readlink -f "$0")

SCRIPTS_DIR="/opt/trmm-community-scripts"
PYTHON_VER="3.10.2"

TMP_FILE=$(mktemp -p "" "rmmupdate_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" > ${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" -ne "${NEW_VER}" ]; then
    printf >&2 "${YELLOW}Old update script detected, downloading and replacing with the latest version...${NC}\n"
    wget -q "${SCRIPT_URL}" -O update.sh
    exec ${THIS_SCRIPT}
fi

rm -f $TMP_FILE

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
curl -s -L "${LATEST_SETTINGS_URL}" > ${TMP_SETTINGS}
SETTINGS_FILE="/rmm/api/tacticalrmm/tacticalrmm/settings.py"

LATEST_TRMM_VER=$(grep "^TRMM_VERSION" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
CURRENT_TRMM_VER=$(grep "^TRMM_VERSION" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

if [[ "${CURRENT_TRMM_VER}" == "${LATEST_TRMM_VER}" ]] && ! [[ "$force" = true ]]; then
  printf >&2 "${GREEN}Already on latest version. Current version: ${CURRENT_TRMM_VER} Latest version: ${LATEST_TRMM_VER}${NC}\n"
  rm -f $TMP_SETTINGS
  exit 0
fi

LATEST_MESH_VER=$(grep "^MESH_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
LATEST_PIP_VER=$(grep "^PIP_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
LATEST_NPM_VER=$(grep "^NPM_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
NATS_SERVER_VER=$(grep "^NATS_SERVER_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')

CURRENT_PIP_VER=$(grep "^PIP_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
CURRENT_NPM_VER=$(grep "^NPM_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

cls() {
  printf "\033c"
}


CHECK_NATS_LIMITNOFILE=$(grep LimitNOFILE /etc/systemd/system/nats.service)
if ! [[ $CHECK_NATS_LIMITNOFILE ]]; then

sudo rm -f /etc/systemd/system/nats.service

natsservice="$(cat << EOF
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
echo "${natsservice}" | sudo tee /etc/systemd/system/nats.service > /dev/null
sudo systemctl daemon-reload
fi

if ! sudo nginx -t > /dev/null 2>&1; then
  sudo nginx -t
  echo -ne "\n"
  echo -ne "${RED}You have syntax errors in your nginx configs. See errors above. Please fix them and re-run this script.${NC}\n"
  echo -ne "${RED}Aborting...${NC}\n"
  exit 1
fi

for i in nginx nats-api nats rmm daphne celery celerybeat
do
printf >&2 "${GREEN}Stopping ${i} service...${NC}\n"
sudo systemctl stop ${i}
done

printf >&2 "${GREEN}Restarting postgresql database${NC}\n"
sudo systemctl restart postgresql
sleep 5

rm -f /rmm/api/tacticalrmm/app.ini

numprocs=$(nproc)
uwsgiprocs=4
if [[ "$numprocs" == "1" ]]; then
  uwsgiprocs=2
else
  uwsgiprocs=$numprocs
fi

uwsgini="$(cat << EOF
[uwsgi]
chdir = /rmm/api/tacticalrmm
module = tacticalrmm.wsgi
home = /rmm/api/env
master = true
processes = ${uwsgiprocs}
threads = ${uwsgiprocs}
enable-threads = true
socket = /rmm/api/tacticalrmm/tacticalrmm.sock
harakiri = 300
chmod-socket = 660
buffer-size = 65535
vacuum = true
die-on-term = true
max-requests = 500
disable-logging = true
EOF
)"
echo "${uwsgini}" > /rmm/api/tacticalrmm/app.ini

CHECK_NGINX_WORKER_CONN=$(grep "worker_connections 2048" /etc/nginx/nginx.conf)
if ! [[ $CHECK_NGINX_WORKER_CONN ]]; then
  printf >&2 "${GREEN}Changing nginx worker connections to 2048${NC}\n"
  sudo sed -i 's/worker_connections.*/worker_connections 2048;/g' /etc/nginx/nginx.conf
fi

sudo sed -i 's/# server_names_hash_bucket_size.*/server_names_hash_bucket_size 64;/g' /etc/nginx/nginx.conf

HAS_PY310=$(python3.10 --version | grep ${PYTHON_VER})
if ! [[ $HAS_PY310 ]]; then
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

HAS_LATEST_NATS=$(/usr/local/bin/nats-server -version | grep "${NATS_SERVER_VER}")
if ! [[ $HAS_LATEST_NATS ]]; then
  printf >&2 "${GREEN}Updating nats to v${NATS_SERVER_VER}${NC}\n"
  nats_tmp=$(mktemp -d -t nats-XXXXXXXXXX)
  wget https://github.com/nats-io/nats-server/releases/download/v${NATS_SERVER_VER}/nats-server-v${NATS_SERVER_VER}-linux-amd64.tar.gz -P ${nats_tmp}
  tar -xzf ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-amd64.tar.gz -C ${nats_tmp}
  sudo rm -f /usr/local/bin/nats-server
  sudo mv ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-amd64/nats-server /usr/local/bin/
  sudo chmod +x /usr/local/bin/nats-server
  sudo chown ${USER}:${USER} /usr/local/bin/nats-server
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

HAS_NODE16=$(node --version | grep v16)
if ! [[ $HAS_NODE16 ]]; then
  printf >&2 "${GREEN}Updating NodeJS to v16${NC}\n"
  rm -rf /rmm/web/node_modules
  sudo systemctl stop meshcentral
  sudo apt remove -y nodejs
  sudo rm -rf /usr/lib/node_modules
  curl -sL https://deb.nodesource.com/setup_16.x | sudo -E bash -
  sudo apt update
  sudo apt install -y nodejs
  sudo npm install -g npm
  sudo chown ${USER}:${USER} -R /meshcentral
  cd /meshcentral
  rm -rf node_modules/
  npm install meshcentral@${LATEST_MESH_VER}
  sudo systemctl start meshcentral
fi

sudo npm install -g npm

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
sudo chmod 775 -R /etc/letsencrypt

CHECK_CELERY_CONFIG=$(grep "autoscale=20,2" /etc/conf.d/celery.conf)
if ! [[ $CHECK_CELERY_CONFIG ]]; then
  sed -i 's/CELERYD_OPTS=.*/CELERYD_OPTS="--time-limit=86400 --autoscale=20,2"/g' /etc/conf.d/celery.conf
fi

CHECK_ADMIN_ENABLED=$(grep ADMIN_ENABLED /rmm/api/tacticalrmm/tacticalrmm/local_settings.py)
if ! [[ $CHECK_ADMIN_ENABLED ]]; then
adminenabled="$(cat << EOF
ADMIN_ENABLED = False
EOF
)"
echo "${adminenabled}" | tee --append /rmm/api/tacticalrmm/tacticalrmm/local_settings.py > /dev/null
fi

sudo cp /rmm/natsapi/bin/nats-api /usr/local/bin
sudo chown ${USER}:${USER} /usr/local/bin/nats-api
sudo chmod +x /usr/local/bin/nats-api

if [[ "${CURRENT_PIP_VER}" != "${LATEST_PIP_VER}" ]] || [[ "$force" = true ]]; then
  rm -rf /rmm/api/env
  cd /rmm/api
  python3.10 -m venv env
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

python manage.py pre_update_tasks
celery -A tacticalrmm purge -f
python manage.py migrate
python manage.py delete_tokens
python manage.py collectstatic --no-input
python manage.py reload_nats
python manage.py load_chocos
python manage.py create_installer_user
python manage.py create_natsapi_conf
python manage.py post_update_tasks
deactivate

rm -rf /rmm/web/dist
rm -rf /rmm/web/.quasar
cd /rmm/web
if [[ "${CURRENT_NPM_VER}" != "${LATEST_NPM_VER}" ]] || [[ "$force" = true ]]; then
  rm -rf /rmm/web/node_modules
fi

npm install
npm run build
sudo rm -rf /var/www/rmm/dist
sudo cp -pr /rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist

for i in nats nats-api rmm daphne celery celerybeat nginx
do
printf >&2 "${GREEN}Starting ${i} service${NC}\n"
sudo systemctl start ${i}
done

sleep 1
/rmm/api/env/bin/python /rmm/api/tacticalrmm/manage.py update_agents

CURRENT_MESH_VER=$(cd /meshcentral/node_modules/meshcentral && node -p -e "require('./package.json').version")
if [[ "${CURRENT_MESH_VER}" != "${LATEST_MESH_VER}" ]] || [[ "$force" = true ]]; then
  printf >&2 "${GREEN}Updating meshcentral from ${CURRENT_MESH_VER} to ${LATEST_MESH_VER}${NC}\n"
  sudo systemctl stop meshcentral
  sudo chown ${USER}:${USER} -R /meshcentral
  cd /meshcentral
  rm -rf node_modules/
  npm install meshcentral@${LATEST_MESH_VER}
  sudo systemctl start meshcentral
fi

rm -f $TMP_SETTINGS
printf >&2 "${GREEN}Update finished!${NC}\n"