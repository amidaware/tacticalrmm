#!/bin/bash

SCRIPT_VERSION="7"
SCRIPT_URL='https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/install.sh'

TMP_FILE=$(mktemp -p "" "rmminstall_XXXXXXXXXX")
curl -s -L "${SCRIPT_URL}" > ${TMP_FILE}
NEW_VER=$(grep "^SCRIPT_VERSION" "$TMP_FILE" | awk -F'[="]' '{print $3}')

if [ "${SCRIPT_VERSION}" \< "${NEW_VER}" ]; then
    printf >&2 "${YELLOW}A newer version of this installer script is available.${NC}\n"
    printf >&2 "${YELLOW}Please download the latest version from ${GREEN}${SCRIPT_URL}${YELLOW} and re-run.${NC}\n"
    rm -f $TMP_FILE
    exit 1
fi

rm -f $TMP_FILE

UBU20=$(grep 20.04 "/etc/"*"release")
if ! [[ $UBU20 ]]; then
  echo -ne "\033[0;31mThis script will only work on Ubuntu 20.04\e[0m\n"
  exit 1
fi

if [ $EUID -eq 0 ]; then
  echo -ne "\033[0;31mDo NOT run this script as root. Exiting.\e[0m\n"
  exit 1
fi

DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 80 | head -n 1)
SALTPW=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)
ADMINURL=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 70 | head -n 1)
MESHPASSWD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 25 | head -n 1)
pgusername=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
pgpw=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)

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

