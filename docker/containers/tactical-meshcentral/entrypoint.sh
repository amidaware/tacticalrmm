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
: "${MESH_COMPRESSION_ENABLED:=true}"
: "${MESH_PERSISTENT_CONFIG:=0}"
: "${MESH_WEBRTC_ENABLED:=false}"
: "${WS_MASK_OVERRIDE:=0}"
: "${SMTP_HOST:=smtp.example.com}"
: "${SMTP_PORT:=587}"
: "${SMTP_FROM:=mesh@example.com}"
: "${SMTP_USER:=mesh@example.com}"
: "${SMTP_PASS:=mesh-smtp-pass}"
: "${SMTP_TLS:=false}"

if [ ! -f "/home/node/app/meshcentral-data/config.json" ] || [[ "${MESH_PERSISTENT_CONFIG}" -eq 0 ]]; then

  encoded_uri=$(node -p "encodeURI('mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@${MONGODB_HOST}:${MONGODB_PORT}')")

  mesh_config="$(
    cat <<EOF
{
  "settings": {
    "mongodb": "${encoded_uri}",
    "cert": "${MESH_HOST}",
    "tlsOffload": "${NGINX_HOST_IP}",
    "redirPort": 8080,
    "WANonly": true,
    "minify": 1,
    "port": 4443,
    "agentAliasPort": 443,
    "aliasPort": 443,
    "allowLoginToken": true,
    "allowFraming": true,
    "agentPing": 35,
    "allowHighQualityDesktop": true,
    "agentCoreDump": false,
    "compression": ${MESH_COMPRESSION_ENABLED},
    "wsCompression": ${MESH_COMPRESSION_ENABLED},
    "agentWsCompression": ${MESH_COMPRESSION_ENABLED},
    "webRTC": ${MESH_WEBRTC_ENABLED},
    "maxInvalidLogin": {
      "time": 5,
      "count": 5,
      "coolofftime": 30
    }
  },
  "domains": {
    "": {
      "title": "Tactical RMM",
      "title2": "TacticalRMM",
      "newAccounts": false,
      "mstsc": true,
      "geoLocation": true,
      "certUrl": "https://${NGINX_HOST_IP}:${NGINX_HOST_PORT}",
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

  echo "${mesh_config}" >/home/node/app/meshcentral-data/config.json
fi

node node_modules/meshcentral --createaccount ${MESH_USER} --pass ${MESH_PASS} --email example@example.com
node node_modules/meshcentral --adminaccount ${MESH_USER}

if [ ! -f "${TACTICAL_DIR}/tmp/mesh_token" ]; then
  mesh_token=$(node node_modules/meshcentral --logintokenkey)

  if [[ ${#mesh_token} -eq 160 ]]; then
    echo ${mesh_token} >/opt/tactical/tmp/mesh_token
  else
    echo "Failed to generate mesh token. Fix the error and restart the mesh container"
  fi
fi

# wait for nginx container
until (echo >/dev/tcp/"${NGINX_HOST_IP}"/${NGINX_HOST_PORT}) &>/dev/null; do
  echo "waiting for nginx to start..."
  sleep 5
done

# start mesh
node node_modules/meshcentral
