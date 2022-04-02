#!/bin/bash

SCRIPT_VERSION="35"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/restore.sh'

sudo apt update
sudo apt install -y curl wget dirmngr gnupg lsb-release

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPTS_DIR="/opt/trmm-community-scripts"
PYTHON_VER="3.10.2"

TMP_FILE=$(mktemp -p "" "rmmrestore_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" > ${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" -ne "${NEW_VER}" ]; then
    printf >&2 "${YELLOW}A newer version of this restore script is available.${NC}\n"
    printf >&2 "${YELLOW}Please download the latest version from ${GREEN}${SCRIPT_URL}${YELLOW} and re-run.${NC}\n"
    rm -f $TMP_FILE
    exit 1
fi

rm -f $TMP_FILE

osname=$(lsb_release -si); osname=${osname^}
osname=$(echo "$osname" | tr  '[A-Z]' '[a-z]')
fullrel=$(lsb_release -sd)
codename=$(lsb_release -sc)
relno=$(lsb_release -sr | cut -d. -f1)
fullrelno=$(lsb_release -sr)

# Fallback if lsb_release -si returns anything else than Ubuntu, Debian or Raspbian
if [ ! "$osname" = "ubuntu" ] && [ ! "$osname" = "debian" ]; then
  osname=$(grep -oP '(?<=^ID=).+' /etc/os-release | tr -d '"')
  osname=${osname^}
fi

# determine system
if ([ "$osname" = "ubuntu" ] && [ "$fullrelno" = "20.04" ]) || ([ "$osname" = "debian" ] && [ $relno -ge 10 ]); then
  echo $fullrel
else
 echo $fullrel
 echo -ne "${RED}Supported versions: Ubuntu 20.04, Debian 10 and 11\n"
 echo -ne "Your system does not appear to be supported${NC}\n"
 exit 1
fi

if ([ "$osname" = "ubuntu" ]); then
  mongodb_repo="deb [arch=amd64] https://repo.mongodb.org/apt/$osname $codename/mongodb-org/4.4 multiverse"
# there is no bullseye repo yet for mongo so just use buster on debian 11
elif ([ "$osname" = "debian" ] && [ $relno -eq 11 ]); then
  mongodb_repo="deb [arch=amd64] https://repo.mongodb.org/apt/$osname buster/mongodb-org/4.4 main"
else
  mongodb_repo="deb [arch=amd64] https://repo.mongodb.org/apt/$osname $codename/mongodb-org/4.4 main"
fi

postgresql_repo="deb [arch=amd64] https://apt.postgresql.org/pub/repos/apt/ $codename-pgdg main"

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

curl -sL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt update
sudo apt install -y gcc g++ make
sudo apt install -y nodejs
sudo npm install -g npm

print_green 'Restoring Nginx'

sudo apt install -y nginx
sudo systemctl stop nginx
sudo rm -rf /etc/nginx
sudo mkdir /etc/nginx
sudo tar -xzf $tmp_dir/nginx/etc-nginx.tar.gz -C /etc/nginx
sudo sed -i 's/worker_connections.*/worker_connections 2048;/g' /etc/nginx/nginx.conf
rmmdomain=$(grep server_name /etc/nginx/sites-available/rmm.conf | grep -v 301 | head -1 | tr -d " \t" | sed 's/.*server_name//' | tr -d ';')
frontenddomain=$(grep server_name /etc/nginx/sites-available/frontend.conf | grep -v 301 | head -1 | tr -d " \t" | sed 's/.*server_name//' | tr -d ';')
meshdomain=$(grep server_name /etc/nginx/sites-available/meshcentral.conf | grep -v 301 | head -1 | tr -d " \t" | sed 's/.*server_name//' | tr -d ';')


print_green 'Restoring hosts file'

HAS_11=$(grep 127.0.1.1 /etc/hosts)
if [[ $HAS_11 ]]; then
  sudo sed -i "/127.0.1.1/s/$/ ${rmmdomain} ${frontenddomain} ${meshdomain}/" /etc/hosts
else
  echo "127.0.1.1 ${rmmdomain} ${frontenddomain} ${meshdomain}" | sudo tee --append /etc/hosts > /dev/null
fi

print_green 'Restoring certbot'

sudo apt install -y software-properties-common
sudo apt install -y certbot openssl

print_green 'Restoring certs'

sudo rm -rf /etc/letsencrypt
sudo mkdir /etc/letsencrypt
sudo tar -xzf $tmp_dir/certs/etc-letsencrypt.tar.gz -C /etc/letsencrypt
sudo chown ${USER}:${USER} -R /etc/letsencrypt
sudo chmod 775 -R /etc/letsencrypt

print_green 'Restoring celery configs'

sudo mkdir /etc/conf.d
sudo tar -xzf $tmp_dir/confd/etc-confd.tar.gz -C /etc/conf.d
sudo chown ${USER}:${USER} -R /etc/conf.d

print_green 'Restoring systemd services'

sudo cp $tmp_dir/systemd/* /etc/systemd/system/
sudo systemctl daemon-reload

print_green 'Installing Python 3.10.2'

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
sudo apt install -y ca-certificates redis git

print_green 'Installing postgresql'

echo "$postgresql_repo" | sudo tee /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-14
sleep 2
sudo systemctl enable postgresql
sudo systemctl restart postgresql

print_green 'Restoring MongoDB'

wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
echo "$mongodb_repo" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable mongod
sudo systemctl restart mongod
sleep 5
mongorestore --gzip $tmp_dir/meshcentral/mongo


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

NATS_SERVER_VER=$(grep "^NATS_SERVER_VER" /rmm/api/tacticalrmm/tacticalrmm/settings.py | awk -F'[= "]' '{print $5}')
nats_tmp=$(mktemp -d -t nats-XXXXXXXXXX)
wget https://github.com/nats-io/nats-server/releases/download/v${NATS_SERVER_VER}/nats-server-v${NATS_SERVER_VER}-linux-amd64.tar.gz -P ${nats_tmp}
tar -xzf ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-amd64.tar.gz -C ${nats_tmp}
sudo mv ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-amd64/nats-server /usr/local/bin/
sudo chmod +x /usr/local/bin/nats-server
sudo chown ${USER}:${USER} /usr/local/bin/nats-server
rm -rf ${nats_tmp}

print_green 'Restoring MeshCentral'

MESH_VER=$(grep "^MESH_VER" /rmm/api/tacticalrmm/tacticalrmm/settings.py | awk -F'[= "]' '{print $5}')
sudo tar -xzf $tmp_dir/meshcentral/mesh.tar.gz -C /
sudo chown ${USER}:${USER} -R /meshcentral
cd /meshcentral
npm install meshcentral@${MESH_VER}


print_green 'Restoring the backend'

echo 'Optimize for number of processors'
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

cp $tmp_dir/rmm/local_settings.py /rmm/api/tacticalrmm/tacticalrmm/
cp $tmp_dir/rmm/env /rmm/web/.env
gzip -d $tmp_dir/rmm/debug.log.gz
cp $tmp_dir/rmm/django_debug.log /rmm/api/tacticalrmm/tacticalrmm/private/log/

sudo cp /rmm/natsapi/bin/nats-api /usr/local/bin
sudo chown ${USER}:${USER} /usr/local/bin/nats-api
sudo chmod +x /usr/local/bin/nats-api

print_green 'Restoring the database'

pgusername=$(grep -w USER /rmm/api/tacticalrmm/tacticalrmm/local_settings.py | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')
pgpw=$(grep -w PASSWORD /rmm/api/tacticalrmm/tacticalrmm/local_settings.py | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')

sudo -u postgres psql -c "DROP DATABASE IF EXISTS tacticalrmm"
sudo -u postgres psql -c "CREATE DATABASE tacticalrmm"
sudo -u postgres psql -c "CREATE USER ${pgusername} WITH PASSWORD '${pgpw}'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET client_encoding TO 'utf8'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET default_transaction_isolation TO 'read committed'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET timezone TO 'UTC'"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tacticalrmm TO ${pgusername}"

gzip -d $tmp_dir/postgres/*.psql.gz
PGPASSWORD=${pgpw} psql -h localhost -U ${pgusername} -d tacticalrmm -f $tmp_dir/postgres/db*.psql

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" /rmm/api/tacticalrmm/tacticalrmm/settings.py | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" /rmm/api/tacticalrmm/tacticalrmm/settings.py | awk -F'[= "]' '{print $5}')

cd /rmm/api
python3.10 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools==${SETUPTOOLS_VER} wheel==${WHEEL_VER}
pip install --no-cache-dir -r /rmm/api/tacticalrmm/requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py create_natsapi_conf
python manage.py reload_nats
python manage.py post_update_tasks
deactivate

sudo systemctl enable nats.service
sudo systemctl start nats.service

print_green 'Restoring the frontend'

sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config
cd /rmm/web
npm install
npm run build
sudo mkdir -p /var/www/rmm
sudo cp -pvr /rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist


# reset perms
sudo chown ${USER}:${USER} -R /rmm
sudo chown ${USER}:${USER} /var/log/celery
sudo chown ${USER}:${USER} -R /etc/conf.d/
sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config
sudo chown -R $USER:$GROUP /home/${USER}/.cache

print_green 'Enabling Services'
sudo systemctl daemon-reload

for i in celery.service celerybeat.service rmm.service daphne.service nats-api.service nginx
do
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