
#!/usr/bin/env bash

set -e

: "${APP_HOST:=scnplus.example.com}"
: "${API_HOST:=api.scnplus.example.com}"
: "${MESH_HOST:=mesh.scnplus.example.com}"
: "${CERT_PUB_KEY:=/opt/scnplus/certs/fullchain.pem}"
: "${CERT_PRIV_KEY:=/opt/scnplus/certs/privkey.pem}"
: "${NGINX_RESOLVER:=127.0.0.11}"

# Set paths for the certificates
CERT_PUB_PATH=${CERT_PUB_KEY}
CERT_PRIV_PATH=${CERT_PRIV_KEY}

# Check if custom cert path
if [[ "${CERT_PUB_KEY}" == "/certs/"* ]]; then
    CERT_PUB_PATH=${CERT_PUB_KEY}
    CERT_PRIV_PATH=${CERT_PRIV_KEY}
else
    CERT_PUB_PATH=/opt/scnplus/certs/fullchain.pem
    CERT_PRIV_PATH=/opt/scnplus/certs/privkey.pem
fi

# Default backend service names
FRONTEND_SERVICE="scnplus-frontend"
BACKEND_SERVICE="scnplus-backend"
WEBSOCKETS_SERVICE="scnplus-websockets"
NATS_SERVICE="scnplus-nats"
MESH_SERVICE="scnplus-meshcentral"

nginx_config="$(cat << 'EOF'
# SCNPLUS frontend config
server {
    resolver ${NGINX_RESOLVER} valid=30s;

    listen 4443 ssl;
    server_name ${APP_HOST};
    ssl_certificate ${CERT_PUB_PATH};
    ssl_certificate_key ${CERT_PRIV_PATH};
    
    ssl_session_cache shared:WEBSSL:10m;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;

    location / {
        #Using variable to disable start checks
        set \$frontend http://${FRONTEND_SERVICE}:8080;

        proxy_pass \$frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# SCNPLUS api config
server {
    resolver ${NGINX_RESOLVER} valid=30s;

    listen 4443 ssl;
    server_name ${API_HOST};
    ssl_certificate ${CERT_PUB_PATH};
    ssl_certificate_key ${CERT_PRIV_PATH};
    
    ssl_session_cache shared:WEBSSL:10m;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;

    location / {
        #Using variable to disable start checks
        set \$backend http://${BACKEND_SERVICE}:8080;

        proxy_pass \$backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws/ {
        #Using variable to disable start checks
        set \$websockets http://${WEBSOCKETS_SERVICE}:8080;

        proxy_pass \$websockets;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location ~ ^/natsws {
        #Using variable to disable start checks
        set \$nats http://${NATS_SERVICE}:9235;

        proxy_pass \$nats;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    listen 8080;
    server_name ${APP_HOST};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 8080;
    server_name ${API_HOST};
    return 301 https://\$server_name\$request_uri;
}

# meshcentral config
server {
    resolver ${NGINX_RESOLVER} valid=30s;

    listen 4443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${MESH_HOST};
    ssl_certificate ${CERT_PUB_PATH};
    ssl_certificate_key ${CERT_PRIV_PATH};
    
    ssl_session_cache shared:WEBSSL:10m;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header X-Content-Type-Options nosniff;

    location / {
        #Using variable to disable start checks
        set \$meshcentral http://${MESH_SERVICE}:4443;

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
    listen 8080;
    server_name ${MESH_HOST};
    return 301 https://\$server_name\$request_uri;
}
EOF
)"

echo "${nginx_config}" >/etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"
