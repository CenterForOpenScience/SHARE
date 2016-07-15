
Quickstart
----------

Note - These instructions are for getting up and running with the simplest steps possible and is good as more of a refresher --
for more details, or getting started for the first time, please see the section on getting up and
running on the :ref:`Harvesters and Normalizers section <harvesters-and-normalizers>`.


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

For more information, see the section on :ref:`Harvesters and Normalizers <harvesters-and-normalizers>`.