while [[ $rmmdomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain for the backend (e.g. api.example.com)${NC}: "
read rmmdomain
done

while [[ $frontenddomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain for the frontend (e.g. rmm.example.com)${NC}: "
read frontenddomain
done

while [[ $meshdomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain for meshcentral (e.g. mesh.example.com)${NC}: "
read meshdomain
done

echo -ne "${YELLOW}Enter the root domain for LetsEncrypt (e.g. example.com or example.co.uk)${NC}: "
read rootdomain

# if server is behind NAT we need to add the 3 subdomains to the host file 
# so that nginx can properly route between the frontend, backend and meshcentral
# EDIT 8-29-2020
# running this even if server is __not__ behind NAT just to make DNS resolving faster
# this also allows the install script to properly finish even if DNS has not fully propagated
CHECK_HOSTS=$(grep 127.0.1.1 /etc/hosts | grep "$rmmdomain" | grep "$meshdomain" | grep "$frontenddomain")

if ! [[ $CHECK_HOSTS ]]; then
    echo -ne "${GREEN}We need to append your 3 subdomains to the line starting with 127.0.1.1 in your hosts file.${NC}\n"
    until [[ $edithosts =~ (y|n) ]]; do
        echo -ne "${GREEN}Would you like me to do this for you? [y/n]${NC}: "
        read edithosts
    done

    if [[ $edithosts == "y" ]]; then
        sudo sed -i "/127.0.1.1/s/$/ ${rmmdomain} $frontenddomain $meshdomain/" /etc/hosts
    else
        echo -ne "${GREEN}Please manually edit your /etc/hosts file to match the line below and re-run this script.${NC}\n"
        sed "/127.0.1.1/s/$/ ${rmmdomain} $frontenddomain $meshdomain/" /etc/hosts | grep 127.0.1.1
        exit 1
    fi
fi


BEHIND_NAT=false
IPV4=$(ip -4 addr | sed -ne 's|^.* inet \([^/]*\)/.* scope global.*$|\1|p' | head -1)
if echo "$IPV4" | grep -qE '^(10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.|192\.168)'; then
    BEHIND_NAT=true 
fi

echo -ne "${YELLOW}Create a username for meshcentral${NC}: "
read meshusername

while [[ $letsemail != *[@]*[.]* ]]
do
echo -ne "${YELLOW}Enter a valid email address for let's encrypt renewal notifications and meshcentral${NC}: "
read letsemail
done

print_green 'Getting wildcard cert'

sudo apt install -y software-properties-common
sudo apt update
sudo apt install -y certbot

sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns -m ${letsemail} --no-eff-email
while [[ $? -ne 0 ]]
do
sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns -m ${letsemail} --no-eff-email
done

print_green 'Creating saltapi user'

sudo adduser --no-create-home --disabled-password --gecos "" saltapi
echo "saltapi:${SALTPW}" | sudo chpasswd

print_green 'Installing golang'

sudo apt install -y curl wget

sudo mkdir -p /usr/local/rmmgo
go_tmp=$(mktemp -d -t rmmgo-XXXXXXXXXX)
wget https://golang.org/dl/go1.15.linux-amd64.tar.gz -P ${go_tmp}

tar -xzf ${go_tmp}/go1.15.linux-amd64.tar.gz -C ${go_tmp}

sudo mv ${go_tmp}/go /usr/local/rmmgo/
rm -rf ${go_tmp}

print_green 'Installing Nginx'

sudo apt install -y nginx
sudo systemctl stop nginx

print_green 'Installing NodeJS'

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
sudo chown ${USER}:${USER} -R /meshcentral
cd /meshcentral
npm install meshcentral@0.6.48
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
      "Title": "Tactical RMM",
      "Title2": "Tactical RMM",
      "NewAccounts": false,
      "CertUrl": "https://${meshdomain}:443/",
      "GeoLocation": true,
      "CookieIpCheck": false,
      "mstsc": true,
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

sudo apt update
sudo apt install -y python3.8-venv python3.8-dev python3-pip python3-cherrypy3 python3-setuptools python3-wheel ca-certificates redis git

print_green 'Installing postgresql'

sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-12

print_green 'Creating database for the rmm'

sudo -u postgres psql -c "CREATE DATABASE tacticalrmm"
sudo -u postgres psql -c "CREATE USER ${pgusername} WITH PASSWORD '${pgpw}'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET client_encoding TO 'utf8'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET default_transaction_isolation TO 'read committed'"
sudo -u postgres psql -c "ALTER ROLE ${pgusername} SET timezone TO 'UTC'"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tacticalrmm TO ${pgusername}"

sudo mkdir /rmm
sudo chown ${USER}:${USER} /rmm
sudo mkdir -p /var/log/celery
sudo chown ${USER}:${USER} /var/log/celery
git clone https://github.com/wh1te909/tacticalrmm.git /rmm/

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

SALT_USERNAME = "saltapi"
SALT_PASSWORD = "${SALTPW}"
SALT_HOST     = "127.0.0.1"
MESH_USERNAME = "${meshusername}"
MESH_SITE = "https://${meshdomain}"
REDIS_HOST    = "localhost"
EOF
)"
echo "${localvars}" > /rmm/api/tacticalrmm/tacticalrmm/local_settings.py

print_green 'Installing the backend'

cd /rmm/api
python3 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools==49.6.0 wheel==0.35.1
pip install --no-cache-dir -r /rmm/api/tacticalrmm/requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py load_chocos
python manage.py load_community_scripts
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
python manage.py generate_barcode ${RANDBASE} ${djangousername} ${frontenddomain}
deactivate
read -n 1 -s -r -p "Press any key to continue..."


uwsgini="$(cat << EOF
[uwsgi]

logto = /rmm/api/tacticalrmm/tacticalrmm/private/log/uwsgi.log
chdir = /rmm/api/tacticalrmm
module = tacticalrmm.wsgi
home = /rmm/api/env
master = true
processes = 6
threads = 6
enable-threads = True
socket = /rmm/api/tacticalrmm/tacticalrmm.sock
harakiri = 300
chmod-socket = 660
# clear environment on exit
vacuum = true
die-on-term = true
max-requests = 500
max-requests-delta = 1000
EOF
)"
echo "${uwsgini}" > /rmm/api/tacticalrmm/app.ini


rmmservice="$(cat << EOF
[Unit]
Description=tacticalrmm uwsgi daemon
After=network.target

[Service]
User=${USER}
Group=www-data
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PATH=/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/rmm/api/env/bin/uwsgi --ini app.ini
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${rmmservice}" | sudo tee /etc/systemd/system/rmm.service > /dev/null


nginxrmm="$(cat << EOF
server_tokens off;

upstream tacticalrmm {
    server unix:////rmm/api/tacticalrmm/tacticalrmm.sock;
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
    access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log;
    error_log /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log;
    ssl_certificate /etc/letsencrypt/live/${rootdomain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${rootdomain}/privkey.pem;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';

    location /static/ {
        root /rmm/api/tacticalrmm;
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /rmm/api/tacticalrmm/tacticalrmm/private/;
    }

    location /saltscripts/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /srv/salt/scripts/userdefined/;
    }

    location /builtin/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /srv/salt/scripts/;
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
    ssl_certificate /etc/letsencrypt/live/${rootdomain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${rootdomain}/privkey.pem;
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

wget -O - https://repo.saltstack.com/py3/ubuntu/20.04/amd64/latest/SALTSTACK-GPG-KEY.pub | sudo apt-key add -
echo 'deb http://repo.saltstack.com/py3/ubuntu/20.04/amd64/latest focal main' | sudo tee /etc/apt/sources.list.d/saltstack.list

sudo apt update
sudo apt install -y salt-master

print_green 'Waiting 30 seconds for salt to start'
sleep 30

saltvars="$(cat << EOF
timeout: 20
gather_job_timeout: 25
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
echo "${saltvars}" | sudo tee /etc/salt/master.d/rmm-salt.conf > /dev/null

# fix the stupid 1 MB limit present in msgpack 0.6.2, which btw was later changed to 100 MB in msgpack 1.0.0
# but 0.6.2 is the default on ubuntu 20
sudo sed -i 's/msgpack_kwargs = {"raw": six.PY2}/msgpack_kwargs = {"raw": six.PY2, "max_buffer_size": 2147483647}/g' /usr/lib/python3/dist-packages/salt/transport/ipc.py



print_green 'Installing Salt API'
sudo apt install -y salt-api

sudo mkdir /etc/conf.d

celeryservice="$(cat << EOF
[Unit]
Description=Celery Service
After=network.target
After=redis-server.service

[Service]
Type=forking
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} multi start \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} \${CELERYD_OPTS}'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \${CELERYD_NODES} --pidfile=\${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c '\${CELERY_BIN} multi restart \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} \${CELERYD_OPTS}'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celeryservice}" | sudo tee /etc/systemd/system/celery.service > /dev/null

celeryconf="$(cat << EOF
CELERYD_NODES="w1"

CELERY_BIN="/rmm/api/env/bin/celery"

CELERY_APP="tacticalrmm"

CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=2900 --autoscale=50,5"

CELERYD_PID_FILE="/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="INFO"

CELERYBEAT_PID_FILE="/rmm/api/tacticalrmm/beat.pid"
CELERYBEAT_LOG_FILE="/var/log/celery/beat.log"
EOF
)"
echo "${celeryconf}" | sudo tee /etc/conf.d/celery.conf > /dev/null

celerywinupdatesvc="$(cat << EOF
[Unit]
Description=Celery WinUpdate Service
After=network.target
After=redis-server.service

[Service]
Type=forking
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery-winupdate.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} multi start \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} -Q wupdate \${CELERYD_OPTS}'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \${CELERYD_NODES} --pidfile=\${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c '\${CELERY_BIN} multi restart \${CELERYD_NODES} -A \${CELERY_APP} --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} -Q wupdate \${CELERYD_OPTS}'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerywinupdatesvc}" | sudo tee /etc/systemd/system/celery-winupdate.service > /dev/null

