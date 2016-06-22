#!/bin/bash

# rm -f share/migrations/00*.py
# rm -f providers/*/*/migrations/0*.py
git clean -f

python manage.py reset_db --noinput

python manage.py makemigrations
python manage.py maketriggermigrations
python manage.py makeprovidermigrations

python manage.py migrate

python manage.py createsuperuser
