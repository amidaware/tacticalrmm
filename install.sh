#!/bin/bash

if [ $EUID -eq 0 ]; then
  echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
  exit 1
fi


DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 50 | head -n 1)
SALTPW=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)
ADMINURL=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 30 | head -n 1)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cls() {
  printf "\033c"
}

print_green() {
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
  printf >&2 "${GREEN}${1}${NC}\n"
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
}

cls


echo -ne "${YELLOW}Create a username for the postgres database${NC}: "
read pgusername
echo -ne "${YELLOW}Create a password for the postgres database${NC}: "
read pgpw
echo -ne "${YELLOW}Enter the backend API domain for the rmm${NC}: "
read rmmdomain
echo -ne "${YELLOW}Enter the frontend  domain for the rmm${NC}: "
read frontenddomain
echo -ne "${YELLOW}Enter the domain for meshcentral${NC}: "
read meshdomain
echo -ne "${YELLOW}Enter your username for meshcentral${NC}: "
read meshusername
echo -ne "${YELLOW}Enter your email address for let's encrypt renewal notifications${NC}: "
read letsemail


print_green 'Creating saltapi user'

sudo adduser --no-create-home --disabled-password --gecos "" saltapi
echo "saltapi:${SALTPW}" | sudo chpasswd


print_green 'Installing Nginx'

sudo add-apt-repository -y ppa:nginx/stable
sudo apt update
sudo apt install -y nginx

print_green 'Installing NodeJS'

sudo apt install -y curl wget

curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash -
sudo apt update
sudo apt install -y gcc g++ make
sudo apt install -y nodejs

print_green 'Installing MongoDB'

wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | sudo apt-key add -
echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.2 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.2.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable mongod
sudo systemctl restart mongod

print_green 'Installing MeshCentral'

sudo mkdir -p /meshcentral/meshcentral-data
cd /meshcentral
sudo npm install meshcentral
cd /home/${USER}
sudo chown ${USER}:${USER} -R /meshcentral

meshcfg="$(cat << EOF
{
  "settings": {
    "Cert": "${meshdomain}",
    "MongoDb": "mongodb://127.0.0.1:27017",
    "MongoDbName": "meshcentral",
    "WANonly": true,
    "Minify": 1,
    "Port": 4430,
    "AliasPort": 443,
    "RedirPort": 800,
    "AllowLoginToken": true,
    "AllowFraming": true,
    "_AgentPing": 60,
    "AgentPong": 300,
    "AllowHighQualityDesktop": true,
    "TlsOffload": "127.0.0.1",
    "MaxInvalidLogin": { "time": 5, "count": 5, "coolofftime": 30 }
  },
  "domains": {
    "": {
      "Title": "Dev RMM",
      "Title2": "DevRMM",
      "NewAccounts": false,
      "Footer": "<a href='https://twitter.com/mytwitter'>Twitter</a>",
      "CertUrl": "https://${meshdomain}:443/",
      "GeoLocation": true,
      "httpheaders": {
        "Strict-Transport-Security": "max-age=360000",
        "_x-frame-options": "sameorigin",
        "Content-Security-Policy": "default-src 'none'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-src 'self'; media-src 'self'"
      }
    }
  }
}
EOF
)"
echo "${meshcfg}" > /meshcentral/meshcentral-data/config.json

print_green 'Installing python, redis and git'

sudo apt install -y software-properties-common
sudo apt install -y python3.7 python3.7-venv python3.7-dev python3-pip python3-dev python3-venv python3-setuptools ca-certificates redis git python3-cherrypy3

print_green 'Installing postgresql'

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-11

print_green 'Creating database for the rmm'

sudo -u postgres psql -c "CREATE DATABASE tacticalrmm"
sudo -u postgres psql -c "CREATE USER ${pgusername} WITH PASSWORD '${pgpw}'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET client_encoding TO 'utf8'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET default_transaction_isolation TO 'read committed'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET timezone TO 'UTC'"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tacticalrmm TO ${pgusername}"


sudo usermod -a -G www-data ${USER}
sudo chmod 710 /home/${USER}
sudo chown ${USER}:www-data /home/${USER}

mkdir -p /home/${USER}/rmm
sudo mkdir -p /var/log/celery
sudo chown ${USER}:${USER} /var/log/celery
git clone https://github.com/wh1te909/tacticalrmm.git /home/${USER}/rmm/
sudo chown ${USER}:www-data -R /home/${USER}/rmm/api/tacticalrmm

