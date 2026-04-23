#!/usr/bin/env bash

SCRIPT_VERSION="33"

export DEBIAN_FRONTEND=noninteractive

set -Eeuo pipefail
PS4='+ ${BASH_SOURCE}:${LINENO}: '

error_handler() {
    local lineno="${1}"
    local exit_code="${2:-$?}"
    print_error "ERROR: backup.sh failed at line ${lineno} with exit code ${exit_code}."
}

trap 'error_handler ${LINENO} $?' ERR

if [[ "${TRACE_BACKUP:-0}" == "1" ]]; then
    set -x
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_green() {
    printf >&2 "${GREEN}%s${NC}\n" "${1}"
}

print_yellow() {
    printf >&2 "${YELLOW}%s${NC}\n" "${1}"
}

print_error() {
    printf >&2 "${RED}%s${NC}\n" "${1}"
}

not_supported() {
    echo -ne "${RED}ERROR: Only Debian 11, Debian 12, Ubuntu 22.04 and Ubuntu 24.04 are supported.${NC}\n"
}

if [ "${EUID}" -eq 0 ]; then
    echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
    exit 1
fi

osname=$(lsb_release -si)
osname=${osname^}
osname=$(echo "${osname}" | tr '[A-Z]' '[a-z]')
relno=$(lsb_release -sr | cut -d. -f1)
fullrelno=$(lsb_release -sr)

if [[ "${osname}" == "debian" ]]; then
    if [[ "${relno}" -ne 11 && "${relno}" -ne 12 ]]; then
        not_supported
        exit 1
    fi
elif [[ "${osname}" == "ubuntu" ]]; then
    if [[ "${fullrelno}" != "22.04" && "${fullrelno}" != "24.04" ]]; then
        not_supported
        exit 1
    fi
else
    not_supported
    exit 1
fi

PRIMARY_GROUP=$(id -gn "${USER}")
local_settings='/rmm/api/tacticalrmm/tacticalrmm/local_settings.py'
RMM_PYTHON='/rmm/api/env/bin/python'

if [[ ! -x "${RMM_PYTHON}" ]]; then
    print_error "ERROR: Python binary ${RMM_PYTHON} not found."
    exit 1
fi

if [[ ! -f "${local_settings}" ]]; then
    print_error "ERROR: Local settings file ${local_settings} not found."
    exit 1
fi

if [[ $* == *--schedule* ]]; then
    if ! sudo -n true 2>/dev/null; then
        echo -ne "${RED}Error: Passwordless sudo is required for scheduling.${NC}\n"
        exit 1
    fi

    (
        crontab -l 2>/dev/null
        echo "0 0 * * * /rmm/backup.sh --auto > /dev/null 2>&1"
    ) | crontab -

    sudo mkdir -p /rmmbackups/daily
    sudo mkdir -p /rmmbackups/weekly
    sudo mkdir -p /rmmbackups/monthly
    sudo chown "${USER}:${PRIMARY_GROUP}" -R /rmmbackups

    print_green "Backups setup to run at midnight and rotate."
    exit 0
fi

if [ ! -d /rmmbackups ]; then
    sudo mkdir -p /rmmbackups
    sudo chown "${USER}:${PRIMARY_GROUP}" /rmmbackups
fi

if [ -d /rmmbackups ]; then
    sudo chown "${USER}:${PRIMARY_GROUP}" -R /rmmbackups
fi

