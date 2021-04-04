example of `/etc/nginx/sites-available/rmm.conf`

**DO NOT COPY PASTE INTO YOUR SERVER ONLY USE AS A REFERENCE**

```
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
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api.example.com;
    client_max_body_size 300M;
    access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log combined if=$ignore_ua;
    error_log /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';

    location /static/ {
        root /rmm/api/tacticalrmm;
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://rmm.example.com";
        alias /rmm/api/tacticalrmm/tacticalrmm/private/;
    }

    location ~ ^/(natsapi) {
        allow 127.0.0.1;
        deny all;
        uwsgi_pass tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 500s;
        uwsgi_ignore_client_abort on;
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

    location / {
        uwsgi_pass  tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 9999s;
        uwsgi_ignore_client_abort on;
    }
}
```