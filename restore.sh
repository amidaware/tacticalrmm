#!/bin/bash

SCRIPT_VERSION="2"
SCRIPT_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/restore.sh'

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

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

UBU20=$(grep 20.04 "/etc/"*"release")
if ! [[ $UBU20 ]]; then
  echo -ne "\033[0;31mThis restore script will only work on Ubuntu 20.04\e[0m\n"
  exit 1
fi

if [ $EUID -eq 0 ]; then
  echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
  exit 1
fi

if [ "$LANG" != "en_US.UTF-8" ]; then
  printf >&2 "\n${RED}System locale must be ${GREEN}en_US.UTF-8${RED} not ${YELLOW}${LANG}${NC}\n"
  printf >&2 "${RED}Run the following command and change the default locale to ${GREEN}en_US.UTF-8${NC}\n\n"
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

print_green 'Installing golang'

sudo apt update
sudo apt install -y curl wget
sudo mkdir -p /usr/local/rmmgo
go_tmp=$(mktemp -d -t rmmgo-XXXXXXXXXX)
wget https://golang.org/dl/go1.15.linux-amd64.tar.gz -P ${go_tmp}

tar -xzf ${go_tmp}/go1.15.linux-amd64.tar.gz -C ${go_tmp}

sudo mv ${go_tmp}/go /usr/local/rmmgo/
rm -rf ${go_tmp}

print_green 'Installing NodeJS'

curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash -
sudo apt update
sudo apt install -y gcc g++ make
sudo apt install -y nodejs

print_green 'Restoring Nginx'

sudo apt install -y nginx
sudo systemctl stop nginx
sudo rm -rf /etc/nginx
sudo mkdir /etc/nginx
sudo tar -xzf $tmp_dir/nginx/etc-nginx.tar.gz -C /etc/nginx
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

if [ -f "${tmp_dir}/certs/certs.tar.gz" ]; then
  sudo mkdir /certs
  sudo tar -xzf $tmp_dir/certs/certs.tar.gz -C /certs
else
  sudo rm -rf /etc/letsencrypt
  sudo mkdir /etc/letsencrypt
  sudo tar -xzf $tmp_dir/certs/etc-letsencrypt.tar.gz -C /etc/letsencrypt
fi


print_green 'Restoring celery configs'

sudo mkdir /etc/conf.d
sudo tar -xzf $tmp_dir/confd/etc-confd.tar.gz -C /etc/conf.d
sudo chown ${USER}:${USER} -R /etc/conf.d

print_green 'Restoring systemd services'

