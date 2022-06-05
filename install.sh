#!/bin/bash

# For first time Dev testing use --prereq to get cert and python setup in place
#
# For Dev testing use --devtest
#
# For Dev testing to define a different repo url use: -u URL
# 
# For Dev testing to device a different repo branch name use: -b develop

### 1. -prereq (does python and certs prep)
### 2. Snapshot vm
### 3. Run -devtest to skip python and certs with either -u and/or -b depending on what you're testing
### 4. Install completes and you test
### 5. Ready to re-test, restore snapshot from 2. and redo

### Script Info
SCRIPT_VERSION="63"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/install.sh'
THIS_SCRIPT=$(readlink -f "$0")

### Misc info
SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.10.4'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'

### Import functions
. $PWD/bashfunctions.cfg

### Set colors
setColors;

### Gather OS info
getOSInfo;

### Install script pre-reqs
installPreReqs;

### Check for new functions version, only include script name as variable
checkCfgVer "$THIS_SCRIPT";

### Check for new script version, pass script version, url, and script name variables in that order
checkScriptVer "$SCRIPT_VERSION" "$SCRIPT_URL" "$THIS_SCRIPT";

### Install additional prereqs
installAdditionalPreReqs;

### Check for dev flags
#while getopts b:u: flag
#do
#    case "${flag}" in
#        b) devbranch=${OPTARG};;
#        u) devurl=${OPTARG};;
#    esac
#done
#echo "devbranch: $devbranch";
#echo "devurl: $devurl";

### Fallback if lsb_release -si returns anything else than Ubuntu, Debian or Raspbian
wutOSThis;

### Verify compatible OS and version
verifySupportedOS;

### Check if root
checkRoot;

### Check language/locale
checkLocale;

### Repo info for Postegres and Mongo
setInstallRepos;

### Prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service

### Create usernames and passwords
generateUsersAndPass;

### This does... something
cls;

### Get host/domain info
getHostAndDomainInfo;

# If server is behind NAT we need to add the 3 subdomains to the host file
# so that nginx can properly route between the frontend, backend and meshcentral
# EDIT 8-29-2020
# running this even if server is __not__ behind NAT just to make DNS resolving faster
# this also allows the install script to properly finish even if DNS has not fully propagated
CHECK_HOSTS=$(grep 127.0.1.1 /etc/hosts | grep "$rmmdomain" | grep "$meshdomain" | grep "$frontenddomain")
HAS_11=$(grep 127.0.1.1 /etc/hosts)

if ! [[ $CHECK_HOSTS ]]; then
  print_green 'Adding subdomains to hosts file'
  if [[ $HAS_11 ]]; then
    sudo sed -i "/127.0.1.1/s/$/ ${rmmdomain} ${frontenddomain} ${meshdomain}/" /etc/hosts
  else
    echo "127.0.1.1 ${rmmdomain} ${frontenddomain} ${meshdomain}" | sudo tee --append /etc/hosts > /dev/null
  fi
fi

BEHIND_NAT=false
IPV4=$(ip -4 addr | sed -ne 's|^.* inet \([^/]*\)/.* scope global.*$|\1|p' | head -1)
if echo "$IPV4" | grep -qE '^(10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.|192\.168)'; then
    BEHIND_NAT=true
fi

### Certificate generation
sudo apt install -y certbot

print_green 'Getting wildcard cert'

sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --no-bootstrap --preferred-challenges dns -m ${letsemail} --no-eff-email
while [[ $? -ne 0 ]]
do
sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --no-bootstrap --preferred-challenges dns -m ${letsemail} --no-eff-email
done

CERT_PRIV_KEY=/etc/letsencrypt/live/${rootdomain}/privkey.pem
CERT_PUB_KEY=/etc/letsencrypt/live/${rootdomain}/fullchain.pem

sudo chown ${USER}:${USER} -R /etc/letsencrypt
sudo chmod 775 -R /etc/letsencrypt

### Install Nginx
print_green 'Installing Nginx'
installNginx;

### Install NodeJS
print_green 'Installing NodeJS'
installNodeJS;

### Install and enable MongoDB
print_green 'Installing MongoDB'
installMongo;

### Install Python
print_green "Installing Python ${PYTHON_VER}"
installPython;

### Installing Redis
print_green 'Installing redis'
installRedis;

### Install and enable Postgresql
print_green 'Installing postgresql'
installPostgresql;

### Postgres DB creation
print_green 'Creating database for the rmm'
createPGDB;

### Clone main repo
print_green 'Cloning repo'

