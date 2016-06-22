#!/bin/bash

# rm -f share/migrations/00*.py
# rm -f providers/*/*/migrations/0*.py
# && touch */**/migrations/__init__.py \
# rm -f share/migrations/* \
# && touch share/migrations/__init__.py \
# && git clean -Xf providers/*/*/migrations/0*.py \
rm -fv ./{*/*/,}*/migrations/00*.py

python manage.py reset_db --noinput \
&& python manage.py makemigrations \
&& git checkout api/migrations \
&& git checkout share/migrations \
&& python manage.py maketriggermigrations \
&& python manage.py makeprovidermigrations \
&& python manage.py migrate \
&& python manage.py createsuperuser
