*****
SHARE
*****

SHARE is a higher education initiative whose mission is to maximize research impact by making research widely accessible,
discoverable, and reusable. To fulfill this mission SHARE is building a free, open, data set about research and scholarly
activities across their life cycle.

SHARE harvests metadata nightly from 100+ repositories, transforms that metadata into one format, and makes it accessable via a web API.

The technical side of SHARE has many pieces that you can interact with:

- A search endpoint powered by elasticsearch that indexes the transformed data allowing:
   - Thorough search of creative works:
        + Creative works: `</api/v2/search/creativeworks/_search_>`_
        + more info on the `elasticsearch docs`_ page
   - Data aggregations across fields
- An `Ember application`_ using the SHARE API for:
   - Searching the SHARE database
   - Discovering new Projects
   - Corrections and Updates
- API Endpoints for accessing transformed metadata
    + https://share.osf.io/api/v2

.. _`/api/v2/search/creativeworks/_search`: https://share.osf.io/api/v2/search/creativeworks/_search
.. _Ember application: /page/ember_app.html
.. _elasticsearch docs: /page/elasticsearch.html

Guide
=====

.. toctree::
    :maxdepth: 2

    quickstart
    harvesters_and_transformers
    share_models
    elasticsearch
    share_api
    ember_app

Contribute
==========

- Source Code: https://github.com/CenterForOpenScience/SHARE
- Issue Tracker: https://github.com/CenterForOpenScience/SHARE/issues

Get In Touch
============

For emails about technical support: share-support@osf.io

::

   Association of Research Libraries
   21 Dupont Circle NW #800
   Washington, DC 20036
   202-296-2296
   info@share-research.org
