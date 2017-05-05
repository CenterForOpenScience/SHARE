#!/bin/bash
set -e

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -b|--backup)
    BACKUP="sup"
    ;;
    -f|--force)
    FORCE="yup"
    ;;
    *)
    # unknown option
    ;;
esac
shift # past argument or value
done

if [ -n "$BACKUP" ]; then
    python manage.py dumpdata share.RawDatum --natural-foreign --natural-primary --format json | gzip > share_rawdata.json.gz
fi

if [ -n "$FORCE" ]; then
  echo "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'share' AND pid <> pg_backend_pid();" | python manage.py dbshell
fi

celery -A project purge -f 2>/dev/null || true;
python manage.py reset_db --noinput
python manage.py migrate
python manage.py addsubjects ./share/models/subjects.json

if [ -n "$BACKUP" ]; then
    python manage.py loaddata share_rawdata.json.gz
fi
