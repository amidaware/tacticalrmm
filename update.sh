#!/bin/bash

SCRIPT_VERSION="124"
SCRIPT_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/update.sh'
LATEST_SETTINGS_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
THIS_SCRIPT=$(readlink -f "$0")

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

CHECK_TOO_OLD=$(grep natsapi /etc/nginx/sites-available/rmm.conf)
if ! [[ $CHECK_TOO_OLD ]]; then
  printf >&2 "${RED}Your version of TRMM is no longer supported. Refusing to update.${NC}\n"
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

CURRENT_PIP_VER=$(grep "^PIP_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
CURRENT_NPM_VER=$(grep "^NPM_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')


if [ -f /etc/systemd/system/natsapi.service ]; then
  printf >&2 "${GREEN}Removing natsapi.service${NC}\n"
  sudo systemctl stop natsapi.service
  sudo systemctl disable natsapi.service
  sudo rm -f /etc/systemd/system/natsapi.service
  sudo systemctl daemon-reload
fi

cls() {
  printf "\033c"
}

CHECK_HAS_DAPHNE=$(grep daphne.sock /etc/nginx/sites-available/rmm.conf)
if ! [[ $CHECK_HAS_DAPHNE ]]; then
  cls
  echo -ne "${RED}Nginx config changes required before continuing.${NC}\n"
  echo -ne "${RED}Please check the v0.5.0 release notes on github for instructions, then re-run this script.${NC}\n"
  echo -ne "${YELLOW}https://github.com/wh1te909/tacticalrmm/releases/tag/v0.5.0${NC}\n"
  echo -ne "${RED}Aborting...${NC}\n"
  exit 1
fi

if ! sudo nginx -t > /dev/null 2>&1; then
  sudo nginx -t
  echo -ne "\n"
  echo -ne "${RED}You have syntax errors in your nginx configs. See errors above. Please fix them and re-run this script.${NC}\n"
  echo -ne "${RED}Aborting...${NC}\n"
  exit 1
fi

if ! [ -f /etc/systemd/system/daphne.service ]; then
daphneservice="$(cat << EOF
[Unit]
Description=django channels daemon
After=network.target

[Service]
User=${USER}
Group=www-data
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PATH=/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/rmm/api/env/bin/daphne -u /rmm/daphne.sock tacticalrmm.asgi:application
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${daphneservice}" | sudo tee /etc/systemd/system/daphne.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable daphne.service
fi

for i in nginx nats rmm daphne celery celerybeat
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
EOF
)"
echo "${uwsgini}" > /rmm/api/tacticalrmm/app.ini

CHECK_NGINX_WORKER_CONN=$(grep "worker_connections 2048" /etc/nginx/nginx.conf)
if ! [[ $CHECK_NGINX_WORKER_CONN ]]; then
  printf >&2 "${GREEN}Changing nginx worker connections to 2048${NC}\n"
  sudo sed -i 's/worker_connections.*/worker_connections 2048;/g' /etc/nginx/nginx.conf
fi

HAS_PY39=$(which python3.9)
if ! [[ $HAS_PY39 ]]; then
  printf >&2 "${GREEN}Updating to Python 3.9${NC}\n"
  sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev
  numprocs=$(nproc)
  cd ~
  wget https://www.python.org/ftp/python/3.9.2/Python-3.9.2.tgz
  tar -xf Python-3.9.2.tgz
  cd Python-3.9.2
  ./configure --enable-optimizations
  make -j $numprocs
  sudo make altinstall
  cd ~
  sudo rm -rf Python-3.9.2 Python-3.9.2.tgz
fi

HAS_NATS220=$(/usr/local/bin/nats-server -version | grep v2.2.6)
if ! [[ $HAS_NATS220 ]]; then
  printf >&2 "${GREEN}Updating nats to v2.2.6${NC}\n"
  nats_tmp=$(mktemp -d -t nats-XXXXXXXXXX)
  wget https://github.com/nats-io/nats-server/releases/download/v2.2.6/nats-server-v2.2.6-linux-amd64.tar.gz -P ${nats_tmp}
  tar -xzf ${nats_tmp}/nats-server-v2.2.6-linux-amd64.tar.gz -C ${nats_tmp}
  sudo rm -f /usr/local/bin/nats-server
  sudo mv ${nats_tmp}/nats-server-v2.2.6-linux-amd64/nats-server /usr/local/bin/
  sudo chmod +x /usr/local/bin/nats-server
  sudo chown ${USER}:${USER} /usr/local/bin/nats-server
  rm -rf ${nats_tmp}
fi

HAS_NODE14=$(/usr/bin/node --version | grep v14)
if ! [[ $HAS_NODE14 ]]; then
  printf >&2 "${GREEN}Updating NodeJS to v14${NC}\n"
  rm -rf /rmm/web/node_modules
  sudo systemctl stop meshcentral
  sudo apt remove -y nodejs
  sudo rm -rf /usr/lib/node_modules
  sudo rm -rf /home/${USER}/.npm/*
  curl -sL https://deb.nodesource.com/setup_14.x | sudo -E bash -
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

cd /rmm
git config user.email "admin@example.com"
git config user.name "Bob"
git fetch
git checkout master
git reset --hard FETCH_HEAD
git clean -df
git pull

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')


sudo chown ${USER}:${USER} -R /rmm
sudo chown ${USER}:${USER} /var/log/celery
sudo chown ${USER}:${USER} -R /etc/conf.d/
sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config
sudo chown -R $USER:$GROUP /home/${USER}/.cache
sudo chown ${USER}:${USER} -R /etc/letsencrypt
sudo chmod 775 -R /etc/letsencrypt

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
  python3.9 -m venv env
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
python manage.py migrate
python manage.py delete_tokens
python manage.py collectstatic --no-input
python manage.py reload_nats
python manage.py load_chocos
python manage.py create_installer_user
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

for i in rmm daphne celery celerybeat nginx nats
do
printf >&2 "${GREEN}Starting ${i} service${NC}\n"
sudo systemctl start ${i}
done

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

# apply redis configuration
sudo redis-cli config set appendonly yes
sudo redis-cli config rewrite

rm -f $TMP_SETTINGS
printf >&2 "${GREEN}Update finished!${NC}\n"