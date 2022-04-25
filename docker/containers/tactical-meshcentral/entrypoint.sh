#!/usr/bin/env bash

set -e

: "${MESH_USER:=meshcentral}"
: "${MESH_PASS:=meshcentralpass}"
: "${MONGODB_USER:=mongouser}"
: "${MONGODB_PASSWORD:=mongopass}"
: "${MONGODB_HOST:=tactical-mongodb}"
: "${MONGODB_PORT:=27017}"
: "${NGINX_HOST_IP:=172.20.0.20}"
: "${NGINX_HOST_PORT:=4443}"
: "${MESH_PERSISTENT_CONFIG:=0}"
: "${WS_MASK_OVERRIDE:=0}"
: "${SMTP_HOST:=smtp.example.com}"
: "${SMTP_PORT:=587}"
: "${SMTP_FROM:=mesh@example.com}"
: "${SMTP_USER:=mesh@example.com}"
: "${SMTP_PASS:=mesh-smtp-pass}"
: "${SMTP_TLS:=false}"

if [ ! -f "/home/node/app/meshcentral-data/config.json" ] || [[ "${MESH_PERSISTENT_CONFIG}" -eq 0 ]]; then

  encoded_uri=$(node -p "encodeURI('mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@${MONGODB_HOST}:${MONGODB_PORT}')")

  mesh_config="$(cat << EOF
{
  "settings": {
    "mongodb": "${encoded_uri}",
    "Cert": "${MESH_HOST}",
    "TLSOffload": "${NGINX_HOST_IP}",
    "RedirPort": 8080,
    "WANonly": true,
    "Minify": 1,
    "Port": 4443,
    "AgentAliasPort": 443,
    "aliasPort": 443,
    "AllowLoginToken": true,
    "AllowFraming": true,
    "_AgentPing": 60,
    "AgentPong": 300,
    "AllowHighQualityDesktop": true,
    "agentCoreDump": false,
    "Compression": true,
    "WsCompression": true,
    "AgentWsCompression": true,
    "MaxInvalidLogin": {
      "time": 5,
      "count": 5,
      "coolofftime": 30
    }
  },
  "domains": {
    "": {
      "Title": "Tactical RMM",
      "Title2": "TacticalRMM",
      "NewAccounts": false,
      "mstsc": true,
      "GeoLocation": true,
      "CertUrl": "https://${NGINX_HOST_IP}:${NGINX_HOST_PORT}",
      "agentConfig": [ "webSocketMaskOverride=${WS_MASK_OVERRIDE}" ]
    }
  },
  "smtp": {
    "host": "${SMTP_HOST}",
    "port": ${SMTP_PORT},
    "from": "${SMTP_FROM}",
    "user": "${SMTP_USER}",
    "pass": "${SMTP_PASS}",
    "tls": ${SMTP_TLS}
  }
}
EOF
)"

  echo "${mesh_config}" > /home/node/app/meshcentral-data/config.json
fi

node node_modules/meshcentral --createaccount ${MESH_USER} --pass ${MESH_PASS} --email example@example.com
node node_modules/meshcentral --adminaccount ${MESH_USER}

if [ ! -f "${TACTICAL_DIR}/tmp/mesh_token" ]; then
    mesh_token=$(node node_modules/meshcentral --logintokenkey)

    if [[ ${#mesh_token} -eq 160 ]]; then
      echo ${mesh_token} > /opt/tactical/tmp/mesh_token
    else
      echo "Failed to generate mesh token. Fix the error and restart the mesh container"
    fi
fi

# wait for nginx container
until (echo > /dev/tcp/"${NGINX_HOST_IP}"/${NGINX_HOST_PORT}) &> /dev/null; do
  echo "waiting for nginx to start..."
  sleep 5
done

# start mesh
node node_modules/meshcentral
