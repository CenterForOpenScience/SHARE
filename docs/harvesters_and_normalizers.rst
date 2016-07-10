Harvesters and Normalizers
==========================

Start Up
--------

Installation (inside a virtual environment))::

    pip install -r requirements.txt

    docker-compose up -d rabbitmq postgres
    ./up.sh
    ---------------- or ----------------
    pg
    createuser share
    psql
        CREATE DATABASE share;
    python manage.py makemigrations
    python manage.py maketriggermigrations
    python manage.py makeprovidermigrations
    python manage.py migrate
    python manage.py createsuperuser


To run::

    python manage.py runserver
    python manage.py celery worker -l DEBUG

To monitor your celery tasks::

    python manage.py celery flower

Visit http://localhost:5555/dashboard to keep an eye on your harvesting and normalizing tasks


Running Existing Harvesters and Normalizers
-------------------------------------------

To see a list of all providers, as well as their names for harvesting, visit http://localhost:8000/api/providers/

Gathering data involves a few steps:
    - **Harvest** data from the original source
    - **Normalize** data, or create a ``ChangeSet``` that will format the data to be saved into SHARE Models
    - **Accept** the ``ChangeSet``` objects, and save them as ``AbstractCreativeWork`` objects in the SHARE database


Printing to the Console
-----------------------

It's possible to run the harvesters and normalizers separately, and print the results out to the console
for testing and debugging using ``./bin/share``

For general help documentation::

    ./bin/share --help

For harvest help::

    ./bin/share harvest --help

To harvest::

    ./bin/share harvest domain.provider_name_here

If the harvester created a *lot* of files and you want to view a couple::

    find <provider dir i.e. edu.icpsr/> -type f -name '*.json' | head -<number to list>

The harvest command will by default create a new folder at the top level with the same name as the provider name,
but you can also specify a specific folder when running the harvest command with the ``--out`` argument.

To normalize all harvested documents::

    ./bin/share normalize domain.provider_name_here dir_where_raw_docs_are/*

To normalize just one document harvested::

    ./bin/share normalize domain.provider_name_here dir_where_raw_docs_are/filename.json

If the normalizer returns an error while parsing a harvested document, it will automatically enter into a python debugger.

To instead enter into an enhanced python debugger with access to a few more variables like ``data``, run::

    ./bin/share debug domain.provider_name_here dir_where_raw_docs_are/filename.json

To debug::

    e(data, ctx.<field>)


Running Though the Full Pipeline
""""""""""""""""""""""""""""""""

Run a harvester and normalizer::

    python manage.py harvest domain.providername --async

To automatically accept all ``ChangeSet`` objects created::

    python manage.py runbot automerge --async

To automatically add all harvested and accepted documents to Elasticsearch::

    python manage.py runbot elasticsearch --async


Writing a Harvester and Normalizer
""""""""""""""""""""""""""""""""""

See the normalizers and harvesters located in the ``providers/`` directory examples of syntax and best practices.


SHARE Normalizing Tools
"""""""""""""""""""""""

    ParseDate


    ParseName


    ParseLanguage


    Trim


    Concat


    XPath


    Join


    Maybe


    Map


    Delegate


    RunPython


    Static