sudo mkdir /rmm
sudo chown ${USER}:${USER} /rmm
sudo mkdir -p /var/log/celery
sudo chown ${USER}:${USER} /var/log/celery

#if [[ $devurl ]]; then
#  git clone ${devurl} /rmm/
#else
git clone https://github.com/amidaware/tacticalrmm.git /rmm/
#fi

cd /rmm
git config user.email "admin@example.com"
git config user.name "Bob"
#if [[ $devbranch ]]; then
#  git checkout ${branch}
#else
  git checkout master
#fi

### Clone scripts repo
cloneScriptsRepo;

### Installing NATS
print_green 'Installing NATS'
installNats "install";

### Install MeshCentral
print_green 'Installing MeshCentral'

MESH_VER=$(grep "^MESH_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

sudo mkdir -p /meshcentral/meshcentral-data
sudo chown ${USER}:${USER} -R /meshcentral
cd /meshcentral
npm install meshcentral@${MESH_VER}
sudo chown ${USER}:${USER} -R /meshcentral

### Create MeshCentral config
meshcfg="$(cat << EOF
{
  "settings": {
    "Cert": "${meshdomain}",
    "MongoDb": "mongodb://127.0.0.1:27017",
    "MongoDbName": "meshcentral",
    "WANonly": true,
    "Minify": 1,
    "Port": 4443,
    "AgentAliasPort": 443,
    "AliasPort": 443,
    "AllowLoginToken": true,
    "AllowFraming": true,
    "_AgentPing": 60,
    "AgentPong": 300,
    "AllowHighQualityDesktop": true,
    "TlsOffload": "127.0.0.1",
    "agentCoreDump": false,
    "Compression": true,
    "WsCompression": true,
    "AgentWsCompression": true,
    "MaxInvalidLogin": { "time": 5, "count": 5, "coolofftime": 30 }
  },
  "domains": {
    "": {
      "Title": "Tactical RMM",
      "Title2": "Tactical RMM",
      "NewAccounts": false,
      "CertUrl": "https://${meshdomain}/",
      "GeoLocation": true,
      "CookieIpCheck": false,
      "mstsc": true
    }
  }
}
EOF
)"
echo "${meshcfg}" > /meshcentral/meshcentral-data/config.json

### Create local settings file
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

MESH_USERNAME = "${meshusername}"
MESH_SITE = "https://${meshdomain}"
REDIS_HOST    = "localhost"
ADMIN_ENABLED = True
EOF
)"
echo "${localvars}" > /rmm/api/tacticalrmm/tacticalrmm/local_settings.py

### Install NATS-API and correct permissions
sudo cp /rmm/natsapi/bin/nats-api /usr/local/bin
sudo chown ${USER}:${USER} /usr/local/bin/nats-api
sudo chmod +x /usr/local/bin/nats-api

### Install backend, configure primary admin user, setup admin 2fa
print_green 'Installing the backend'

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

cd /rmm/api
python3.10 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir setuptools==${SETUPTOOLS_VER} wheel==${WHEEL_VER}
pip install --no-cache-dir -r /rmm/api/tacticalrmm/requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py create_natsapi_conf
python manage.py load_chocos
python manage.py load_community_scripts
WEB_VERSION=$(python manage.py get_config webversion)
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
printf >&2 "${YELLOW}Please create your login for the RMM website and django admin${NC}\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
echo -ne "Username: "
read djangousername
python manage.py createsuperuser --username ${djangousername} --email ${letsemail}
python manage.py create_installer_user
RANDBASE=$(python manage.py generate_totp)
cls
python manage.py generate_barcode ${RANDBASE} ${djangousername} ${frontenddomain}
deactivate
read -n 1 -s -r -p "Press any key to continue..."

### Determine Proc setting for UWSGI
echo 'Optimizing for number of processors'
uwsgiprocs=4
if [[ "$numprocs" == "1" ]]; then
  uwsgiprocs=2
else
  uwsgiprocs=$numprocs
fi

### Create UWSGI config
uwsgini="$(cat << EOF
[uwsgi]
chdir = /rmm/api/tacticalrmm
module = tacticalrmm.wsgi
home = /rmm/api/env
master = true
processes = ${uwsgiprocs}
threads = ${uwsgiprocs}
enable-threads = true
socket = /rmm/api/tacticalrmm/tacticalrmm.sock
harakiri = 300
chmod-socket = 660
buffer-size = 65535
vacuum = true
die-on-term = true
max-requests = 500
disable-logging = true
EOF
)"
echo "${uwsgini}" > /rmm/api/tacticalrmm/app.ini

### Create RMM UWSGI systemd service
rmmservice="$(cat << EOF
[Unit]
Description=tacticalrmm uwsgi daemon
After=network.target postgresql.service

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

