#!/bin/bash

SCRIPT_VERSION="10"
SCRIPT_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/update.sh'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

TMP_FILE=$(mktemp -p "" "rmmupdate_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" > ${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" \< "${NEW_VER}" ]; then
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


for i in celery celerybeat celery-winupdate rmm nginx
do
sudo systemctl stop ${i}
done


sudo chown ${USER}:${USER} -R /rmm
sudo chown ${USER}:${USER} /var/log/celery
sudo chown ${USER}:${USER} -R /srv/salt/
sudo chown ${USER}:${USER} -R /etc/conf.d/
sudo chown ${USER}:www-data /srv/salt/scripts/userdefined
sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config
sudo chown -R $USER:$GROUP /home/${USER}/.cache
sudo chmod 750 /srv/salt/scripts/userdefined

cd /rmm
git fetch origin develop
git reset --hard FETCH_HEAD
git clean -df
cp /rmm/_modules/* /srv/salt/_modules/
cp /rmm/scripts/* /srv/salt/scripts/
rm -rf /rmm/api/env
cd /rmm/api
python3 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools==49.6.0 wheel==0.35.1
pip install --no-cache-dir -r requirements.txt
python manage.py pre_update_tasks
python manage.py migrate
python manage.py delete_tokens
python manage.py fix_salt_key
python manage.py collectstatic --no-input
python manage.py post_update_tasks
deactivate


rm -rf /rmm/web/node_modules
rm -rf /rmm/web/dist
cd /rmm/web
npm install
npm run build
sudo rm -rf /var/www/rmm/dist
sudo cp -pvr /rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist

for i in celery celerybeat celery-winupdate rmm nginx
do
sudo systemctl start ${i}
done

sudo systemctl stop meshcentral
sudo chown ${USER}:${USER} -R /meshcentral
cd /meshcentral
rm -rf node_modules/
npm install meshcentral@0.6.48
sudo systemctl start meshcentral
sleep 10

printf >&2 "${GREEN}Update finished!${NC}\n"