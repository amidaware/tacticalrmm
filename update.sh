#!/bin/bash

SCRIPT_VERSION="100"
SCRIPT_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/update.sh'
LATEST_SETTINGS_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

TMP_FILE=$(mktemp -p "" "rmmupdate_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" > ${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" -ne "${NEW_VER}" ]; then
    printf >&2 "${YELLOW}Old update script detected, downloading and replacing with the latest version...${NC}\n"
    wget -q "${SCRIPT_URL}" -O update.sh
    printf >&2 "${YELLOW}Script updated! Please re-run ./update.sh${NC}\n"
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
LATEST_SALT_VER=$(grep "^SALT_MASTER_VER" "$TMP_SETTINGS" | awk -F'[= "]' '{print $5}')

CURRENT_PIP_VER=$(grep "^PIP_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
CURRENT_NPM_VER=$(grep "^NPM_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

NEEDS_NATS=false
if [ ! -f /etc/systemd/system/nats.service ]; then
  if [ ! -d /etc/letsencrypt ]; then
      printf >&2 "${RED}ERROR: no letsencrypt cert detected. The RMM now requires a valid TLS certificate${NC}\n"
      printf >&2 "${RED}Please send us a message in our discord for instructions on how to proceed, or open a github ticket.${NC}\n"
      exit 1
  fi
  NEEDS_NATS=true
fi

if [ "$NEEDS_NATS" = true ]; then
printf "\033c"
printf >&2 "\n\n"
printf >&2 "${YELLOW}WARNING: BREAKING CHANGES AHEAD${NC}\n\n"
printf >&2 "${YELLOW}In order to continue with this update, please open up port 4222 TCP in ufw${NC}\n\n"
printf >&2 "${YELLOW}If you are running behind NAT, make sure to also setup the necessary port forwards in your router${NC}\n\n"
printf >&2 "${YELLOW}Run the following command to open the port in ufw firewall:\n\n${GREEN}sudo ufw allow proto tcp from any to any port 4222 && sudo ufw reload${NC}\n\n\n"
printf >&2 "${YELLOW}Many of your agent functions will stop working until your agents are updated to at least version 1.1.0${NC}\n"
printf >&2 "${YELLOW}This will happen shortly after this update completes, as long as you have auto agent updated enabled in Global Settings${NC}\n"
printf >&2 "${YELLOW}A background job also runs every hour to auto update agents.\nIf you do not want to wait, you may manually trigger an agent update from the Agents > Update Agents menu in the web ui.${NC}\n\n\n"
until [[ "$CONFIRM_NATS" == "yes" ]]; do
    echo -ne "${RED}If you have not opened port 4222 yet, please Ctrl+C to cancel this script, open the port and then re-run${NC}"
    printf >&2 "\n\n"
    echo -ne "${YELLOW}Confirm you have port 4222 TCP open? [type 'yes' to confirm]${NC}: "
    read CONFIRM_NATS
done
printf >&2 "\n"
fi

if [ "$NEEDS_NATS" = true ]; then
printf >&2 "${Green}Downloading nats${NC}\n\n"
nats_tmp=$(mktemp -d -t nats-XXXXXXXXXX)
wget https://github.com/nats-io/nats-server/releases/download/v2.1.9/nats-server-v2.1.9-linux-amd64.tar.gz -P ${nats_tmp}

tar -xzf ${nats_tmp}/nats-server-v2.1.9-linux-amd64.tar.gz -C ${nats_tmp}

sudo mv ${nats_tmp}/nats-server-v2.1.9-linux-amd64/nats-server /usr/local/bin/
sudo chmod +x /usr/local/bin/nats-server
sudo chown ${USER}:${USER} /usr/local/bin/nats-server
rm -rf ${nats_tmp}

natsservice="$(cat << EOF
[Unit]
Description=NATS Server
After=network.target ntp.service

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

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsservice}" | sudo tee /etc/systemd/system/nats.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable nats.service

fi


for i in nginx rmm celery celerybeat celery-winupdate nats
do
printf >&2 "${GREEN}Stopping ${i} service...${NC}\n"
sudo systemctl stop ${i}
done

cd /rmm
git config user.email "admin@example.com"
git config user.name "Bob"
git fetch
git checkout master
git reset --hard FETCH_HEAD
git clean -df
git pull

CHECK_SALT=$(sudo salt --version | grep ${LATEST_SALT_VER})
if ! [[ $CHECK_SALT ]]; then
  printf >&2 "${GREEN}Updating salt${NC}\n"
  sudo apt update
  sudo apt install -y salt-master salt-api salt-common
  printf >&2 "${GREEN}Waiting for salt...${NC}\n"
  sleep 15
  sudo systemctl stop salt-master
  sudo systemctl stop salt-api
  printf >&2 "${GREEN}Fixing msgpack${NC}\n"
  sudo sed -i 's/msgpack_kwargs = {"raw": six.PY2}/msgpack_kwargs = {"raw": six.PY2, "max_buffer_size": 2147483647}/g' /usr/lib/python3/dist-packages/salt/transport/ipc.py
  sudo systemctl start salt-master
  printf >&2 "${GREEN}Waiting for salt...${NC}\n"
  sleep 15
  sudo systemctl start salt-api
  printf >&2 "${GREEN}Salt update finished${NC}\n"
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
sudo chown ${USER}:${USER} -R /etc/letsencrypt
sudo chmod 775 -R /etc/letsencrypt

cp /rmm/_modules/* /srv/salt/_modules/
cp /rmm/scripts/* /srv/salt/scripts/
/usr/local/rmmgo/go/bin/go get github.com/josephspurrier/goversioninfo/cmd/goversioninfo
sudo cp /rmm/api/tacticalrmm/core/goinstaller/bin/goversioninfo /usr/local/bin/
sudo chown ${USER}:${USER} /usr/local/bin/goversioninfo
sudo chmod +x /usr/local/bin/goversioninfo

printf >&2 "${GREEN}Running postgres vacuum${NC}\n"
sudo -u postgres psql -d tacticalrmm -c "vacuum full logs_auditlog"
sudo -u postgres psql -d tacticalrmm -c "vacuum full logs_pendingaction"
sudo -u postgres psql -d tacticalrmm -c "vacuum full agents_agentoutage"

if [[ "${CURRENT_PIP_VER}" != "${LATEST_PIP_VER}" ]]; then
  rm -rf /rmm/api/env
  cd /rmm/api
  python3 -m venv env
  source /rmm/api/env/bin/activate
  cd /rmm/api/tacticalrmm
  pip install --no-cache-dir --upgrade pip
  pip install --no-cache-dir setuptools==50.3.2 wheel==0.36.1
  pip install --no-cache-dir -r requirements.txt
else
  source /rmm/api/env/bin/activate
  cd /rmm/api/tacticalrmm
  pip install -r requirements.txt
fi

python manage.py pre_update_tasks
python manage.py migrate
python manage.py delete_tokens
python manage.py fix_salt_key
python manage.py collectstatic --no-input
python manage.py reload_nats
python manage.py post_update_tasks
deactivate

rm -rf /rmm/web/dist
rm -rf /rmm/web/.quasar
cd /rmm/web
if [[ "${CURRENT_NPM_VER}" != "${LATEST_NPM_VER}" ]]; then
  rm -rf /rmm/web/node_modules
  npm install
fi

npm run build
sudo rm -rf /var/www/rmm/dist
sudo cp -pr /rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist

for i in celery celerybeat celery-winupdate rmm nginx nats
do
printf >&2 "${GREEN}Starting ${i} service${NC}\n"
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