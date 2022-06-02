#!/bin/bash

### Script info
SCRIPT_VERSION="19"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/backup.sh'
THIS_SCRIPT=$(readlink -f "$0")

### Import functions
. $PWD/bashfunctions.cfg

### Set colors
setColors;

### Check for new functions version, only include script name as variable
checkCfgVer "$THIS_SCRIPT";

### Check for new script version, pass script version, url, and script name variables in that order
checkScriptVer "$SCRIPT_VERSION" "$SCRIPT_URL" "$THIS_SCRIPT";

### Check if root
checkRoot;

### Pull Postgres info
POSTGRES_USER=$(grep -w USER /rmm/api/tacticalrmm/tacticalrmm/local_settings.py | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')
POSTGRES_PW=$(grep -w PASSWORD /rmm/api/tacticalrmm/tacticalrmm/local_settings.py | sed 's/^.*: //' | sed 's/.//' | sed -r 's/.{2}$//')


if [ ! -d /rmmbackups ]; then
    sudo mkdir /rmmbackups
    sudo chown ${USER}:${USER} /rmmbackups
fi

if [ -d /meshcentral/meshcentral-backup ]; then
    rm -rf /meshcentral/meshcentral-backup/*
fi

if [ -d /meshcentral/meshcentral-coredumps ]; then
    rm -f /meshcentral/meshcentral-coredumps/*
fi

dt_now=$(date '+%Y_%m_%d__%H_%M_%S')
tmp_dir=$(mktemp -d -t tacticalrmm-XXXXXXXXXXXXXXXXXXXXX)
sysd="/etc/systemd/system"

mkdir -p ${tmp_dir}/meshcentral/mongo
mkdir ${tmp_dir}/postgres
mkdir ${tmp_dir}/certs
mkdir ${tmp_dir}/nginx
mkdir ${tmp_dir}/systemd
mkdir ${tmp_dir}/rmm
mkdir ${tmp_dir}/confd

### Dump Postgres database
pg_dump --dbname=postgresql://"${POSTGRES_USER}":"${POSTGRES_PW}"@127.0.0.1:5432/tacticalrmm | gzip -9 > ${tmp_dir}/postgres/db-${dt_now}.psql.gz

tar -czvf ${tmp_dir}/meshcentral/mesh.tar.gz --exclude=/meshcentral/node_modules /meshcentral
mongodump --gzip --out=${tmp_dir}/meshcentral/mongo

sudo tar -czvf ${tmp_dir}/certs/etc-letsencrypt.tar.gz -C /etc/letsencrypt .

sudo tar -czvf ${tmp_dir}/nginx/etc-nginx.tar.gz -C /etc/nginx .

sudo tar -czvf ${tmp_dir}/confd/etc-confd.tar.gz -C /etc/conf.d .

sudo cp ${sysd}/rmm.service ${sysd}/celery.service ${sysd}/celerybeat.service ${sysd}/meshcentral.service ${sysd}/nats.service ${sysd}/daphne.service ${tmp_dir}/systemd/
if [ -f "${sysd}/nats-api.service" ]; then
    sudo cp ${sysd}/nats-api.service ${tmp_dir}/systemd/
fi

cat /rmm/api/tacticalrmm/tacticalrmm/private/log/django_debug.log | gzip -9 > ${tmp_dir}/rmm/debug.log.gz
cp /rmm/api/tacticalrmm/tacticalrmm/local_settings.py ${tmp_dir}/rmm/

tar -cf /rmmbackups/rmm-backup-${dt_now}.tar -C ${tmp_dir} .

rm -rf ${tmp_dir}

echo -ne "${GREEN}Backup saved to /rmmbackups/rmm-backup-${dt_now}.tar${NC}\n"