sudo cp $tmp_dir/systemd/* /etc/systemd/system/
sudo systemctl daemon-reload

print_green 'Restoring saltapi user'

SALTPW=$(grep SALT_PASSWORD $tmp_dir/rmm/local_settings.py | tr -d " \t" | sed 's/.*=//' | tr -d '"')
sudo adduser --no-create-home --disabled-password --gecos "" saltapi
echo "saltapi:${SALTPW}" | sudo chpasswd

print_green 'Installing python, redis and git'

sudo apt install -y python3.8-venv python3.8-dev python3-pip python3-cherrypy3 python3-setuptools python3-wheel ca-certificates redis git

print_green 'Installing postgresql'

sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-12
sleep 2

print_green 'Restoring the database'

pgusername=$(grep -A 6 DATABASES $tmp_dir/rmm/local_settings.py | grep USER | tr -d " \t" | sed 's/.*://' | tr -d "',")
pgpw=$(grep -A 6 DATABASES $tmp_dir/rmm/local_settings.py | grep PASSWORD | tr -d " \t" | sed 's/.*://' | tr -d "',")

sudo -u postgres psql -c "DROP DATABASE IF EXISTS tacticalrmm"
sudo -u postgres psql -c "CREATE DATABASE tacticalrmm"
sudo -u postgres psql -c "CREATE USER ${pgusername} WITH PASSWORD '${pgpw}'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET client_encoding TO 'utf8'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET default_transaction_isolation TO 'read committed'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET timezone TO 'UTC'"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tacticalrmm TO ${pgusername}"

gzip -d $tmp_dir/postgres/*.psql.gz
PGPASSWORD=${pgpw} psql -h localhost -U ${pgusername} -d tacticalrmm -f $tmp_dir/postgres/db*.psql


print_green 'Restoring MongoDB'

wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | sudo apt-key add -
echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.2 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.2.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable mongod
sudo systemctl restart mongod
sleep 5
mongorestore --gzip $tmp_dir/meshcentral/mongo

print_green 'Restoring MeshCentral'

sudo tar -xzf $tmp_dir/meshcentral/mesh.tar.gz -C /
sudo chown ${USER}:${USER} -R /meshcentral
cd /meshcentral
npm install meshcentral@0.6.62


print_green 'Restoring the backend'

sudo mkdir /rmm
sudo chown ${USER}:${USER} /rmm
sudo mkdir -p /var/log/celery
sudo chown ${USER}:${USER} /var/log/celery
git clone https://github.com/wh1te909/tacticalrmm.git /rmm/

cp $tmp_dir/rmm/local_settings.py /rmm/api/tacticalrmm/tacticalrmm/
cp $tmp_dir/rmm/env /rmm/web/.env
cp $tmp_dir/rmm/app.ini /rmm/api/tacticalrmm/
gzip -d $tmp_dir/rmm/debug.log.gz
cp $tmp_dir/rmm/debug.log /rmm/api/tacticalrmm/tacticalrmm/private/log/
cp $tmp_dir/rmm/mesh*.exe /rmm/api/tacticalrmm/tacticalrmm/private/exe/

/usr/local/rmmgo/go/bin/go get github.com/josephspurrier/goversioninfo/cmd/goversioninfo
sudo cp /rmm/api/tacticalrmm/core/goinstaller/bin/goversioninfo /usr/local/bin/
sudo chown ${USER}:${USER} /usr/local/bin/goversioninfo
sudo chmod +x /usr/local/bin/goversioninfo

cd /rmm/api
python3 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools==49.6.0 wheel==0.35.1
pip install --no-cache-dir -r /rmm/api/tacticalrmm/requirements.txt
python manage.py collectstatic --no-input
deactivate


print_green 'Installing Salt Master'

wget -O - https://repo.saltstack.com/py3/ubuntu/20.04/amd64/latest/SALTSTACK-GPG-KEY.pub | sudo apt-key add -
echo 'deb http://repo.saltstack.com/py3/ubuntu/20.04/amd64/latest focal main' | sudo tee /etc/apt/sources.list.d/saltstack.list

sudo apt update
sudo apt install -y salt-master

print_green 'Waiting 30 seconds for salt to start'
sleep 30

print_green 'Installing Salt API'
sudo apt install -y salt-api

sudo sed -i 's/msgpack_kwargs = {"raw": six.PY2}/msgpack_kwargs = {"raw": six.PY2, "max_buffer_size": 2147483647}/g' /usr/lib/python3/dist-packages/salt/transport/ipc.py

sudo systemctl enable salt-master
sudo systemctl enable salt-api
sudo systemctl restart salt-api
sleep 3

print_green 'Restoring salt keys'

sudo systemctl stop salt-master
sudo systemctl stop salt-api
sudo rm -rf /etc/salt
sudo mkdir /etc/salt
sudo tar -xzf $tmp_dir/salt/etc-salt.tar.gz -C /etc/salt
sudo mkdir -p /srv/salt
sudo tar -xzf $tmp_dir/salt/srv-salt.tar.gz -C /srv/salt
sudo chown ${USER}:${USER} -R /srv/salt/
sudo chown ${USER}:www-data /srv/salt/scripts/userdefined
sudo chmod 750 /srv/salt/scripts/userdefined

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
sudo chown ${USER}:${USER} -R /srv/salt/
sudo chown ${USER}:${USER} -R /etc/conf.d/
sudo chown ${USER}:www-data /srv/salt/scripts/userdefined
sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config
sudo chown -R $USER:$GROUP /home/${USER}/.cache
sudo chmod 750 /srv/salt/scripts/userdefined

print_green 'Enabling Services'
sudo systemctl daemon-reload

for i in celery.service celerybeat.service celery-winupdate.service rmm.service nginx
do
  sudo systemctl enable ${i}
  sudo systemctl restart ${i}
done
sleep 5

print_green 'Starting meshcentral'
sudo systemctl enable meshcentral
sudo systemctl start meshcentral

print_green 'Restarting salt and waiting 30 seconds'
sudo systemctl restart salt-master
sleep 30
sudo systemctl restart salt-api

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n\n"
printf >&2 "${YELLOW}Restore complete!${NC}\n\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"