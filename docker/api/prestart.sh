#! /usr/bin/env bash

sleep 5
python manage.py migrate --no-input
python manage.py collectstatic --no-input
