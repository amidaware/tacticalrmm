#!/bin/bash

for i in celery celery-winupdate celerybeat rmm nginx
do
sudo systemctl stop ${i}
done

cd /home/${USER}/rmm/
git fetch origin develop
git reset --hard FETCH_HEAD
git clean -df
cp /home/${USER}/rmm/_modules/* /srv/salt/_modules/
cp /home/${USER}/rmm/scripts/* /srv/salt/scripts/
rm -rf /home/${USER}/rmm/api/env
cd /home/${USER}/rmm/api
python3.7 -m venv env
source /home/${USER}/rmm/api/env/bin/activate
cd /home/${USER}/rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir --upgrade setuptools wheel
pip install --no-cache-dir -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py delete_tokens
deactivate


rm -rf /home/${USER}/rmm/web/node_modules
rm -rf /home/${USER}/rmm/web/dist
cd /home/${USER}/rmm/web
npm install
npm run build
sudo rm -rf /var/www/rmm/dist
sudo cp -pvr /home/${USER}/rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist

for i in celery celery-winupdate celerybeat rmm nginx
do
sudo systemctl start ${i}
done
