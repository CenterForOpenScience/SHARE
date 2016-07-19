.. _harvesters-and-normalizers:

Harvesters and Normalizers
==========================

A `harvester` gathers raw data from a provider using their API.

A `normalizer` takes the raw data gathered by a harvester and maps the fields to the defined :ref:`SHARE models <share-models>`.

Start Up
--------

    1. Install `Docker <https://docs.docker.com/engine/installation/>`_.
    2. Make sure you're using Python3 - install with `conda <http://conda.pydata.org/miniconda.html>`_ , or `homebrew <http://blog.manbolo.com/2013/02/04/how-to-install-python-3-and-pydev-on-osx#2>`_
    3. Install everything inside a Virtual Enviornment - created with `Conda <http://conda.pydata.org/docs/using/envs.html>`_ or `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ or your python enviornment of choice.

Installation (inside a virtual environment)::

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

.. _running-providers:

Running Existing Harvesters and Normalizers
-------------------------------------------

To see a list of all providers and their names for harvesting, visit https://staging-share.osf.io/api/providers/

Steps for gathering data:
    - **Harvest** data from the original source
    - **Normalize** data, or create a ``ChangeSet``` that will format the data to be saved into SHARE Models
    - **Accept** the ``ChangeSet``` objects, and save them as ``AbstractCreativeWork`` objects in the SHARE database


Printing to the Console
-----------------------

It is possible to run the harvesters and normalizers separately, and print the results out to the console
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
but you can also specify a folder when running the harvest command with the ``--out`` argument.

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

Note: celery must be running for ``--async`` tasks

Run a harvester and normalizer::

    python manage.py harvest domain.providername --async

To automatically accept all ``ChangeSet`` objects created::

    python manage.py runbot automerge --async

To automatically add all harvested and accepted documents to Elasticsearch::

    python manage.py runbot elasticsearch --async


Writing a Harvester and Normalizer
----------------------------------

See the normalizers and harvesters located in the ``providers/`` directory for examples of syntax and best practices.

Best practices for OAI providers
""""""""""""""""""""""""""""""""

If the provider follows OAI standards, then the provider's ``app.py`` should begin like this:

.. code-block:: python

    from share.provider import OAIProviderAppConfig


    class AppConfig(OAIProviderAppConfig):

Provider-specific normalizers and harvesters are unnecessary for OAI providers as they all use the base OAI harvester and normalizer.

Best practices for writing a non-OAI Harvester
""""""""""""""""""""""""""""""""""""""""""""""

- The harvester should be defined in ``<provider_dir>/harvester.py``.
- Add an example record to the provider's ``__init__.py``.
- Add the provider to the list of ``INSTALLED_APPS`` in ``project/settings.py``
- When writing the harvester:
    - Define a ``do_harvest(...)`` function (and possibly additional helper functions) to make requests to the provider and to yield the harvested records.
    - Check to see if the data returned by the provider is paginated.
        - There will often be a resumption token to get the next page of results.
    - Check to see if the provider's API accepts a date range
        - If the API does not then, if possible, check the date on each record returned and stop harvesting if the date on the record is older than the specified start date.
- Test by :ref:`running the harvester <running-providers>`


Best practices for writing a non-OAI Normalizer
"""""""""""""""""""""""""""""""""""""""""""""""

- The normalizer should be defined in ``<provider_dir>/normalizer.py``.
- When writing the normalizer:
    - Determine what information from the provider record should be stored as part of the ``CreativeWork`` :ref:`model <creative-work>` (i.e. if the record clearly defines a title, description, contributors, etc.).
    - Use the :ref:`normalizing tools <normalizing-tools>` as necessary to correctly parse the raw data.
    - Utilize the ``Extra`` class
        - Raw data that does not fit into a defined :ref:`share model <share-models>` should be stored here.
        - Raw data that is otherwise altered in the normalizer should also be stored here to ensure data integrity.
- Test by :ref:`running the normalizer <running-providers>` against raw data you have harvested.

.. _normalizing-tools:

SHARE Normalizing Tools
"""""""""""""""""""""""

If using normalizing tools, add ``from share.normalize import tools`` at the top of the file.
Tools are defined in ``SHARE/share/normalize/links.py`` but are imported as ``tools`` to avoid name conflicts with the models.

- Concat
    To combine list or singular elements into a flat list::

        tools.Concat(<string_or_list>, <string_or_list>)

.. _delegate-reference:

- Delegate
    To specify which class to use::

        tools.Delegate(<class_name>)

- Join
    To combine list elements into a single string::

        tools.Join(<list>, joiner=' ')

    Elements are separated with the ``joiner``.
    By default ``joiner`` is a newline.

- Map
    To designate the class used for each instance of a value found::

        tools.Map(tools.Delegate(<class_name>), <chain>)

    See the :ref:`share models <share-models>` for what uses a through table (anything that sets ``through=``).
    Uses the :ref:`Delegate <delegate-reference>` tool.

- Maybe
    To normalize data that is not consistently available::

        tools.Maybe(<path>, '<item_that_might_not_exist>')

    Indexing further if the path exists::

        tools.Maybe(<path>, '<item_that_might_not_exist>')['<item_that_will_exist_if_maybe_passes>']

    Nesting Maybe::

        tools.Maybe(tools.Maybe(<path>, '<item_that_might_not_exist>')['<item_that_will_exist_if_maybe_passes>'], '<item_that_might_not_exist>')

- ParseDate
    To determine a date from a string::

        tools.ParseDate(<date_string>)

- ParseLanguage
    To determine the ISO language code (i.e. 'ENG') from a string (i.e. 'English')::

        tools.ParseLanguage(<language_string>)

    Uses pycountry_ package.

    .. _pycountry: https://pypi.python.org/pypi/pycountry

- ParseName
    To determine the parts of a name (i.e. first name) out of a string::

        tools.ParseName(<name_string>).first

    options::

        first
        last
        middle
        suffix
        title
        nickname

    Uses nameparser_ package.

    .. _nameparser: https://pypi.python.org/pypi/nameparser

- RunPython
    To run a defined python function::

        tools.RunPython('<function_name>', <chain>, *args, **kwargs)

- Static
    To define a static field::

        tools.Static(<static_value>)

- XPath
    To access data using xpath::

        tools.XPath(<chain>, "<xpath_string>")