if [ -d /meshcentral/meshcentral-backup ]; then
    rm -rf /meshcentral/meshcentral-backup/*
fi

if [ -d /meshcentral/meshcentral-backups ]; then
    rm -rf /meshcentral/meshcentral-backups/*
fi

if [ -d /meshcentral/meshcentral-coredumps ]; then
    rm -f /meshcentral/meshcentral-coredumps/*
fi

dt_now=$(date '+%Y_%m_%d__%H_%M_%S')
tmp_dir=$(mktemp -d -t tacticalrmm-XXXXXXXXXXXXXXXXXXXXX)
sysd="/etc/systemd/system"

mkdir -p "${tmp_dir}/meshcentral/mongo"
mkdir -p "${tmp_dir}/postgres"
mkdir -p "${tmp_dir}/certs"
mkdir -p "${tmp_dir}/nginx"
mkdir -p "${tmp_dir}/systemd"
mkdir -p "${tmp_dir}/rmm"
mkdir -p "${tmp_dir}/confd"
mkdir -p "${tmp_dir}/opt"

POSTGRES_USER=$("${RMM_PYTHON}" /rmm/api/tacticalrmm/manage.py get_config dbuser)
POSTGRES_PW=$("${RMM_PYTHON}" /rmm/api/tacticalrmm/manage.py get_config dbpw)

pg_dump --no-privileges --no-owner --dbname=postgresql://"${POSTGRES_USER}":"${POSTGRES_PW}"@localhost:5432/tacticalrmm | gzip -9 >"${tmp_dir}/postgres/db-${dt_now}.psql.gz"

node /meshcentral/node_modules/meshcentral --dbexport # for import to postgres

if grep -q postgres "/meshcentral/meshcentral-data/config.json"; then
    if ! command -v jq >/dev/null 2>&1; then
        sudo apt-get install -y jq >/dev/null
    fi
    MESH_POSTGRES_USER=$(jq '.settings.postgres.user' /meshcentral/meshcentral-data/config.json -r)
    MESH_POSTGRES_PW=$(jq '.settings.postgres.password' /meshcentral/meshcentral-data/config.json -r)
    pg_dump --no-privileges --no-owner --dbname=postgresql://"${MESH_POSTGRES_USER}":"${MESH_POSTGRES_PW}"@localhost:5432/meshcentral | gzip -9 >"${tmp_dir}/postgres/mesh-db-${dt_now}.psql.gz"
else
    mongodump --gzip --out="${tmp_dir}/meshcentral/mongo"
fi

tar -czvf "${tmp_dir}/meshcentral/mesh.tar.gz" --exclude=/meshcentral/node_modules --exclude=/meshcentral/meshcentral-recordings /meshcentral

if [ -d /etc/letsencrypt ]; then
    sudo tar -czvf "${tmp_dir}/certs/etc-letsencrypt.tar.gz" -C /etc/letsencrypt .
fi

if [ -d /opt/tactical ]; then
    sudo tar -czvf "${tmp_dir}/opt/opt-tactical.tar.gz" -C /opt/tactical .
fi

if grep -q CERT_FILE "${local_settings}"; then
    mkdir -p "${tmp_dir}/certs/custom"
    CERT_FILE=$(grep "^CERT_FILE" "${local_settings}" | awk -F'[= "]' '{print $5}')
    KEY_FILE=$(grep "^KEY_FILE" "${local_settings}" | awk -F'[= "]' '{print $5}')
    cp -p "${CERT_FILE}" "${tmp_dir}/certs/custom/cert"
    cp -p "${KEY_FILE}" "${tmp_dir}/certs/custom/key"
elif grep -q TRMM_INSECURE "${local_settings}"; then
    mkdir -p "${tmp_dir}/certs/selfsigned"
    certdir='/etc/ssl/tactical'
    cp -p "${certdir}/key.pem" "${tmp_dir}/certs/selfsigned/"
    cp -p "${certdir}/cert.pem" "${tmp_dir}/certs/selfsigned/"
fi

for i in rmm frontend meshcentral; do
    sudo cp "/etc/nginx/sites-available/${i}.conf" "${tmp_dir}/nginx/"
done

sudo tar -czvf "${tmp_dir}/confd/etc-confd.tar.gz" -C /etc/conf.d .

sudo cp "${sysd}/rmm.service" "${sysd}/celery.service" "${sysd}/celerybeat.service" "${sysd}/meshcentral.service" "${sysd}/nats.service" "${sysd}/daphne.service" "${sysd}/nats-api.service" "${tmp_dir}/systemd/"

cp "${local_settings}" "${tmp_dir}/rmm/"

if [[ $* == *--auto* ]]; then
    month_day=$(date +"%d")
    week_day=$(date +"%u")

    if [ "${month_day}" -eq 10 ]; then
        tar -cf "/rmmbackups/monthly/rmm-backup-${dt_now}.tar" -C "${tmp_dir}" .
    else
        if [ "${week_day}" -eq 5 ]; then
            tar -cf "/rmmbackups/weekly/rmm-backup-${dt_now}.tar" -C "${tmp_dir}" .
        else
            tar -cf "/rmmbackups/daily/rmm-backup-${dt_now}.tar" -C "${tmp_dir}" .
        fi
    fi

    rm -rf "${tmp_dir}"

    find /rmmbackups/daily/ -type f -mtime +14 -name '*.tar' -execdir rm -- '{}' \;
    find /rmmbackups/weekly/ -type f -mtime +60 -name '*.tar' -execdir rm -- '{}' \;
    find /rmmbackups/monthly/ -type f -mtime +380 -name '*.tar' -execdir rm -- '{}' \;
    echo -ne "${GREEN}Backup Completed${NC}\n"
    exit
else
    tar -cf "/rmmbackups/rmm-backup-${dt_now}.tar" -C "${tmp_dir}" .
    rm -rf "${tmp_dir}"

    echo -ne "${GREEN}Backup saved to /rmmbackups/rmm-backup-${dt_now}.tar${NC}\n"
fi