localvars="$(cat << EOF
SECRET_KEY = "${DJANGO_SEKRET}"

DEBUG = False

ALLOWED_HOSTS = ['${rmmdomain}']

ADMIN_URL = "${ADMINURL}/"

CORS_ORIGIN_WHITELIST = [
    "https://${frontenddomain}"
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tacticalrmm',
        'USER': '${pgusername}',
        'PASSWORD': '${pgpw}',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

REST_FRAMEWORK = {
    'DATETIME_FORMAT': "%b-%d-%Y - %H:%M",

    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'knox.auth.TokenAuthentication',
    ),
}

if not DEBUG:
    REST_FRAMEWORK.update({
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    })

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'example@gmail.com'
EMAIL_HOST_PASSWORD = 'yourgmailpassword'
EMAIL_PORT = 587
EMAIL_ALERT_RECIPIENTS = ["jsmith@example.com",]

SALT_USERNAME = "saltapi"
SALT_PASSWORD = "${SALTPW}"
MESH_USERNAME = "${meshusername}"
MESH_SITE = "https://${meshdomain}"
EOF
)"
echo "${localvars}" > /home/${USER}/rmm/api/tacticalrmm/tacticalrmm/local_settings.py

print_green 'Installing the backend'

cd /home/${USER}/rmm/api
python3.7 -m venv env
source /home/${USER}/rmm/api/env/bin/activate
cd /home/${USER}/rmm/api/tacticalrmm
pip install --upgrade pip
pip install -r /home/${USER}/rmm/api/tacticalrmm/requirements.txt
python manage.py migrate
python manage.py collectstatic
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
printf >&2 "${YELLOW}Please create your login for the RMM website and django admin${NC}\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
echo -ne "Username: "
read djangousername
python manage.py createsuperuser --username ${djangousername} --email ${letsemail}
RANDBASE=$(python manage.py generate_totp)
cls
python manage.py generate_barcode ${RANDBASE} ${djangousername}
deactivate
read -n 1 -s -r -p "Press any key to continue..."

totp="$(cat << EOF
TWO_FACTOR_OTP = "${RANDBASE}"
EOF
)"
echo "${totp}" | tee --append /home/${USER}/rmm/api/tacticalrmm/tacticalrmm/local_settings.py > /dev/null

uwsgini="$(cat << EOF
[uwsgi]

logto = /home/${USER}/rmm/api/tacticalrmm/log/uwsgi.log
chdir = /home/${USER}/rmm/api/tacticalrmm
module = tacticalrmm.wsgi
home = /home/${USER}/rmm/api/env
master = true
processes = 6
threads = 6
enable-threads = True
socket = /home/${USER}/rmm/api/tacticalrmm/tacticalrmm.sock
harakiri = 300
chmod-socket = 660
# clear environment on exit
vacuum = true
die-on-term = true
EOF
)"
echo "${uwsgini}" > /home/${USER}/rmm/api/tacticalrmm/app.ini


rmmservice="$(cat << EOF
[Unit]
Description=tacticalrmm uwsgi daemon
After=network.target

[Service]
User=${USER}
Group=www-data
WorkingDirectory=/home/${USER}/rmm/api/tacticalrmm
Environment="PATH=/home/${USER}/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/${USER}/rmm/api/env/bin/uwsgi --ini app.ini

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${rmmservice}" | sudo tee /etc/systemd/system/rmm.service > /dev/null


nginxrmm="$(cat << EOF
server_tokens off;

upstream tacticalrmm {
    server unix:////home/${USER}/rmm/api/tacticalrmm/tacticalrmm.sock;
}

server {
    listen 80;
    server_name ${rmmdomain};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${rmmdomain};
    client_max_body_size 300M;
    access_log /home/${USER}/rmm/api/tacticalrmm/log/rmm-access.log;
    error_log /home/${USER}/rmm/api/tacticalrmm/log/rmm-error.log;
    ssl_certificate /etc/letsencrypt/live/${rmmdomain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${rmmdomain}/privkey.pem;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';

    location /static/ {
        root /home/${USER}/rmm/api/tacticalrmm;
    }

    location /protected/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /home/${USER}/rmm/api/tacticalrmm/tacticalrmm/downloads/;
    }

    location /protectedlogs/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /home/steam/rmm/api/tacticalrmm/log/;
    }


    location / {
        uwsgi_pass  tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 9999s;
        uwsgi_ignore_client_abort on;
    }
}
EOF
)"
echo "${nginxrmm}" | sudo tee /etc/nginx/sites-available/rmm.conf > /dev/null


