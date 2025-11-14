#!/bin/bash
# DLTS - TacticalRMM Dev deployment (Raspberry Pi)

set -e

cd "$(dirname "$0")/docker"

# משתמשים בקובץ ההגדרות של DEV
cp .env.dev .env

# משיכת האימג'ים האחרונים והקמה
docker compose pull
docker compose up -d
