#!/bin/bash

rm -fv ./{*/*/*/,*/*/,}*/migrations/00*.py

python manage.py reset_db --noinput \
&& python manage.py makemigrations \
&& git checkout api/migrations \
&& git checkout share/migrations \
&& python manage.py maketriggermigrations \
&& python manage.py makeprovidermigrations \
&& python manage.py migrate \
&& python manage.py loaddata ./share/models/initial_data.json \
&& python manage.py loaddata ./share/models/initial_groups.json
