#!/bin/bash

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
pip install --no-cache-dir --upgrade setuptools wheel
pip install --no-cache-dir -r requirements.txt
python manage.py migrate
python manage.py delete_tokens
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