
Quickstart
----------

SHARE Pipeline
^^^^^^^^^^^^^^
THE SHARE Pipeline can be setup locally for testing and modifications.  Note: Kill any postgres process running before
starting.

If prompted, install docker from https://docs.docker.com/docker-for-mac/.

This requires Python 3.6; If necessary, follow the steps below:

From scratch::

    pip install virtualenv
    pip install virtualenvwrapper

Create virtualenv 'share'::

    mkvirtualenv share --python=python3.6

Switch into the share environment for the first time::

    workon share
Note - These instructions are for getting up and running with the simplest steps possible and is good as more of a refresher --
for more details, or getting started for the first time, please see the section on getting up and
running on the :ref:`Harvesters and Transformers section <harvesters-and-transformers>`.


THE SHARE Pipeline can be setup locally for testing and modifications.

Setup::

    git clone https://github.com/CenterForOpenScience/SHARE.git

    cd SHARE

    pip install -r requirements.txt

    // Creates and starts containers for elasticsearch, rabbitmq, and postgres
    docker-compose up -d web

    ./up.sh

To run::

    python manage.py runserver
    python manage.py celery worker -l DEBUG

Run a harvester::

    python manage.py harvest domain.providername --async

To see a list of all providers, as well as their names for harvesting, visit https://share.osf.io/api/v2/sources

For more information, see the section on :ref:`Harvesters and Transformers <harvesters-and-transformers>`.