nginxmesh="$(cat << EOF
server {
  listen 80;
  server_name ${meshdomain};
  location / {
     proxy_pass http://127.0.0.1:800;
     proxy_http_version 1.1;
     proxy_set_header X-Forwarded-Host \$host:\$server_port;
     proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
     proxy_set_header X-Forwarded-Proto \$scheme;
  }

}

server {

    listen 443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${meshdomain};
    ssl_certificate /etc/letsencrypt/live/${meshdomain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${meshdomain}/privkey.pem;
    ssl_session_cache shared:WEBSSL:10m;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:4430/;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Host \$host:\$server_port;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
)"
echo "${nginxmesh}" | sudo tee /etc/nginx/sites-available/meshcentral.conf > /dev/null

sudo ln -s /etc/nginx/sites-available/rmm.conf /etc/nginx/sites-enabled/rmm.conf
sudo ln -s /etc/nginx/sites-available/meshcentral.conf /etc/nginx/sites-enabled/meshcentral.conf

print_green 'Installing Salt Master'

wget -O - https://repo.saltstack.com/py3/ubuntu/18.04/amd64/latest/SALTSTACK-GPG-KEY.pub | sudo apt-key add -
echo 'deb http://repo.saltstack.com/py3/ubuntu/18.04/amd64/latest bionic main' | sudo tee /etc/apt/sources.list.d/saltstack.list
sudo apt update
sudo apt install -y salt-master

saltvars="$(cat << EOF
timeout: 60
gather_job_timeout: 30
max_event_size: 30485760
external_auth:
  pam:
    saltapi:
      - .*
      - '@runner'
      - '@wheel'
      - '@jobs'

rest_cherrypy:
  port: 8123
  disable_ssl: True
  max_request_body_size: 30485760

EOF
)"
echo "${saltvars}" | sudo tee --append /etc/salt/master > /dev/null

print_green 'Waiting 30 seconds for salt to start'
sleep 30 # wait for salt to start

print_green 'Installing Salt API'
sudo apt install -y salt-api

sudo mkdir /etc/conf.d

celeryservice="$(cat << EOF
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/home/${USER}/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} multi start \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} \${CELERYD_OPTS}'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \${CELERYD_NODES} --pidfile=\${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c '\${CELERY_BIN} multi restart \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} \${CELERYD_OPTS}'

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celeryservice}" | sudo tee /etc/systemd/system/celery.service > /dev/null

celerywinupdatesvc="$(cat << EOF
[Unit]
Description=Celery Win Update Service
After=network.target

[Service]
Type=forking
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery-winupdate.conf
WorkingDirectory=/home/${USER}/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} multi start \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} -Q wupdate \${CELERYD_OPTS}'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \${CELERYD_NODES} --pidfile=\${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c '\${CELERY_BIN} multi restart \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} -Q wupdate \${CELERYD_OPTS}'

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerywinupdatesvc}" | sudo tee /etc/systemd/system/celery-winupdate.service > /dev/null

celeryconf="$(cat << EOF
CELERYD_NODES="w1"

CELERY_BIN="/home/${USER}/rmm/api/env/bin/celery"

CELERY_APP="tacticalrmm"

CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=2900 --autoscale=50,5"

CELERYD_PID_FILE="/home/${USER}/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="INFO"

CELERYBEAT_PID_FILE="/home/${USER}/rmm/api/tacticalrmm/beat.pid"
CELERYBEAT_LOG_FILE="/var/log/celery/beat.log"
EOF
)"
echo "${celeryconf}" | sudo tee /etc/conf.d/celery.conf > /dev/null

celerywinupdate="$(cat << EOF
CELERYD_NODES="w2"

CELERY_BIN="/home/${USER}/rmm/api/env/bin/celery"

CELERY_APP="tacticalrmm"

CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=4000 --autoscale=15,1"

CELERYD_PID_FILE="/home/${USER}/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="INFO"
EOF
)"
echo "${celerywinupdate}" | sudo tee /etc/conf.d/celery-winupdate.conf > /dev/null


celerybeatservice="$(cat << EOF
[Unit]
Description=Celery Beat Service
After=network.target

