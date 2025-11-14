#!/usr/bin/env bash
pip install -r requirements.txt
npm install
npm run build:css
python manage.py collectstatic --noinput
