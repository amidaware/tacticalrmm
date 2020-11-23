#!/usr/bin/env bash
#
# build docker-compose images

set -o errexit
set -o pipefail

# tactical tactical-frontend tactical-nginx tactical-meshcentral tactical-salt tactical-nats
DOCKER_IMAGES="tactical-nats tactical-nginx"

cd ..

for DOCKER_IMAGE in ${DOCKER_IMAGES}; do
  echo "Building Tactical Image: ${DOCKER_IMAGE}..."
  docker build --pull --no-cache -t "${DOCKER_IMAGE}" -f "docker/containers/${DOCKER_IMAGE}/dockerfile" .
done