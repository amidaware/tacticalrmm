#!/usr/bin/env bash

set -e

: "${WORKER_CONNECTIONS:=2048}"
: "${APP_PORT:=80}"
: "${API_PORT:=80}"

CERT_PRIV_PATH=${TACTICAL_DIR}/certs/privkey.pem
CERT_PUB_PATH=${TACTICAL_DIR}/certs/fullchain.pem

mkdir -p "${TACTICAL_DIR}/certs"

# remove default config
rm -f /etc/nginx/conf.d/default.conf

# check for certificates in env variable
if [ ! -z "$CERT_PRIV_KEY" ] && [ ! -z "$CERT_PUB_KEY" ]; then
  echo "${CERT_PRIV_KEY}" | base64 -d > ${CERT_PRIV_PATH}
  echo "${CERT_PUB_KEY}" | base64 -d > ${CERT_PUB_PATH}
else
  # generate a self signed cert
  if [ ! -f "${CERT_PRIV_PATH}" ] || [ ! -f "${CERT_PUB_PATH}" ]; then
    rootdomain=$(echo ${API_HOST} | cut -d "." -f2- )
    openssl req -newkey rsa:4096 -x509 -sha256 -days 365 -nodes -out ${CERT_PUB_PATH} -keyout ${CERT_PRIV_PATH} -subj "/C=US/ST=Some-State/L=city/O=Internet Widgits Pty Ltd/CN=*.${rootdomain}"
  fi
fi

/bin/bash -c "sed -i 's/worker_connections.*/worker_connections ${WORKER_CONNECTIONS};/g' /etc/nginx/nginx.conf"

nginx_config="$(cat << EOF
# backend config
server  {
    resolver 127.0.0.11 valid=30s;

    server_name ${API_HOST};

    location / {
        #Using variable to disable start checks
        set \$api http://tactical-backend:${API_PORT};

        proxy_pass \$api;
        proxy_http_version  1.1;
        proxy_cache_bypass  \$http_upgrade;
        
        proxy_set_header Upgrade           \$http_upgrade;
        proxy_set_header Connection        "upgrade";
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host  \$host;
        proxy_set_header X-Forwarded-Port  \$server_port;
    }

    location /static/ {
        root ${TACTICAL_DIR}/api;
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${APP_HOST}";
        alias ${TACTICAL_DIR}/api/tacticalrmm/private/;
    }

    location ~ ^/ws/ {
        set \$api http://tactical-websockets:8383;
        proxy_pass \$api;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect     off;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host \$server_name;
    }

    error_log  /var/log/nginx/api-error.log;
    access_log /var/log/nginx/api-access.log;

    client_max_body_size 300M;

    listen 443 ssl;
    ssl_certificate ${CERT_PUB_PATH};
    ssl_certificate_key ${CERT_PRIV_PATH};
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
    
}

server {
    listen 80;
    server_name ${API_HOST};
    return 301 https://\$server_name\$request_uri;
}

# frontend config
server  {
    resolver 127.0.0.11 valid=30s;
    
    server_name ${APP_HOST};

    location / {
        #Using variable to disable start checks
        set \$app http://tactical-frontend:${APP_PORT};

        proxy_pass \$app;
        proxy_http_version  1.1;
        proxy_cache_bypass  \$http_upgrade;
        
        proxy_set_header Upgrade           \$http_upgrade;
        proxy_set_header Connection        "upgrade";
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host  \$host;
        proxy_set_header X-Forwarded-Port  \$server_port;
    }

    error_log  /var/log/nginx/app-error.log;
    access_log /var/log/nginx/app-access.log;

    listen 443 ssl;
    ssl_certificate ${CERT_PUB_PATH};
    ssl_certificate_key ${CERT_PRIV_PATH};
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
    
}

server {

    listen 80;
    server_name ${APP_HOST};
    return 301 https://\$server_name\$request_uri;
}

# meshcentral config
server {
    resolver 127.0.0.11 valid=30s;

    listen 443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${MESH_HOST};
    ssl_certificate ${CERT_PUB_PATH};
    ssl_certificate_key ${CERT_PRIV_PATH};
    ssl_session_cache shared:WEBSSL:10m;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        #Using variable to disable start checks
        set \$meshcentral http://tactical-meshcentral:443;

        proxy_pass \$meshcentral;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Host \$host:\$server_port;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    resolver 127.0.0.11 valid=30s;

    listen 80;
    server_name ${MESH_HOST};
    return 301 https://\$server_name\$request_uri;
}
EOF
)"

echo "${nginx_config}" > /etc/nginx/conf.d/default.conf
