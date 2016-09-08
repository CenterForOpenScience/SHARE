#!/bin/bash
set -e

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -b|--backup)
    BACKUP="sup"
    ;;
    *)
    # unknown option
    ;;
esac
shift # past argument or value
done

#rm -fv ./{*/*/*/,*/*/,}*/migrations/00*.py
#rm -fv ./bots/*/migrations/00*.py

if [ -n "$BACKUP" ]; then
    python manage.py dumpdata share.RawData --natural-foreign --natural-primary --format json | gzip > share_rawdata.json.gz
fi

python manage.py celery purge -f
python manage.py reset_db --noinput
python manage.py makemigrations
#git checkout api/migrations
#git checkout share/migrations
#git checkout osf_oauth2_adapter/migrations
#python manage.py maketriggermigrations
#python manage.py makeprovidermigrations
python manage.py migrate
python manage.py loaddata ./share/models/initial_data.yaml
python manage.py addsubjects ./share/fixtures/subjects.json

if [ -n "$BACKUP" ]; then
    python manage.py loaddata share_rawdata.json.gz
fi
