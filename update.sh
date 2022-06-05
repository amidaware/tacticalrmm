#!/bin/bash

### Script info
SCRIPT_VERSION="135"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/update.sh'
LATEST_SETTINGS_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py'
THIS_SCRIPT=$(readlink -f "$0")

### Misc info
SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.10.4'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'

### Import functions
. $PWD/bashfunctions.cfg

### Set colors
setColors;

### Install script pre-reqs
installPreReqs;

### Check for new functions version, only include script name as variable
checkCfgVer "$THIS_SCRIPT";

### Check for new script version, pass script version, url, and script name variables in that order
checkScriptVer "$SCRIPT_VERSION" "$SCRIPT_URL" "$THIS_SCRIPT";

### Install additional prereqs
installAdditionalPreReqs;

### Check for force update flag
force=false
if [[ $* == *--force* ]]; then
    force=true
fi

### Check if root
checkRoot;

### Check if user is same as during installation
strip="User="
ORIGUSER=$(grep ${strip} /etc/systemd/system/rmm.service | sed -e "s/^${strip}//")

if [ "$ORIGUSER" != "$USER" ]; then
  printf >&2 "${RED}ERROR: You must run this update script from the same user account used during install: ${GREEN}${ORIGUSER}${NC}\n"
  exit 1
fi

### Get current release version and check if update is necessary
TMP_SETTINGS=$(mktemp -p "" "rmmsettings_XXXXXXXXXX")
curl -s -L "${LATEST_SETTINGS_URL}" > ${TMP_SETTINGS}

LATEST_TRMM_VER=$(grep "^TRMM_VERSION" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
CURRENT_TRMM_VER=$(grep "^TRMM_VERSION" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

if [[ "${CURRENT_TRMM_VER}" == "${LATEST_TRMM_VER}" ]] && ! [[ "$force" = true ]]; then
  printf >&2 "${GREEN}Already on latest version. Current version: ${CURRENT_TRMM_VER} Latest version: ${LATEST_TRMM_VER}${NC}\n"
  rm -f $TMP_SETTINGS
  exit 0
fi

### Get current versions of necessary included apps
LATEST_MESH_VER=$(grep "^MESH_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
LATEST_PIP_VER=$(grep "^PIP_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
NATS_SERVER_VER=$(grep "^NATS_SERVER_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')

CURRENT_PIP_VER=$(grep "^PIP_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

### This does... something
cls;


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

### Update services
sudo systemctl daemon-reload
fi

### Check Nginx config
installNginx "updatepart1";

### Stop services
for i in nginx nats-api nats rmm daphne celery celerybeat
do
printf >&2 "${GREEN}Stopping ${i} service...${NC}\n"
sudo systemctl stop ${i}
done

### Rebuild uwsgi config
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

### Check additional Nginx settings and update
installNginx "updatepart2";

### Check if Python is up to date, if not, update
installPython "update";

### Check if NATS is up to date, if not, update
installNats "update";

if [ -d ~/.npm ]; then
  sudo rm -rf ~/.npm
fi

if [ -d ~/.cache ]; then
  sudo rm -rf ~/.cache
fi

if [ -d ~/.config ]; then
  sudo chown -R $USER:$GROUP ~/.config
fi

### Check NodeJS version, update if needed and update MeshCentral
installNodeJS "update";

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
API=$(python manage.py get_config api)
WEB_VERSION=$(python manage.py get_config webversion)
deactivate

printf >&2 "${GREEN}Turning off redis aof${NC}\n"
sudo redis-cli config set appendonly no
sudo redis-cli config rewrite
sudo rm -f /var/lib/redis/appendonly.aof


if [ -d /rmm/web ]; then
  rm -rf /rmm/web
fi

if [ ! -d /var/www/rmm ]; then
  sudo mkdir -p /var/www/rmm
fi

webtar="trmm-web-v${WEB_VERSION}.tar.gz"
wget -q https://github.com/amidaware/tacticalrmm-web/releases/download/v${WEB_VERSION}/${webtar} -O /tmp/${webtar}
sudo rm -rf /var/www/rmm/dist
sudo tar -xzf /tmp/${webtar} -C /var/www/rmm
echo "window._env_ = {PROD_URL: \"https://${API}\"}" | sudo tee /var/www/rmm/dist/env-config.js > /dev/null
sudo chown www-data:www-data -R /var/www/rmm/dist
rm -f /tmp/${webtar}

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