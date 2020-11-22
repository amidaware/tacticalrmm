#!/usr/bin/env bash
#
# build docker-compose images

set -o errexit
set -o pipefail

DOCKER_IMAGES="tactical tactical-frontend tactical-nginx tactical-meshcentral tactical-salt tactical-nats"

cd ..

for DOCKER_IMAGE in ${DOCKER_IMAGES}; do
  echo "Building Tactical Image: ${DOCKER_IMAGE}..."
  docker build --pull --no-cache --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" -t "${DOCKER_IMAGE}" -f "docker/containers/${DOCKER_IMAGE}/dockerfile" .
done