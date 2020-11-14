#!/usr/bin/env bash
set -e

# install tactical
groupadd -g 1000 "${TACTICAL_USER}"
useradd -M -d "${TACTICAL_DIR}" -s /bin/bash -u 1000 -g 1000 "${TACTICAL_USER}"

if [ "$1" = 'install' ]; then
  apt-get update
  apt-get upgrade -y
  apt-get install -y --no-install-recommends wget ca-certificates gcc libc6-dev
  rm -rf /var/lib/apt/lists/*
  pip install --upgrade pip 
  pip install --no-cache-dir virtualenv && python -m virtualenv ${TACTICAL_TMP_DIR}/env
  ${TACTICAL_TMP_DIR}/env/bin/pip install --no-cache-dir setuptools wheel gunicorn
  ${TACTICAL_TMP_DIR}/env/bin/pip install --no-cache-dir -r ${TACTICAL_TMP_DIR}/requirements.txt
  wget https://golang.org/dl/go1.15.linux-amd64.tar.gz -P /tmp
  tar -xzf /tmp/go1.15.linux-amd64.tar.gz -C /tmp
fi

if [ "$1" = 'run' ]; then
  mkdir /usr/local/rmmgo

fi
