#!/bin/bash

rm -fv ./{*/*/*/,*/*/,}*/migrations/00*.py
rm -fv ./bots/*/migrations/00*.py

python manage.py celery purge -f \
&& python manage.py reset_db --noinput \
&& python manage.py makemigrations \
&& git checkout api/migrations \
&& git checkout share/migrations \
&& git checkout osf_oauth2_adapter/migrations \
&& python manage.py maketriggermigrations \
&& python manage.py makeprovidermigrations \
&& python manage.py migrate \
&& python manage.py loaddata ./share/models/initial_data.yaml
