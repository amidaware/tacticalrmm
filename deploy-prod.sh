#!/bin/bash
# DLTS - TacticalRMM Production deployment

set -e

cd "$(dirname "$0")/docker"

# משתמשים בקובץ ההגדרות של PROD
cp .env.prod .env

docker compose pull
docker compose up -d
