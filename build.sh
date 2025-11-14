#!/usr/bin/env bash
set -o errexit  # exit if any command fails

# Install dependencies
pip install -r requirements.txt

# Run Django migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput
