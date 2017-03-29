.. _harvesters-and-transformers:

Harvesters and Transformers
===========================

A `harvester` gathers raw data from a source using their API.

A `transformer` takes the raw data gathered by a harvester and maps the fields to the defined :ref:`SHARE models <share-models>`.

Start Up
--------

    1. Install `Docker <https://docs.docker.com/engine/installation/>`_.
    2. Make sure you're using Python3 - install with `miniconda <http://conda.pydata.org/miniconda.html>`_ , or `homebrew <http://blog.manbolo.com/2013/02/04/how-to-install-python-3-and-pydev-on-osx#2>`_
    3. Install everything inside a Virtual Enviornment - created with `Conda <http://conda.pydata.org/docs/using/envs.html>`_ or `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ or your python enviornment of choice.

Installation (inside a virtual environment)::

    pip install -r requirements.txt

    // Creates, starts, and sets up containers for elasticsearch,
    // postgres, and the server
    docker-compose build web
    docker-compose run --rm web ./bootstrap.sh

To run the server in a virtual environment instead of Docker::

    docker-compose stop web
    python manage.py runserver

To run celery worker::

    python manage.py celery worker -l DEBUG

.. _running-sources:

Running Existing Harvesters and Transformers
--------------------------------------------

To see a list of all sources and their names for harvesting, visit https://share.osf.io/api/sources/

Steps for gathering data:
    - **Harvest** data from the original source
    - **Transform** data, or create a ``ChangeSet``` that will format the data to be saved into SHARE Models
    - **Accept** the ``ChangeSet``` objects, and save them as ``AbstractCreativeWork`` objects in the SHARE database


Printing to the Console
-----------------------

It is possible to run the harvesters and transformers separately, and print the results out to the console
for testing and debugging using ``./bin/share``

For general help documentation::

    ./bin/share --help

For harvest help::

    ./bin/share harvest --help

To harvest::

    ./bin/share harvest domain.source_name_here

If the harvester created a *lot* of files and you want to view a couple::

    find <source dir i.e. edu.icpsr/> -type f -name '*.json' | head -<number to list>

The harvest command will by default create a new folder at the top level with the same name as the source name,
but you can also specify a folder when running the harvest command with the ``--out`` argument.

To transform all harvested documents::

    ./bin/share transform domain.source_name_here dir_where_raw_docs_are/*

To transform just one document harvested::

    ./bin/share transform domain.source_name_here dir_where_raw_docs_are/filename.json

If the transformer returns an error while parsing a harvested document, it will automatically enter into a python debugger.

To instead enter into an enhanced python debugger with access to a few more variables like ``data``, run::

    ./bin/share debug domain.source_name_here dir_where_raw_docs_are/filename.json

To debug::

    e(data, ctx.<field>)


Running Though the Full Pipeline
""""""""""""""""""""""""""""""""

Note: celery must be running for ``--async`` tasks

Run a harvester and transformer::

    python manage.py harvest domain.sourcename --async

To automatically accept all ``ChangeSet`` objects created::

    python manage.py runbot automerge --async

To automatically add all harvested and accepted documents to Elasticsearch::

    python manage.py runbot elasticsearch --async


Writing a Harvester and Transformer
-----------------------------------

See the transformers and harvesters located in the ``share/transformers/`` and ``share/harvesters/`` directories for more examples of syntax and best practices.

Adding a new source
"""""""""""""""""""""

- Determine whether the source has an API to access their metadata
- Create a source folder at ``share/sources/{source name}``
    - Source names are typically the reversed domain name of the source, e.g. a source at ``http://example.com`` would have the name ``com.example``
    - If the source name starts with a new TLD (e.g. com, au, gov), please add ``/TLD.*/`` to `.gitignore`_ in the generated harvester data section
- Create a file named ``source.yaml`` in the source folder
    - See :ref:`Writing a source.yaml file <writing-yaml>`
- Determine whether the source makes their data available using the `OAI-PMH`_ protocol
    - If the source is OAI see :ref:`Best practices for OAI sources <oai-sources>`
- Writing the harvester
    - See :ref:`Best practices for writing a Harvester <writing-harvesters>`
- Writing the transformer
    - See :ref:`Best practices for writing a Transformer <writing-transformers>`
- Adding a sources's icon
    - visit ``www.domain.com/favicon.ico`` and download the ``favicon.ico`` file
    - place the favicon as ``icon.ico`` in the source folder
- Load the source
    - To make the source available in your local SHARE, run ``./manage.py loadsources`` in the terminal

.. _OAI-PMH: http://www.openarchives.org/OAI/openarchivesprotocol.html


.. _writing-yaml:

Writing a source.yaml file
""""""""""""""""""""""""""

The ``source.yaml`` file contains information about the source itself, and one or more configs that describe how to harvest and transform data from that source.

.. code-block:: yaml

    name: com.example
    long_title: Example SHARE Source for Examples
    home_page: http://example.com/
    user: sources.com.example
    configs:
    - label: com.example.oai
      base_url: http://example.com/oai/
      harvester: oai
      harvester_kwargs:
          metadata_prefix: oai_datacite
      rate_limit_allowance: 5
      rate_limit_period: 1
      transformer: org.datacite
      transformer_kwargs: {}

See the whitepaper_ for Source and SourceConfig tables for the available fields.

.. _whitepaper: https://github.com/CenterForOpenScience/SHARE/blob/develop/whitepapers/Tables.md

.. _oai-sources:

Best practices for OAI sources
""""""""""""""""""""""""""""""

Sources that use OAI-PMH_ make it easy to harvest their metadata.

- Set ``harvester: oai`` in the source config.
- Choose a metadata format to harvest.
    - Use the ``ListMetadataFormats`` OAI verb to see what formats the source supports.
    - Every OAI source supports ``oai_dc``, but they usually also support at least one other format that has richer, more structured data, like ``oai_datacite`` or ``mods``. 
    - Choose the format that seems to have the most useful data for SHARE, especially if a transformer for that format already exists.
    - Choose ``oai_dc`` only as a last resort.
- Add ``metadata_prefix: {prefix}`` to the ``harvester_kwargs`` in the source config.
- If necessary, write a transformer for the chosen format.
    - See :ref:`Best practices for writing a Transformer <writing-transformers>`


.. _.gitignore: https://github.com/CenterForOpenScience/SHARE/blob/develop/.gitignore


.. _writing-harvesters:

Best practices for writing a non-OAI Harvester
""""""""""""""""""""""""""""""""""""""""""""""

- The harvester should be defined in ``share/harvesters/{harvester name}.py``.
- When writing the harvester:
    - Inherit from ``share.harvest.BaseHarvester``
    - Add the version of the harvester ``VERSION = 1``
    - Implement ``do_harvest(...)`` (and possibly additional helper functions) to make requests to the source and to yield the harvested records.
    - Check to see if the data returned by the source is paginated.
        - There will often be a resumption token to get the next page of results.
    - Check to see if the source's API accepts a date range
        - If the API does not then, if possible, check the date on each record returned and stop harvesting if the date on the record is older than the specified start date.
- Add the harvester to ``entry_points`` in ``setup.py``
    - e.g. ``'com.example = share.harvesters.com_example:ExampleHarvester',``
    - run ``python setup.py develop`` to make the harvester available in your local SHARE
- Test by :ref:`running the harvester <running-sources>`

.. _writing-transformers:

Best practices for writing a non-OAI Transformer
""""""""""""""""""""""""""""""""""""""""""""""""

- The transformer should be defined in ``share/transformers/{transformer name}.py``.
- When writing the transformer:
    - Determine what information from the source record should be stored as part of the ``CreativeWork`` :ref:`model <share-models>` (i.e. if the record clearly defines a title, description, contributors, etc.).
    - Use the :ref:`chain transformer tools <chain-transformer>` as necessary to correctly parse the raw data.
        - Alternatively, implement ``share.transform.BaseTransformer`` to create a transformer from scratch.
    - Utilize the ``Extra`` class
        - Raw data that does not fit into a defined :ref:`share model <share-models>` should be stored here.
        - Raw data that is otherwise altered in the transformer should also be stored here to ensure data integrity.
- Add the transformer to ``entry_points`` in ``setup.py``
    - e.g. ``'com.example = share.transformer.com_example:ExampleTransformer',``
    - run ``python setup.py develop`` to make the transformer available in your local SHARE
- Test by :ref:`running the transformer <running-sources>` against raw data you have harvested.

.. _chain-transformer:

SHARE Chain Transformer
"""""""""""""""""""""""

SHARE provides a set of tools for writing transformers, based on the idea of constructing chains for each field that lead from the root of the raw document to the data for that field. To write a chain transformer, add ``from share.transform.chain import links`` at the top of the file and make the transformer inherit ``share.transform.chain.ChainTransformer``.


.. code-block:: python

    from share.transform.chain import ctx, links, ChainTransformer, Parser


    class CreativeWork(Parser):
        title = ctx.title


    class ExampleTransformer(ChainTransformer):
        VERSION = 1
        root_parser = CreativeWork


- Concat
    To combine list or singular elements into a flat list::

        links.Concat(<string_or_list>, <string_or_list>)

.. _delegate-reference:

- Delegate
    To specify which class to use::

        links.Delegate(<class_name>)

- Join
    To combine list elements into a single string::

        links.Join(<list>, joiner=' ')

    Elements are separated with the ``joiner``.
    By default ``joiner`` is a newline.

- Map
    To designate the class used for each instance of a value found::

        links.Map(links.Delegate(<class_name>), <chain>)

    See the :ref:`share models <share-models>` for what uses a through table (anything that sets ``through=``).
    Uses the :ref:`Delegate <delegate-reference>` tool.

- Maybe
    To transform data that is not consistently available::

        links.Maybe(<chain>, '<item_that_might_not_exist>')

    Indexing further if the path exists::

        links.Maybe(<chain>, '<item_that_might_not_exist>')['<item_that_will_exist_if_maybe_passes>']

    Nesting Maybe::

        links.Maybe(links.Maybe(<chain>, '<item_that_might_not_exist>')['<item_that_will_exist_if_maybe_passes>'], '<item_that_might_not_exist>')

    To avoid excessive nesting use the :ref:`Try link <try-reference>`

- OneOf
    To specify two possible paths for a single value::

        links.OneOf(<chain_option_1>, <chain_option_2>)

- ParseDate
    To determine a date from a string::

        links.ParseDate(<date_string>)

- ParseLanguage
    To determine the ISO language code (i.e. 'ENG') from a string (i.e. 'English')::

        links.ParseLanguage(<language_string>)

    Uses pycountry_ package.

    .. _pycountry: https://pypi.python.org/pypi/pycountry

- ParseName
    To determine the parts of a name (i.e. first name) out of a string::

        links.ParseName(<name_string>).first

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

        links.RunPython('<function_name>', <chain>, *args, **kwargs)

- Static
    To define a static field::

        links.Static(<static_value>)

- Subjects
    To map a subject to the PLOS taxonomy based on defined mappings::

        links.Subjects(<subject_string>)

.. _try-reference:

- Try
    To transform data that is not consistently available and may throw an exception::

        links.Try(<chain>)

- XPath
    To access data using xpath::

        links.XPath(<chain>, "<xpath_string>")
