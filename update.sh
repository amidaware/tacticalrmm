#!/bin/bash

sudo systemctl stop celery
sudo systemctl stop celerybeat
sudo systemctl stop rmm
sudo systemctl stop nginx
cd /home/${USER}/rmm/
git pull
source /home/${USER}/rmm/api/env/bin/activate
cd /home/${USER}/rmm/api/tacticalrmm
pip install -r /home/${USER}/rmm/api/tacticalrmm/requirements.txt
python manage.py makemigrations
python manage.py migrate
deactivate


rm -rf /home/${USER}/rmm/web/node_modules
rm -rf /home/${USER}/rmm/web/dist
cd /home/${USER}/rmm/web
npm install
npm run build
sudo rm -rf /var/www/rmm/dist
sudo cp -pvr /home/${USER}/rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist

sudo systemctl start celery
sudo systemctl start celerybeat
sudo systemctl start rmm
sudo systemctl start nginx
