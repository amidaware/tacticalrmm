#!/bin/bash

SCRIPT_VERSION="2"
SCRIPT_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/update.sh'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
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

for i in celery celerybeat rmm nginx
do
sudo systemctl stop ${i}
done

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
pip install --no-cache-dir setuptools==47.3.2 wheel==0.34.2
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

for i in celery celerybeat rmm nginx
do
sudo systemctl start ${i}
done

sudo systemctl stop meshcentral
cd /meshcentral
rm -rf node_modules/
npm install meshcentral@latest
sudo systemctl start meshcentral
sleep 10

printf >&2 "${GREEN}Update finished!${NC}\n"