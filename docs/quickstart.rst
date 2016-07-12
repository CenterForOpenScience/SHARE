
Quickstart
----------

SHARE Pipeline
^^^^^^^^^^^^^^
THE SHARE Pipeline can be setup locally for testing and modifications.

Setup::

    pip install -r requirements.txt

    docker-compose up -d rabbitmq postgres
    ./up.sh

To run::

    python manage.py runserver
    python manage.py celery worker -l DEBUG

Run a harvester::

    python manage.py harvest domain.providername --async

To see a list of all providers, as well as their names for harvesting, visit https://staging-share.osf.io/api/providers/

For more information, see the section on Running and Creating Harvesters
