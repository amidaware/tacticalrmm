#!/usr/bin/env bash
#
# https://www.freecodecamp.org/news/how-to-implement-runtime-environment-variables-with-create-react-app-docker-and-nginx-7f9d42a91d70/
#
set -e

function check_tactical_ready {
  sleep 15
  until [ -f "${TACTICAL_READY_FILE}" ]; do
    echo "waiting for init container to finish install or update..."
    sleep 10
  done
}

# Recreate js config file on start
rm -rf ${PUBLIC_DIR}/env-config.js
touch ${PUBLIC_DIR}/env-config.js

nginx_config="$(cat << EOF
server {
  listen 8080;
  charset utf-8;

  location / {
    root /usr/share/nginx/html;
    try_files \$uri \$uri/ /index.html;
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    add_header Pragma "no-cache";
  }
}
EOF
)"

echo "${nginx_config}" > /etc/nginx/conf.d/default.conf

check_tactical_ready

URL_PATH="${TACTICAL_DIR}/tmp/web_tar_url"
AGENT_BASE=$(grep -o 'AGENT_BASE_URL.*' /tmp/settings.py | cut -d'"' -f 2)
WEB_VERSION=$(grep -o 'WEB_VERSION.*' /tmp/settings.py | cut -d'"' -f 2)

# add dynamic web tar if configured
if [ -f "$URL_PATH" ]; then
  START_STRING=$(head -c ${#AGENT_BASE} "$URL_PATH")
  if [ "$START_STRING" == "${AGENT_BASE}" ]; then
    echo "Attempting to pull dynamic web tar from ${AGENT_BASE}"
    webtar="trmm-web-v${WEB_VERSION}.tar.gz"
    wget -q $(cat "${URL_PATH}") -O /tmp/${webtar}
    tar -xzf /tmp/${webtar} -C /tmp/
    rm -rf ${PUBLIC_DIR}/*
    mv /tmp/dist/* ${PUBLIC_DIR}

    rm -f /tmp/${webtar}
    rm -rf /tmp/dist
    echo "Success!"
  fi
fi  

# Add runtime base url assignment 
echo "window._env_ = {PROD_URL: \"https://${API_HOST}\"}" > ${PUBLIC_DIR}/env-config.js
chown -R nginx:nginx /etc/nginx && chown -R nginx:nginx ${PUBLIC_DIR}