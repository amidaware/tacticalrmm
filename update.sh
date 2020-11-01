#!/bin/bash

SCRIPT_VERSION="94"
SCRIPT_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/update.sh'
LATEST_SETTINGS_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

TMP_FILE=$(mktemp -p "" "rmmupdate_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" > ${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" -ne "${NEW_VER}" ]; then
    printf >&2 "${YELLOW}A newer version of this update script is available.${NC}\n"
    printf >&2 "${YELLOW}Please download the latest version from ${GREEN}${SCRIPT_URL}${YELLOW} and re-run.${NC}\n"
    rm -f $TMP_FILE
    exit 1
fi

rm -f $TMP_FILE

if [ $EUID -eq 0 ]; then
  echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
  exit 1
fi

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

if [[ "${CURRENT_TRMM_VER}" == "${LATEST_TRMM_VER}" ]]; then
  printf >&2 "${GREEN}Already on latest version. Current version: ${CURRENT_TRMM_VER} Latest version: ${LATEST_TRMM_VER}${NC}\n"
  rm -f $TMP_SETTINGS
  exit 0
fi

LATEST_MESH_VER=$(grep "^MESH_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
LATEST_PIP_VER=$(grep "^PIP_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')
LATEST_NPM_VER=$(grep "^NPM_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')

CURRENT_PIP_VER=$(grep "^PIP_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
CURRENT_NPM_VER=$(grep "^NPM_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

for i in nginx rmm celery celerybeat celery-winupdate
do
sudo systemctl stop ${i}
done

cd /rmm
git fetch
git checkout master
git reset --hard FETCH_HEAD
git clean -df
git pull

# added new celery queue 9-7-2020
if [ ! -f /etc/systemd/system/celery-winupdate.service ]; then
celerywinupdatesvc="$(cat << EOF
[Unit]
Description=Celery WinUpdate Service
After=network.target
After=redis-server.service

[Service]
Type=forking
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery-winupdate.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} multi start \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} -Q wupdate \${CELERYD_OPTS}'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \${CELERYD_NODES} --pidfile=\${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c '\${CELERY_BIN} multi restart \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} -Q wupdate \${CELERYD_OPTS}'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerywinupdatesvc}" | sudo tee /etc/systemd/system/celery-winupdate.service > /dev/null

celerywinupdate="$(cat << EOF
CELERYD_NODES="w2"

CELERY_BIN="/rmm/api/env/bin/celery"
CELERY_APP="tacticalrmm"
CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=4000 --autoscale=40,1"

CELERYD_PID_FILE="/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="ERROR"
EOF
)"
echo "${celerywinupdate}" | sudo tee /etc/conf.d/celery-winupdate.conf > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable celery-winupdate
fi

sudo chown ${USER}:${USER} -R /rmm
sudo chown ${USER}:${USER} /var/log/celery
sudo chown ${USER}:${USER} -R /srv/salt/
sudo chown ${USER}:${USER} -R /etc/conf.d/
sudo chown ${USER}:www-data /srv/salt/scripts/userdefined
sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config
sudo chown -R $USER:$GROUP /home/${USER}/.cache
sudo chmod 750 /srv/salt/scripts/userdefined

cp /rmm/_modules/* /srv/salt/_modules/
cp /rmm/scripts/* /srv/salt/scripts/
/usr/local/rmmgo/go/bin/go get github.com/josephspurrier/goversioninfo/cmd/goversioninfo
sudo cp /rmm/api/tacticalrmm/core/goinstaller/bin/goversioninfo /usr/local/bin/
sudo chown ${USER}:${USER} /usr/local/bin/goversioninfo
sudo chmod +x /usr/local/bin/goversioninfo

if [[ "${CURRENT_PIP_VER}" != "${LATEST_PIP_VER}" ]]; then
  rm -rf /rmm/api/env
  cd /rmm/api
  python3 -m venv env
  source /rmm/api/env/bin/activate
  cd /rmm/api/tacticalrmm
  pip install --no-cache-dir --upgrade pip
  pip install --no-cache-dir setuptools==49.6.0 wheel==0.35.1
  pip install --no-cache-dir -r requirements.txt
else
  source /rmm/api/env/bin/activate
  cd /rmm/api/tacticalrmm
fi

python manage.py pre_update_tasks
python manage.py migrate
python manage.py delete_tokens
python manage.py fix_salt_key
python manage.py collectstatic --no-input
python manage.py post_update_tasks
deactivate

rm -rf /rmm/web/dist
cd /rmm/web
if [[ "${CURRENT_NPM_VER}" != "${LATEST_NPM_VER}" ]]; then
  rm -rf /rmm/web/node_modules
  npm install
fi

npm run build
sudo rm -rf /var/www/rmm/dist
sudo cp -pr /rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist

for i in celery celerybeat celery-winupdate rmm nginx
do
sudo systemctl start ${i}
done

CURRENT_MESH_VER=$(cd /meshcentral && npm list meshcentral | grep 'meshcentral@' | awk -F'[@]' '{print $2}' | tr -d " \t")
if [[ "${CURRENT_MESH_VER}" != "${LATEST_MESH_VER}" ]]; then
  printf >&2 "${GREEN}Updating meshcentral from ${CURRENT_MESH_VER} to ${LATEST_MESH_VER}${NC}\n"
  sudo systemctl stop meshcentral
  sudo chown ${USER}:${USER} -R /meshcentral
  cd /meshcentral
  rm -rf node_modules/
  npm install meshcentral@${LATEST_MESH_VER}
  sudo systemctl start meshcentral
  sleep 10
fi

rm -f $TMP_SETTINGS
printf >&2 "${GREEN}Update finished!${NC}\n"