celerywinupdate="$(cat << EOF
CELERYD_NODES="w2"

CELERY_BIN="/rmm/api/env/bin/celery"
CELERY_APP="tacticalrmm"
CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=4000 --autoscale=40,1"

CELERYD_PID_FILE="/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="ERROR"
EOF
)"
echo "${celerywinupdate}" | sudo tee /etc/conf.d/celery-winupdate.conf > /dev/null

celerybeatservice="$(cat << EOF
[Unit]
Description=Celery Beat Service
After=network.target
After=redis-server.service

[Service]
Type=simple
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} beat -A \${CELERY_APP} --pidfile=\${CELERYBEAT_PID_FILE} --logfile=\${CELERYBEAT_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL}'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerybeatservice}" | sudo tee /etc/systemd/system/celerybeat.service > /dev/null

sudo mkdir -p /srv/salt
sudo cp -r /rmm/_modules /srv/salt/
sudo cp -r /rmm/scripts /srv/salt/
sudo mkdir /srv/salt/scripts/userdefined
sudo chown ${USER}:${USER} -R /srv/salt/
sudo chown ${USER}:www-data /srv/salt/scripts/userdefined
sudo chmod 750 /srv/salt/scripts/userdefined
sudo chown ${USER}:${USER} -R /etc/conf.d/

meshservice="$(cat << EOF
[Unit]
Description=MeshCentral Server
After=network.target
After=mongod.service
After=nginx.service
[Service]
Type=simple
LimitNOFILE=1000000
ExecStart=/usr/bin/node node_modules/meshcentral
Environment=NODE_ENV=production
WorkingDirectory=/meshcentral
User=${USER}
Group=${USER}
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${meshservice}" | sudo tee /etc/systemd/system/meshcentral.service > /dev/null

sudo systemctl daemon-reload


sudo systemctl enable salt-master
sudo systemctl enable salt-api

sudo systemctl restart salt-api

sudo chown -R $USER:$GROUP /home/${USER}/.npm
sudo chown -R $USER:$GROUP /home/${USER}/.config

