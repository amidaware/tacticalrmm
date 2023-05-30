#!/usr/bin/env bash

SCRIPT_VERSION="24"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

if [ $EUID -eq 0 ]; then
    echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
    exit 1
fi

if [[ $* == *--schedule* ]]; then
    (
        crontab -l 2>/dev/null
        echo "0 0 * * * /rmm/backup.sh --auto"
    ) | crontab -
    
     if [ ! -d /rmmbackups ]; then
        sudo mkdir /rmmbackups
    fi
    
    if [ ! -d /rmmbackups/daily ]; then
        sudo mkdir /rmmbackups/daily
    fi

    if [ ! -d /rmmbackups/weekly ]; then
        sudo mkdir /rmmbackups/weekly
    fi

    if [ ! -d /rmmbackups/monthly ]; then
        sudo mkdir /rmmbackups/monthly
    fi
    sudo chown ${USER}:${USER} -R /rmmbackups
    
    printf >&2 "${GREEN}Backups setup to run at midnight and rotate.${NC}\n"
    exit 0
fi

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

POSTGRES_USER=$(/rmm/api/env/bin/python /rmm/api/tacticalrmm/manage.py get_config dbuser)
POSTGRES_PW=$(/rmm/api/env/bin/python /rmm/api/tacticalrmm/manage.py get_config dbpw)

pg_dump --dbname=postgresql://"${POSTGRES_USER}":"${POSTGRES_PW}"@127.0.0.1:5432/tacticalrmm | gzip -9 >${tmp_dir}/postgres/db-${dt_now}.psql.gz

tar -czvf ${tmp_dir}/meshcentral/mesh.tar.gz --exclude=/meshcentral/node_modules /meshcentral

if grep -q postgres "/meshcentral/meshcentral-data/config.json"; then
    if ! which jq >/dev/null; then
        sudo apt-get install -y jq >null
    fi
    MESH_POSTGRES_USER=$(jq '.settings.postgres.user' /meshcentral/meshcentral-data/config.json -r)
    MESH_POSTGRES_PW=$(jq '.settings.postgres.password' /meshcentral/meshcentral-data/config.json -r)
    pg_dump --dbname=postgresql://"${MESH_POSTGRES_USER}":"${MESH_POSTGRES_PW}"@127.0.0.1:5432/meshcentral | gzip -9 >${tmp_dir}/postgres/mesh-db-${dt_now}.psql.gz
else
    mongodump --gzip --out=${tmp_dir}/meshcentral/mongo
fi

sudo tar -czvf ${tmp_dir}/certs/etc-letsencrypt.tar.gz -C /etc/letsencrypt .

for i in rmm frontend meshcentral; do
    sudo cp /etc/nginx/sites-available/${i}.conf ${tmp_dir}/nginx/
done

sudo tar -czvf ${tmp_dir}/confd/etc-confd.tar.gz -C /etc/conf.d .

sudo cp ${sysd}/rmm.service ${sysd}/celery.service ${sysd}/celerybeat.service ${sysd}/meshcentral.service ${sysd}/nats.service ${sysd}/daphne.service ${sysd}/nats-api.service ${tmp_dir}/systemd/

cat /rmm/api/tacticalrmm/tacticalrmm/private/log/django_debug.log | gzip -9 >${tmp_dir}/rmm/debug.log.gz
cp /rmm/api/tacticalrmm/tacticalrmm/local_settings.py ${tmp_dir}/rmm/

if [[ $* == *--auto* ]]; then

    month_day=$(date +"%d")
    week_day=$(date +"%u")

    if [ "$month_day" -eq 10 ]; then
        tar -cf /rmmbackups/monthly/rmm-backup-${dt_now}.tar -C ${tmp_dir} .
    else
        if [ "$week_day" -eq 5 ]; then
            tar -cf /rmmbackups/weekly/rmm-backup-${dt_now}.tar -C ${tmp_dir} .
        else
            tar -cf /rmmbackups/daily/rmm-backup-${dt_now}.tar -C ${tmp_dir} .
        fi
    fi

    rm -rf ${tmp_dir}

    find /rmmbackups/daily/ -maxdepth 1 -mtime +14 -type d -exec rm -rv {} \;
    find /rmmbackups/weekly/ -maxdepth 1 -mtime +60 -type d -exec rm -rv {} \;
    find /rmmbackups/monthly/ -maxdepth 1 -mtime +380 -type d -exec rm -rv {} \;
    echo -ne "${GREEN}Backup Completed${NC}\n"
    exit

else
    tar -cf /rmmbackups/rmm-backup-${dt_now}.tar -C ${tmp_dir} .

    echo -ne "${GREEN}Backup saved to /rmmbackups/rmm-backup-${dt_now}.tar${NC}\n"
fi
