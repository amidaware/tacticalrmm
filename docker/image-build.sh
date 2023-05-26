#!/usr/bin/env bash

set -o errexit
set -o pipefail

# tactical tactical-frontend tactical-nats tactical-nginx tactical-meshcentral
DOCKER_IMAGES="tactical tactical-frontend tactical-nats tactical-nginx tactical-meshcentral"

cd ..

for DOCKER_IMAGE in ${DOCKER_IMAGES}; do
  echo "Building Tactical Image: ${DOCKER_IMAGE}..."
  docker build --pull --no-cache -t "${DOCKER_IMAGE}" -f "docker/containers/${DOCKER_IMAGE}/dockerfile" .
done