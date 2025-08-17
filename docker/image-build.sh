#!/usr/bin/env bash

set -o errexit
set -o pipefail

# scnplus scnplus-frontend scnplus-nats scnplus-nginx scnplus-meshcentral
DOCKER_IMAGES="scnplus scnplus-frontend scnplus-nats scnplus-nginx scnplus-meshcentral"

cd ..

for DOCKER_IMAGE in ${DOCKER_IMAGES}; do
  echo "Building SCNPLUS Image: ${DOCKER_IMAGE}..."
  docker build --pull --no-cache -t "${DOCKER_IMAGE}" -f "docker/containers/${DOCKER_IMAGE}/dockerfile" .
done