[Service]
Type=simple
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/home/${USER}/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} beat -A \${CELERY_APP} --pidfile=\${CELERYBEAT_PID_FILE} --logfile=\${CELERYBEAT_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL}'

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerybeatservice}" | sudo tee /etc/systemd/system/celerybeat.service > /dev/null

sudo mkdir -p /srv/salt
sudo cp -r /home/${USER}/rmm/_modules /srv/salt/
sudo cp -r /home/${USER}/rmm/scripts /srv/salt/
sudo chown root:root -R /srv/salt/
sudo chown root:${USER} -R /srv/salt/scripts/
sudo chmod 770 -R /srv/salt/scripts/

meshservice="$(cat << EOF
[Unit]
Description=MeshCentral Server
After=network.target
After=nginx.service
[Service]
Type=simple
LimitNOFILE=1000000
ExecStart=/usr/bin/node /meshcentral/node_modules/meshcentral
Environment=NODE_ENV=production
WorkingDirectory=/meshcentral
User=root
Group=root
Restart=always
# Restart service after 10 seconds if node service crashes
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF
)"
echo "${meshservice}" | sudo tee /etc/systemd/system/meshcentral.service > /dev/null

sudo systemctl daemon-reload


sudo systemctl enable salt-master
sudo systemctl enable salt-api

sudo systemctl restart salt-api

print_green 'Installing certbot'

sudo add-apt-repository -y ppa:certbot/certbot
sudo apt install -y certbot
sudo ufw allow http
sudo ufw allow https
sudo systemctl stop nginx

print_green 'Getting https certs'

sudo certbot certonly --standalone --agree-tos -m ${letsemail} --no-eff-email -d ${meshdomain}
sudo certbot certonly --standalone --agree-tos -m ${letsemail} --no-eff-email -d ${rmmdomain}
sudo certbot certonly --standalone --agree-tos -m ${letsemail} --no-eff-email -d ${frontenddomain}

sudo ufw delete allow http
sudo ufw delete allow https

sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config

vueconf="$(cat << EOF
VUE_APP_PROD_URL = "https://${rmmdomain}"
VUE_APP_DEV_URL = "http://localhost:8000"
EOF
)"
echo "${vueconf}" | tee /home/${USER}/rmm/web/.env.local > /dev/null

print_green 'Installing the frontend'

cd /home/${USER}/rmm/web
npm install
npm run build
sudo mkdir -p /var/www/rmm
sudo cp -pvr /home/${USER}/rmm/web/dist /var/www/rmm/
sudo chown www-data:www-data -R /var/www/rmm/dist

nginxfrontend="$(cat << EOF
server {
    server_name ${frontenddomain};
    charset utf-8;
    location / {
        root /var/www/rmm/dist;
        try_files \$uri \$uri/ /index.html;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
    }
    error_log  /var/log/nginx/frontend-error.log;
    access_log /var/log/nginx/frontend-access.log;

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/${frontenddomain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${frontenddomain}/privkey.pem;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
}

server {
    if (\$host = ${frontenddomain}) {
        return 301 https://\$host\$request_uri;
    }

    listen      80;
    server_name ${frontenddomain};
    return 404;
}
EOF
)"
echo "${nginxfrontend}" | sudo tee /etc/nginx/sites-available/frontend.conf > /dev/null

sudo ln -s /etc/nginx/sites-available/frontend.conf /etc/nginx/sites-enabled/frontend.conf


print_green 'Restarting Services'

for i in nginx celery.service celery-winupdate.service celerybeat.service rmm.service
do
  sudo systemctl enable ${i}
  sudo systemctl restart ${i}
done
sleep 5
sudo systemctl enable meshcentral

print_green 'Restarting meshcentral and waiting for it to install plugins'

sudo systemctl restart meshcentral

sleep 30

print_green 'Restarting salt-master and waiting 30 seconds'
sudo systemctl restart salt-master
sleep 30
sudo systemctl restart salt-api

printf >&2 "${BLUE}%0.s*${NC}" {1..80}
printf >&2 "\n\n"
printf >&2 "${BLUE}Installation complete!${NC}\n\n"
printf >&2 "${BLUE}Please refer to the github README for next steps${NC}\n"
printf >&2 "\n\n"
printf >&2 "${BLUE}%0.s*${NC}" {1..80}
printf >&2 "\n"
