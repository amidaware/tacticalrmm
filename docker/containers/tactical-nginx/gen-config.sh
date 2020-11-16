#!/usr/bin/env bash

set -e

# check for certificates

# generate a self signed cert
sudo mkdir -p /certs/${rootdomain}
sudo openssl req -newkey rsa:4096 -x509 -sha256 -days 365 -nodes -out /certs/${rootdomain}/pubkey.pem -keyout /certs/${rootdomain}/privkey.pem -subj "/C=US/ST=Some-State/L=city/O=Internet Widgits Pty Ltd/CN=*.${rootdomain}"

CERT_PRIV_KEY=/certs/${rootdomain}/privkey.pem
CERT_PUB_KEY=/certs/${rootdomain}/pubkey.pem

# backend config
server  {
    resolver 127.0.0.11 valid=30s;

    server_name ${API_HOST};

    location / {
        #Using variable to disable start checks
        set $api http://tactical-backend;

        proxy_pass $api;
        proxy_http_version  1.1;
        proxy_cache_bypass  $http_upgrade;
        
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host  $host;
        proxy_set_header X-Forwarded-Port  $server_port;
    }

    location /static/ {
        root ${TACTICAL_DIR}/api;
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${APP_HOST}";
        alias ${TACTICAL_DIR}/api/tacticalrmm/private/;
    }

    location /saltscripts/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${APP_HOST}";
        alias ${TACTICAL_DIR}/scripts/userdefined/;
    }

    location /builtin/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${APP_HOST}";
        alias ${TACTICAL_DIR}/scripts/;
    }

    error_log  /var/log/nginx/api-error.log;
    access_log /var/log/nginx/api-access.log;

    client_max_body_size 300M;

    listen 443 ssl;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
    
}

server {
    listen 80;
    server_name ${API_HOST};
    return 301 https://$server_name$request_uri;
}


# frontend config
server  {
    resolver 127.0.0.11 valid=30s;
    
    server_name ${APP_HOST};

    location / {
        #Using variable to disable start checks
        set $app http://tactical-frontend;

        proxy_pass $app;
        proxy_http_version  1.1;
        proxy_cache_bypass  $http_upgrade;
        
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host  $host;
        proxy_set_header X-Forwarded-Port  $server_port;
    }

    error_log  /var/log/nginx/app-error.log;
    access_log /var/log/nginx/app-access.log;

    listen 443 ssl;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
    
}

server {

    listen 80;
    server_name ${APP_HOST};
    return 301 https://$server_name$request_uri;
}


# meshcentral config
server {
    resolver 127.0.0.11 valid=30s;

    listen 443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${MESH_HOST};
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    ssl_session_cache shared:WEBSSL:10m;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        #Using variable to disable start checks
        set $meshcentral http://tactical-meshcentral:443;

        proxy_pass $meshcentral;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Host $host:$server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    resolver 127.0.0.11 valid=30s;

    listen 80;
    server_name ${MESH_HOST};
    return 301 https://$server_name$request_uri;
}
