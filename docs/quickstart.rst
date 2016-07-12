
Quickstart
----------

SHARE Pipeline
^^^^^^^^^^^^^^
THE SHARE Pipeline can be setup locally for testing and modifications.  Note: Kill any postgres process running before
starting.

If prompted, install docker from https://docs.docker.com/docker-for-mac/.

This requires Python 3.5; If necessary, follow the steps below:

From scratch::

    pip install virtualenv
    pip install virtualenvwrapper

Create virtualenv 'share'::

    mkvirtualenv share --python=python3.5

Switch into the share environment for the first time::

    workon share

Setup::

    git clone https://github.com/CenterForOpenScience/SHARE.git

    cd SHARE

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

sharepa
^^^^^^^
sharepa is the SHARE Parsing and Analysis Library. It is a python library that you can install to directly access SHARE's
elasticsearch API, and use to quickly generate summary statistics covering the metadata in SHARE.

You can find the `source code for sharepa on GitHub <https://github.com/CenterForOpenScience/sharepa>`_.

Install sharepa by running::

    pip install sharepa