### Create Daphne systemd service
daphneservice="$(cat << EOF
[Unit]
Description=django channels daemon
After=network.target

[Service]
User=${USER}
Group=www-data
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PATH=/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/rmm/api/env/bin/daphne -u /rmm/daphne.sock tacticalrmm.asgi:application
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${daphneservice}" | sudo tee /etc/systemd/system/daphne.service > /dev/null

### Create NATS systemd service
natsservice="$(cat << EOF
[Unit]
Description=NATS Server
After=network.target

[Service]
PrivateTmp=true
Type=simple
ExecStart=/usr/local/bin/nats-server -c /rmm/api/tacticalrmm/nats-rmm.conf
ExecReload=/usr/bin/kill -s HUP \$MAINPID
ExecStop=/usr/bin/kill -s SIGINT \$MAINPID
User=${USER}
Group=www-data
Restart=always
RestartSec=5s
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsservice}" | sudo tee /etc/systemd/system/nats.service > /dev/null

### Create NATS-api systemd service
natsapi="$(cat << EOF
[Unit]
Description=TacticalRMM Nats Api v1
After=nats.service

[Service]
Type=simple
ExecStart=/usr/local/bin/nats-api
User=${USER}
Group=${USER}
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsapi}" | sudo tee /etc/systemd/system/nats-api.service > /dev/null

### Create RMM Nginx site config
nginxrmm="$(cat << EOF
server_tokens off;

upstream tacticalrmm {
    server unix:////rmm/api/tacticalrmm/tacticalrmm.sock;
}

map \$http_user_agent \$ignore_ua {
    "~python-requests.*" 0;
    "~go-resty.*" 0;
    default 1;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${rmmdomain};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${rmmdomain};
    client_max_body_size 300M;
    access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log combined if=\$ignore_ua;
    error_log /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;
    
    location /static/ {
        root /rmm/api/tacticalrmm;
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /rmm/api/tacticalrmm/tacticalrmm/private/;
    }

    location ~ ^/ws/ {
        proxy_pass http://unix:/rmm/daphne.sock;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect     off;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host \$server_name;
    }

    location / {
        uwsgi_pass  tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 300s;
        uwsgi_ignore_client_abort on;
    }
}
EOF
)"
echo "${nginxrmm}" | sudo tee /etc/nginx/sites-available/rmm.conf > /dev/null

### Create MeshCentral Nginx configuration
nginxmesh="$(cat << EOF
server {
  listen 80;
  listen [::]:80;
  server_name ${meshdomain};
  return 301 https://\$server_name\$request_uri;
}

server {

    listen 443 ssl;
    listen [::]:443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${meshdomain};
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};

    ssl_session_cache shared:WEBSSL:10m;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://127.0.0.1:4443/;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
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

### Enable Mesh and RMM sites
sudo ln -s /etc/nginx/sites-available/rmm.conf /etc/nginx/sites-enabled/rmm.conf
sudo ln -s /etc/nginx/sites-available/meshcentral.conf /etc/nginx/sites-enabled/meshcentral.conf

### Create conf directory
sudo mkdir /etc/conf.d

### Create Celery systemd service
celeryservice="$(cat << EOF
[Unit]
Description=Celery Service V2
After=network.target redis-server.service postgresql.service

[Service]
Type=forking
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi start \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --loglevel="\${CELERYD_LOG_LEVEL}"'
ExecReload=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi restart \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celeryservice}" | sudo tee /etc/systemd/system/celery.service > /dev/null

### Configure Celery service
celeryconf="$(cat << EOF
CELERYD_NODES="w1"

CELERY_BIN="/rmm/api/env/bin/celery"

CELERY_APP="tacticalrmm"

CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=86400 --autoscale=20,2"

CELERYD_PID_FILE="/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="ERROR"

CELERYBEAT_PID_FILE="/rmm/api/tacticalrmm/beat.pid"
CELERYBEAT_LOG_FILE="/var/log/celery/beat.log"
EOF
)"
echo "${celeryconf}" | sudo tee /etc/conf.d/celery.conf > /dev/null

### Create CeleryBeat systemd service
celerybeatservice="$(cat << EOF
[Unit]
Description=Celery Beat Service V2
After=network.target redis-server.service postgresql.service

[Service]
Type=simple
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \${CELERY_APP} beat --pidfile=\${CELERYBEAT_PID_FILE} --logfile=\${CELERYBEAT_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL}'
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${celerybeatservice}" | sudo tee /etc/systemd/system/celerybeat.service > /dev/null

