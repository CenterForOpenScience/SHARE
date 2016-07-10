.. SHARE documentation master file, created by
   sphinx-quickstart on Sat Jul  9 14:45:04 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: ../project/static/img/share.png

.. toctree::
   :maxdepth: 2


SHARE is building a free, open, data set about research and scholarly activities across their life cycle.


SHARE is a higher education initiative whose mission is to maximize research impact by making research widely accessible,
discoverable, and reusable. To fulfill this mission SHARE is building a free, open, data set about research and scholarly
activities across their life cycle.

SHARE harvests metadata from 100+ separate repositories from around the web on a nightly basis, and then normalizes that
metadata into one format, and makes it accessable via a web API.

The technical side of SHARE has many pieces that you can interact with:

    - API Endpoints for accessing the raw and normalized metadata
    - A search endpoint powered by elasticsearch that indexes the normalized data, to allow for:
       - Thorough search
       - Data aggregations across fields
    - A python library called ``sharepa`` for SHARE Parsing and Analysis
    - An application built using Ember using the SHARE API for:
        - Discovering new Projects
        - Curation
        - Corrections and Updates


Features
--------

SHARE has a procesing pipeline that allows the data to be used in many formats::

    Harvester/Push/Curators -> Raw -> Normalization -> HoldingMaster ->
    Process -> Master (Versioned) -> Views (e.g., JamDB, ES, Neo4J)-> Provenance


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

Run a harvester:
    python manage.py harvest domain.providername --async

To see a list of all providers, as well as their names for harvesting, visit http://localhost:8000/api/providers/

For more information, see the section on Running and Creating Harvesters

sharepa
^^^^^^^
sharepa is the SHARE Parsing and Analysis Library. It is a python library that you can install to directly access SHARE's
elasticsearch API, and use to quickly generate summary statistics covering the metadata in SHARE.

You can find the `source code for sharepa on GitHub <https://github.com/CenterForOpenScience/sharepa>`_.

Install sharepa by running::

    pip install sharepa

Contribute
----------

- Issue Tracker: https://github.com/CenterForOpenScience/SHARE/issues
- Source Code: https://github.com/CenterForOpenScience/SHARE

Get In Touch
------------

Association of Research Libraries
21 Dupont Circle NW #800
Washington, DC 20036
202-296-2296
info@share-research.org


Creating a Harvester
--------------------

Start Up
^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To see a list of all providers, as well as their names for harvesting, visit http://localhost:8000/api/providers/

Gathering data involves a few steps:
    - **Harvest** data from the original source
    - **Normalize** data, or create a ``ChangeSet``` that will format the data to be saved into SHARE Models
    - **Accept** the ``ChangeSet``` objects, and save them as ``AbstractCreativeWork`` objects in the SHARE database


Printing to the Console
"""""""""""""""""""""""
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



Troubleshoting
""""""""""""""

If you're having trouble connecting to your Celery worker, or Postgres database, make sure both are running with::

    docker-compose up -d rabbitmq postgres


Elasticsearch
-------------
Coming Soon...


Ember Application
-----------------
Coming Soon...
