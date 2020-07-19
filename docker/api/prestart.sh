#! /usr/bin/env bash

sleep 10
python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py initial_db_setup
python manage.py initial_mesh_setup
python manage.py load_chocos
python manage.py fix_salt_key
