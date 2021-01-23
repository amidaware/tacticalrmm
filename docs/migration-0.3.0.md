### Upgrading to Tactical RMM 0.3.0
- Some of these steps may not apply to you depending on when you installed but please go through all of them just to make sure you have all.

1. stop all services
```bash
for i in salt-master salt-api rmm celery celerybeat celery-winupdate meshcentral nginx; do sudo systemctl stop $i; done
```

2. Edit `/etc/nginx/sites-available/rmm.conf` and add the following location block. You can add it right after the `location /builtin/ {...}` block. This file needs to be opened with sudo
```bash
location ~ ^/(natsapi) {
    allow 127.0.0.1;
    deny all;
    uwsgi_pass tacticalrmm;
    include     /etc/nginx/uwsgi_params;
    uwsgi_read_timeout 500s;
    uwsgi_ignore_client_abort on;
}
```

Add the following to the top of the file right under the `upstream tacticalrmm {...}` block
```bash
map $http_user_agent $ignore_ua {
    "~python-requests.*" 0;
    "~go-resty.*" 0;
    default 1;
}
```

Look for this line
```bash
access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log;
```
and change to
```bash
access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log combined if=$ignore_ua;
```

Example of what entire file should look like:
```bash
server_tokens off;

upstream tacticalrmm {
    server unix:////rmm/api/tacticalrmm/tacticalrmm.sock;
}

map $http_user_agent $ignore_ua {
    "~python-requests.*" 0;
    "~go-resty.*" 0;
    default 1;
}

server {
    listen 80;
    server_name api.EXAMPLE.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    client_max_body_size 300M;
    access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log combined if=$ignore_ua;
    error_log /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log;
    ssl_certificate /etc/letsencrypt/live/EXAMPLE.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/EXAMPLE.com/privkey.pem;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';

    location /static/ {
        root /rmm/api/tacticalrmm;
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://rmm.EXAMPLE.com";
        alias /rmm/api/tacticalrmm/tacticalrmm/private/;
    }

    location /saltscripts/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://rmm.EXAMPLE.com";
        alias /srv/salt/scripts/userdefined/;
    }

    location /builtin/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://rmm.EXAMPLE.com";
        alias /srv/salt/scripts/;
    }

    location ~ ^/(natsapi) {
        allow 127.0.0.1;
        deny all;
        uwsgi_pass tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 9999s;
        uwsgi_ignore_client_abort on;
    }

    location / {
        uwsgi_pass  tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 9999s;
        uwsgi_ignore_client_abort on;
    }
}
```

3. Edit `/etc/nginx/sites-available/meshcentral.conf` and change to match the example below. Don't forget to replace `mesh.EXAMPLE.COM` with your mesh domain. This file needs to be opened with sudo
```bash
server {
  listen 80;
  server_name mesh.EXAMPLE.com;
  return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name mesh.example.com;
    ssl_certificate /etc/letsencrypt/live/EXAMPLE.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/EXAMPLE.com/privkey.pem;
    ssl_session_cache shared:WEBSSL:10m;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:4430/;
        proxy_http_version 1.1;

        proxy_set_header Host $host; ## this line is new
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Host $host:$server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. Edit `/meshcentral/meshcentral-data/config.json` and change to match the example below. Replace `mesh.example.com` with your mesh domain. After editing, use a json linter like `https://jsonlint.com/` to verify no syntax errors, otherwise meshcentral will fail to start.
```
{
  "settings": {
    "Cert": "mesh.example.com",
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
    "AgentPong": 200,
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
      "CertUrl": "https://mesh.example.com:443/",
      "GeoLocation": true,
      "CookieIpCheck": false,
      "mstsc": true
    }
  }
}
```

5. Replace `/rmm/api/tacticalrmm/app.ini` with the following:
```bash
[uwsgi]

chdir = /rmm/api/tacticalrmm
module = tacticalrmm.wsgi
home = /rmm/api/env
master = true
processes = 6
threads = 6
enable-threads = True
socket = /rmm/api/tacticalrmm/tacticalrmm.sock
harakiri = 300
chmod-socket = 666
# clear environment on exit
vacuum = true
die-on-term = true
max-requests = 500
max-requests-delta = 1000
```

6. Replace `/etc/salt/master.d/rmm-salt.conf` with the following. This file needs to be opened with sudo
```
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
```

7. Edit `/etc/conf.d/celery.conf` and `/etc/conf.d/celery-winupdate.conf` and change
```
CELERYD_LOG_LEVEL="INFO"
```
to
```
CELERYD_LOG_LEVEL="ERROR"
```

8. Clear log files
```bash
baselog="/rmm/api/tacticalrmm/tacticalrmm/private/log"
for i in ${baselog}/access.log ${baselog}/error.log ${baselog}/debug.log ${baselog}/uwsgi.log; do sudo rm -f $i; done
sudo rm -f /var/log/celery/*
```

9. Verify nginx syntax is correct. If any errors check steps above and fix nginx configs
```
sudo nginx -t
```

10. Edit `/etc/hosts` and make sure the line starting with 127.0.1.1 or 127.0.0.1 has your 3 subdomains in it like this:
```bash
127.0.0.1 localhost
127.0.1.1 yourservername api.example.com rmm.example.com mesh.example.com
```

11. Start services
```bash
for i in rmm celery celerybeat celery-winupdate salt-master salt-api nginx meshcentral; do sudo systemctl start $i; done
```

12. Delete whatever `update.sh` script you currently have and download the latest one and run it
```bash
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/update.sh
chmod +x update.sh
./update.sh
```



