#!/bin/bash

if [ $EUID -eq 0 ]; then
  echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
  exit 1
fi

GREEN='\033[0;32m'
NC='\033[0m'

if [ ! -d /rmmbackups ]; then
    sudo mkdir /rmmbackups
    sudo chown ${USER}:${USER} /rmmbackups
fi

POSTGRES_USER="changeme"
POSTGRES_PW="hunter2"

dt_now=$(date '+%Y_%m_%d__%H_%M_%S')
tmp_dir=$(mktemp -d -t tacticalrmm-XXXXXXXXXXXXXXXXXXXXX)
sysd="/etc/systemd/system"

mkdir -p ${tmp_dir}/meshcentral/mongo
mkdir ${tmp_dir}/postgres
mkdir ${tmp_dir}/salt
mkdir ${tmp_dir}/certs
mkdir ${tmp_dir}/nginx
mkdir ${tmp_dir}/systemd
mkdir ${tmp_dir}/rmm
mkdir ${tmp_dir}/confd


pg_dump --dbname=postgresql://${POSTGRES_USER}:${POSTGRES_PW}@127.0.0.1:5432/tacticalrmm | gzip -9 > ${tmp_dir}/postgres/db-${dt_now}.psql.gz

tar -czvf ${tmp_dir}/meshcentral/mesh.tar.gz --exclude=/meshcentral/node_modules /meshcentral
mongodump --gzip --out=${tmp_dir}/meshcentral/mongo

sudo tar -czvf ${tmp_dir}/salt/etc-salt.tar.gz -C /etc/salt .
tar -czvf ${tmp_dir}/salt/srv-salt.tar.gz -C /srv/salt .

sudo tar -czvf ${tmp_dir}/certs/etc-letsencrypt.tar.gz -C /etc/letsencrypt .
sudo tar -czvf ${tmp_dir}/certs/certs.tar.gz -C /certs .

sudo tar -czvf ${tmp_dir}/nginx/etc-nginx.tar.gz -C /etc/nginx .

sudo tar -czvf ${tmp_dir}/confd/etc-confd.tar.gz -C /etc/conf.d .

sudo cp ${sysd}/rmm.service ${sysd}/celery.service ${sysd}/celerybeat.service ${sysd}/celery-winupdate.service ${sysd}/meshcentral.service ${tmp_dir}/systemd/

cat /rmm/api/tacticalrmm/tacticalrmm/private/log/debug.log | gzip -9 > ${tmp_dir}/rmm/debug.log.gz
cp /rmm/api/tacticalrmm/tacticalrmm/local_settings.py /rmm/api/tacticalrmm/app.ini ${tmp_dir}/rmm/
cp /rmm/web/.env ${tmp_dir}/rmm/env
cp /rmm/api/tacticalrmm/tacticalrmm/private/exe/mesh*.exe ${tmp_dir}/rmm/

tar -cf /rmmbackups/rmm-backup-${dt_now}.tar -C ${tmp_dir} .

rm -rf ${tmp_dir}

echo -ne "${GREEN}Backup saved to /rmmbackups/rmm-backup-${dt_now}.tar${NC}\n"