sudo chown ${USER}:${USER} -R /etc/conf.d/

### Create MeshCentral systemd service
meshservice="$(cat << EOF
[Unit]
Description=MeshCentral Server
After=network.target mongod.service nginx.service
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

### Update services info
sudo systemctl daemon-reload

### Verify and correct permissions
if [ -d ~/.npm ]; then
  sudo chown -R $USER:$GROUP ~/.npm
fi

if [ -d ~/.config ]; then
  sudo chown -R $USER:$GROUP ~/.config
fi

### Install frontend
print_green 'Installing the frontend'
installFrontEnd;

### Set front end Nginx config and enable
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
    listen [::]:443 ssl;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;
}

server {
    if (\$host = ${frontenddomain}) {
        return 301 https://\$host\$request_uri;
    }

    listen 80;
    listen [::]:80;
    server_name ${frontenddomain};
    return 404;
}
EOF
)"
echo "${nginxfrontend}" | sudo tee /etc/nginx/sites-available/frontend.conf > /dev/null

### Enable Frontend site
sudo ln -s /etc/nginx/sites-available/frontend.conf /etc/nginx/sites-enabled/frontend.conf

### Enable RMM, Daphne, Celery, and Nginx services
print_green 'Enabling Services'

for i in rmm.service daphne.service celery.service celerybeat.service nginx
do
  sudo systemctl enable ${i}
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done
sleep 5

### Enable MeshCentral service
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

### Generating MeshCentral key
print_green 'Generating meshcentral login token key'

MESHTOKENKEY=$(node /meshcentral/node_modules/meshcentral --logintokenkey)

meshtoken="$(cat << EOF
MESH_TOKEN_KEY = "${MESHTOKENKEY}"
EOF
)"
echo "${meshtoken}" | tee --append /rmm/api/tacticalrmm/tacticalrmm/local_settings.py > /dev/null

### Configuring MeshCentral admin user and device group, restart service
print_green 'Creating meshcentral account and group'

sudo systemctl stop meshcentral
sleep 1
cd /meshcentral

node node_modules/meshcentral --createaccount ${meshusername} --pass ${MESHPASSWD} --email ${letsemail}
sleep 1
node node_modules/meshcentral --adminaccount ${meshusername}

sudo systemctl start meshcentral
sleep 5

while ! [[ $CHECK_MESH_READY2 ]]; do
  CHECK_MESH_READY2=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
  sleep 3
done

node node_modules/meshcentral/meshctrl.js --url wss://${meshdomain} --loginuser ${meshusername} --loginpass ${MESHPASSWD} AddDeviceGroup --name TacticalRMM
sleep 1

### Enable and configure NATS service
sudo systemctl enable nats.service
cd /rmm/api/tacticalrmm
source /rmm/api/env/bin/activate
python manage.py initial_db_setup
python manage.py reload_nats
deactivate
sudo systemctl start nats.service

sleep 1
sudo systemctl enable nats-api.service
sudo systemctl start nats-api.service

### Disable django admin
sed -i 's/ADMIN_ENABLED = True/ADMIN_ENABLED = False/g' /rmm/api/tacticalrmm/tacticalrmm/local_settings.py

### Restart core services
print_green 'Restarting services'
for i in rmm.service daphne.service celery.service celerybeat.service
do
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n\n"
printf >&2 "${YELLOW}Installation complete!${NC}\n\n"
printf >&2 "${YELLOW}Access your rmm at: ${GREEN}https://${frontenddomain}${NC}\n\n"
printf >&2 "${YELLOW}Django admin url (disabled by default): ${GREEN}https://${rmmdomain}/${ADMINURL}/${NC}\n\n"
printf >&2 "${YELLOW}MeshCentral username: ${GREEN}${meshusername}${NC}\n"
printf >&2 "${YELLOW}MeshCentral password: ${GREEN}${MESHPASSWD}${NC}\n\n"

if [ "$BEHIND_NAT" = true ]; then
    echo -ne "${YELLOW}Read below if your router does NOT support Hairpin NAT${NC}\n\n"
    echo -ne "${GREEN}If you will be accessing the web interface of the RMM from the same LAN as this server,${NC}\n"
    echo -ne "${GREEN}you'll need to make sure your 3 subdomains resolve to ${IPV4}${NC}\n"
    echo -ne "${GREEN}This also applies to any agents that will be on the same local network as the rmm.${NC}\n"
    echo -ne "${GREEN}You'll also need to setup port forwarding in your router on ports 80, 443 and 4222 tcp.${NC}\n\n"
fi

printf >&2 "${YELLOW}Please refer to the github README for next steps${NC}\n\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