quasarenv="$(cat << EOF
PROD_URL = "https://${rmmdomain}"
DEV_URL = "https://${rmmdomain}"
EOF
)"
echo "${quasarenv}" | tee /rmm/web/.env > /dev/null

print_green 'Installing the frontend'

cd /rmm/web
npm install
npm run build
sudo mkdir -p /var/www/rmm
sudo cp -pvr /rmm/web/dist /var/www/rmm/
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
    ssl_certificate /etc/letsencrypt/live/${rootdomain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${rootdomain}/privkey.pem;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
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


print_green 'Enabling Services'

for i in nginx celery.service celerybeat.service celery-winupdate.service rmm.service
do
  sudo systemctl enable ${i}
  sudo systemctl restart ${i}
done
sleep 5
sudo systemctl enable meshcentral

print_green 'Starting meshcentral and waiting for it to install plugins'

sudo systemctl restart meshcentral

sleep 3

# The first time we start meshcentral, it will need some time to generate certs and install plugins.
# This will take anywhere from a few seconds to a few minutes depending on the server's hardware
# We will know it's ready once the last line of the systemd service stdout is 'MeshCentral HTTP server running on port.....'
while ! [[ $CHECK_MESH_READY ]]; do
  CHECK_MESH_READY=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
  sleep 3
done

print_green 'Generating meshcentral login token key'

MESHTOKENKEY=$(node /meshcentral/node_modules/meshcentral --logintokenkey)

meshtoken="$(cat << EOF
MESH_TOKEN_KEY = "${MESHTOKENKEY}"
EOF
)"
echo "${meshtoken}" | tee --append /rmm/api/tacticalrmm/tacticalrmm/local_settings.py > /dev/null


print_green 'Creating meshcentral account and group'

sudo systemctl stop meshcentral
sleep 3
cd /meshcentral

node node_modules/meshcentral --createaccount ${meshusername} --pass ${MESHPASSWD} --email ${letsemail}
sleep 2
node node_modules/meshcentral --adminaccount ${meshusername}

sudo systemctl start meshcentral
sleep 5

while ! [[ $CHECK_MESH_READY2 ]]; do
  CHECK_MESH_READY2=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
  sleep 3
done

node node_modules/meshcentral/meshctrl.js --url wss://${meshdomain}:443 --loginuser ${meshusername} --loginpass ${MESHPASSWD} AddDeviceGroup --name TacticalRMM
sleep 5
MESHEXE=$(node node_modules/meshcentral/meshctrl.js --url wss://${meshdomain}:443 --loginuser ${meshusername} --loginpass ${MESHPASSWD} GenerateInviteLink --group TacticalRMM --hours 8)

cd /rmm/api/tacticalrmm
source /rmm/api/env/bin/activate
python manage.py initial_db_setup
deactivate


print_green 'Restarting services'
for i in celery.service celerybeat.service celery-winupdate.service rmm.service
do
  sudo systemctl restart ${i}
done

print_green 'Restarting salt-master and waiting 30 seconds'
sudo systemctl restart salt-master
sleep 30
sudo systemctl restart salt-api

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n\n"
printf >&2 "${YELLOW}Installation complete!${NC}\n\n"
printf >&2 "${YELLOW}Download the meshagent 64 bit EXE from:\n\n${GREEN}"
echo ${MESHEXE} | sed 's/{.*}//'
printf >&2 "${NC}\n\n"
printf >&2 "${YELLOW}Access your rmm at: ${GREEN}https://${frontenddomain}${NC}\n\n"
printf >&2 "${YELLOW}Django admin url: ${GREEN}https://${rmmdomain}/${ADMINURL}${NC}\n\n"
printf >&2 "${YELLOW}MeshCentral password: ${GREEN}${MESHPASSWD}${NC}\n\n"

if [ "$BEHIND_NAT" = true ]; then
    echo -ne "${YELLOW}Read below if your router does NOT support Hairpin NAT${NC}\n\n"  
    echo -ne "${GREEN}If you will be accessing the web interface of the RMM from the same LAN as this server,${NC}\n"
    echo -ne "${GREEN}you'll need to make sure your 3 subdomains resolve to ${IPV4}${NC}\n"
    echo -ne "${GREEN}This also applies to any agents that will be on the same local network as the rmm.${NC}\n"
    echo -ne "${GREEN}You'll also need to setup port forwarding in your router on ports 80, 443, 4505 and 4506 tcp.${NC}\n\n"
fi

printf >&2 "${YELLOW}Please refer to the github README for next steps${NC}\n\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
