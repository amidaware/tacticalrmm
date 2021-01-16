#!/usr/bin/env bash

set -o errexit
set -o pipefail

DOCKER_IMAGES="tactical-nginx"

cd ..

for DOCKER_IMAGE in ${DOCKER_IMAGES}; do
  echo "Building Tactical Image: ${DOCKER_IMAGE}..."
  docker build --pull --no-cache -t "${DOCKER_IMAGE}" -f "docker/containers/${DOCKER_IMAGE}/dockerfile" .
done