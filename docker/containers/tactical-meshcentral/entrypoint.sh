#!/usr/bin/env bash

set -e

: "${MESH_USER:=meshcentral}"
: "${MESH_PASS:=meshcentralpass}"
: "${MONGODB_USER:=mongouser}"
: "${MONGODB_PASSWORD:=mongopass}"
: "${MONGODB_HOST:=tactical-mongodb}"
: "${MONGODB_PORT:=27017}"
: "${NGINX_HOST_IP:=172.20.0.20}"

mkdir -p /home/node/app/meshcentral-data
mkdir -p ${TACTICAL_DIR}/tmp

mesh_config="$(cat << EOF
{
  "settings": {
    "mongodb": "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@${MONGODB_HOST}:${MONGODB_PORT}",
    "Cert": "${MESH_HOST}",
    "TLSOffload": "${NGINX_HOST_IP}",
    "RedirPort": 80,
    "WANonly": true,
    "Minify": 1,
    "Port": 443,
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
      "CertUrl": "https://${NGINX_HOST_IP}:443"
    }
  }
}
EOF
)"

echo "${mesh_config}" > /home/node/app/meshcentral-data/config.json

node node_modules/meshcentral --createaccount ${MESH_USER} --pass ${MESH_PASS} --email example@example.com
node node_modules/meshcentral --adminaccount ${MESH_USER}

if [ ! -f "${TACTICAL_DIR}/tmp/mesh_token" ]; then
    node node_modules/meshcentral --logintokenkey > ${TACTICAL_DIR}/tmp/mesh_token
fi

# wait for nginx container
until (echo > /dev/tcp/"${NGINX_HOST_IP}"/443) &> /dev/null; do
  echo "waiting for nginx to start..."
  sleep 5
done

# start mesh
node node_modules/meshcentral
