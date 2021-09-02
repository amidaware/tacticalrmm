# Unsupported Reference Scripts

!!!note 
    These are not supported scripts/configurations by Tactical RMM, but it's provided here for your reference. 

## HAProxy


Check/Change the mesh central config.json, some of the values may be set already, CertUrl must be changed to point to the HAProxy server.

### Meshcentral Adjustment

Credit to [@bradhawkins](https://github.com/bradhawkins85)

Edit Meshcentral config

```bash
nano /meshcentral/meshcentral-data/config.json
```

Insert this (modify `HAProxyIP` to your network)

```
{
  "settings": {
    "Port": 4430,
    "AliasPort": 443,
    "RedirPort": 800,
    "TlsOffload": "127.0.0.1",
  },
  "domains": {
    "": {
      "CertUrl": "https://HAProxyIP:443/",
    }
  }
}
```

Restart meshcentral

```bash
service meshcentral restart
```

### HAProxy Config

The order of use_backend is important `Tactical-Mesh-WebSocket_ipvANY` must be before `Tactical-Mesh_ipvANY`
The values of `timeout connect`, `timeout server`, `timeout tunnel` in `Tactical-Mesh-WebSocket` have been configured to maintain a stable agent connection, however you may need to adjust these values to suit your environment. 

```
frontend HTTPS-merged
	bind			0.0.0.0:443 name 0.0.0.0:443   ssl crt-list /var/etc/haproxy/HTTPS.crt_list  #ADJUST THIS TO YOUR OWN SSL CERTIFICATES
	mode			http
	log			global
	option			socket-stats
	option			dontlognull
	option			http-server-close
	option			forwardfor
	acl https ssl_fc
	http-request set-header		X-Forwarded-Proto http if !https
	http-request set-header		X-Forwarded-Proto https if https
	timeout client		30000
	acl			RMM	var(txn.txnhost) -m sub -i rmm.example.com
	acl			aclcrt_RMM	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	acl			API	var(txn.txnhost) -m sub -i api.example.com
	acl			aclcrt_API	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	acl			is_websocket	hdr(Upgrade) -i WebSocket
	acl			is_mesh	var(txn.txnhost) -m beg -i mesh.example.com
	acl			aclcrt_MESH-WebSocket	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	acl			MESH	var(txn.txnhost) -m sub -i mesh.example.com
	acl			aclcrt_MESH	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	#PUT OTHER USE_BACKEND IN HERE
	use_backend Tactical_ipvANY  if  RMM aclcrt_RMM
	use_backend Tactical_ipvANY  if  API aclcrt_API
	use_backend Tactical-Mesh-WebSocket_ipvANY  if  is_websocket is_mesh aclcrt_MESH-WebSocket
	use_backend Tactical-Mesh_ipvANY  if  MESH aclcrt_MESH

frontend http-to-https
	bind			0.0.0.0:80   
	mode			http
	log			global
	option			http-keep-alive
	timeout client		30000
	http-request redirect scheme https 


backend Tactical_ipvANY
	mode			http
	id			100
	log			global
	timeout connect		30000
	timeout server		30000
	retries			3
	option			httpchk GET / 
	server			tactical 192.168.10.123:443 id 101 ssl check inter 1000  verify none 


backend Tactical-Mesh-WebSocket_ipvANY
	mode			http
	id			113
	log			global
	timeout connect		3000
	timeout server		3000
	retries			3
	timeout tunnel		3600000
	http-request add-header X-Forwarded-Host %[req.hdr(Host)] 
	http-request add-header X-Forwarded-Proto https 
	server			tactical 192.168.10.123:443 id 101 ssl  verify none 

backend Tactical-Mesh_ipvANY
	mode			http
	id			112
	log			global
	timeout connect		15000
	timeout server		15000
	retries			3
	option			httpchk GET / 
	timeout tunnel		15000
	http-request add-header X-Forwarded-Host %[req.hdr(Host)] 
	http-request add-header X-Forwarded-Proto https 
	server			tactical 192.168.10.123:443 id 101 ssl check inter 1000  verify none 
```

## fail2ban

### Install fail2ban

```bash
sudo apt install -y fail2ban
```

### Set Tactical fail2ban filter conf File


```
tacticalfail2banfilter="$(cat << EOF
[Definition]
failregex = ^<HOST>.*400.17.*$
ignoreregex = ^<HOST>.*200.*$
EOF
)"
sudo echo "${tacticalfail2banfilter}" > /etc/fail2ban/filter.d/tacticalrmm.conf
```

### Set Tactical fail2ban jail conf File

```
tacticalfail2banjail="$(cat << EOF
[tacticalrmm]
enabled = true
port = 80,443
filter = tacticalrmm
action = iptables-allports[name=tactical]
logpath = /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log
maxretry = 3
bantime = 14400
findtime = 14400
EOF
)"
sudo echo "${tacticalfail2banjail}" > /etc/fail2ban/jail.d/tacticalrmm.local
```

### Restart fail2ban

```bash
sudo systemctl restart fail2ban
```

## Using purchased SSL certs instead of LetsEncrypt wildcards

Credit to [@dinger1986](https://github.com/dinger1986)

How to change certs used by Tactical RMM to purchased ones (this can be a wildcard cert).

You need to add the certificate private key and public keys to the following files:

`/etc/nginx/sites-available/rmm.conf`

`/etc/nginx/sites-available/meshcentral.conf`

`/etc/nginx/sites-available/frontend.conf`

`/rmm/api/tacticalrmm/tacticalrmm/local_settings.py`

1. create a new folder for certs and allow tactical user permissions (assumed to be tactical)

		sudo mkdir /certs
		sudo chown -R tactical:tactical /certs"

2. Now move your certs into that folder.

3. Open the api file and add the api certificate or if its a wildcard the directory should be `/certs/yourdomain.com/`

		sudo nano /etc/nginx/sites-available/rmm.conf

    replace   

        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    with

        ssl_certificate /certs/api.yourdomain.com/fullchain.pem;
        ssl_certificate_key /certs/api.yourdomain.com/privkey.pem;

4. Repeat the process for 

        /etc/nginx/sites-available/meshcentral.conf
        /etc/nginx/sites-available/frontend.conf
        
    but change api. to: mesh. and rmm. respectively.

7. Add the following to the last lines of `/rmm/api/tacticalrmm/tacticalrmm/local_settings.py`

        nano /rmm/api/tacticalrmm/tacticalrmm/local_settings.py

    add

        CERT_FILE = "/certs/api.yourdomain.com/fullchain.pem"
        KEY_FILE = "/certs/api.yourdomain.com/privkey.pem"
	
    
6. Regenerate Nats Conf

        cd /rmm/api/tacticalrmm
        source ../env/bin/activate
        python manage.py reload_nats

7. Restart services
   
        sudo systemctl restart rmm celery celerybeat nginx nats natsapi

## Use certbot to do acme challenge over http

The standard SSL cert process in Tactical uses a [DNS challenge](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge) that requires dns txt files to be updated with every run.

The below script uses [http challenge](https://letsencrypt.org/docs/challenge-types/#http-01-challenge) on the 3 separate ssl certs, one for each subdomain: rmm, api, mesh. They still have the same 3 month expiry. You will need to run this script every 3 months (at a minimum - every 2 months probably best) to renew the ssl certs for Tactical RMM.

!!!note
    Your Tactical RMM server will need to have TCP Port: 80 exposed to the internet

```bash
#!/bin/bash

###Set colours same as Tactical RMM install and Update
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

### Ubuntu 20.04 Check

UBU20=$(grep 20.04 "/etc/"*"release")
if ! [[ $UBU20 ]]; then
  echo -ne "\033[0;31mThis script will only work on Ubuntu 20.04\e[0m\n"
  exit 1
fi

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

### Set variables for domains

while [[ $rmmdomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain used for the backend (e.g. api.example.com)${NC}: "
read rmmdomain
done

while [[ $frontenddomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain used for the frontend (e.g. rmm.example.com)${NC}: "
read frontenddomain
done

while [[ $meshdomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain used for meshcentral (e.g. mesh.example.com)${NC}: "
read meshdomain
done

echo -ne "${YELLOW}Enter the current root domain (e.g. example.com or example.co.uk)${NC}: "
read rootdomain


### Setup Certificate Variables
CERT_PRIV_KEY=/etc/letsencrypt/live/${rootdomain}/privkey.pem
CERT_PUB_KEY=/etc/letsencrypt/live/${rootdomain}/fullchain.pem

### Make Letsencrypt directories

sudo mkdir /var/www/letsencrypt
sudo mkdir /var/www/letsencrypt/.mesh
sudo mkdir /var/www/letsencrypt/.rmm
sudo mkdir /var/www/letsencrypt/.api

### Remove config files for nginx

sudo rm /etc/nginx/sites-available/rmm.conf
sudo rm /etc/nginx/sites-available/meshcentral.conf
sudo rm /etc/nginx/sites-available/frontend.conf
sudo rm /etc/nginx/sites-enabled/rmm.conf
sudo rm /etc/nginx/sites-enabled/meshcentral.conf
sudo rm /etc/nginx/sites-enabled/frontend.conf

### Setup tactical nginx config files for letsencrypt

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
    server_name ${rmmdomain};
	    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt/.api/;}
    location / {
    return 301 https://\$server_name\$request_uri;}
}
server {
    listen 443 ssl;
    server_name ${rmmdomain};
    client_max_body_size 300M;
    access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log;
    error_log /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    
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
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect     off;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host $server_name;
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
    location ~ ^/(natsapi) {
        allow 127.0.0.1;
        deny all;
        uwsgi_pass tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 500s;
        uwsgi_ignore_client_abort on;
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
      location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt/.mesh/;}
    location / {
  return 301 https://\$server_name\$request_uri;}
}
server {
    listen 443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${meshdomain};
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    ssl_session_cache shared:WEBSSL:10m;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    location / {
        proxy_pass http://127.0.0.1:4430/;
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
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
}
server {
    listen 80;
    server_name ${frontenddomain};
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt/.rmm/;}
    location / {
    return 301 https://\$host\$request_uri;}
}
EOF
)"
echo "${nginxfrontend}" | sudo tee /etc/nginx/sites-available/frontend.conf > /dev/null

### Relink nginx config files

sudo ln -s /etc/nginx/sites-available/rmm.conf /etc/nginx/sites-enabled/rmm.conf
sudo ln -s /etc/nginx/sites-available/meshcentral.conf /etc/nginx/sites-enabled/meshcentral.conf
sudo ln -s /etc/nginx/sites-available/frontend.conf /etc/nginx/sites-enabled/frontend.conf

### Restart nginx

sudo systemctl restart nginx


### Get letsencrypt Certs

sudo letsencrypt certonly --webroot -w /var/www/letsencrypt/.mesh/ -d ${meshdomain}
sudo letsencrypt certonly --webroot -w /var/www/letsencrypt/.rmm/ -d ${frontenddomain}
sudo letsencrypt certonly --webroot -w /var/www/letsencrypt/.api/ -d ${rmmdomain}

### Ensure letsencrypt Permissions are correct
sudo chown ${USER}:${USER} -R /etc/letsencrypt
sudo chmod 775 -R /etc/letsencrypt

### Set variables for new certs

CERT_PRIV_KEY_API=/etc/letsencrypt/live/${rmmdomain}/privkey.pem
CERT_PUB_KEY_API=/etc/letsencrypt/live/${rmmdomain}/fullchain.pem
CERT_PRIV_KEY_RMM=/etc/letsencrypt/live/${frontenddomain}/privkey.pem
CERT_PUB_KEY_RMM=/etc/letsencrypt/live/${frontenddomain}/fullchain.pem
CERT_PRIV_KEY_MESH=/etc/letsencrypt/live/${meshdomain}/privkey.pem
CERT_PUB_KEY_MESH=/etc/letsencrypt/live/${meshdomain}/fullchain.pem

### Replace certs in files

rmmlocalsettings="$(cat << EOF
CERT_FILE = "${CERT_PUB_KEY_API}"
KEY_FILE = "${CERT_PRIV_KEY_API}"
EOF
)"
echo "${rmmlocalsettings}" | tee --append /rmm/api/tacticalrmm/tacticalrmm/local_settings.py > /dev/null

sudo sed -i "s|${CERT_PRIV_KEY}|${CERT_PRIV_KEY_API}|g" /etc/nginx/sites-available/rmm.conf
sudo sed -i "s|${CERT_PUB_KEY}|${CERT_PUB_KEY_API}|g" /etc/nginx/sites-available/rmm.conf
sudo sed -i "s|${CERT_PRIV_KEY}|${CERT_PRIV_KEY_MESH}|g" /etc/nginx/sites-available/meshcentral.conf
sudo sed -i "s|${CERT_PUB_KEY}|${CERT_PUB_KEY_MESH}|g" /etc/nginx/sites-available/meshcentral.conf
sudo sed -i "s|${CERT_PRIV_KEY}|${CERT_PRIV_KEY_RMM}|g" /etc/nginx/sites-available/frontend.conf
sudo sed -i "s|${CERT_PUB_KEY}|${CERT_PUB_KEY_RMM}|g" /etc/nginx/sites-available/frontend.conf

### Remove Wildcard Cert

rm -r /etc/letsencrypt/live/${rootdomain}/
rm -r /etc/letsencrypt/archive/${rootdomain}/
rm /etc/letsencrypt/renewal/${rootdomain}.conf


### Regenerate Nats Conf
cd /rmm/api/tacticalrmm
source ../env/bin/activate
python manage.py reload_nats

### Restart services

for i in rmm celery celerybeat nginx nats natsapi
do
printf >&2 "${GREEN}Restarting ${i} service...${NC}\n"
sudo systemctl restart ${i}
done


###Renew certs can be done by sudo letsencrypt renew (this should automatically be in /etc/cron.d/certbot)
```