*****
SHARE
*****

SHARE is a higher education initiative whose mission is to maximize research impact by making research widely accessible,
discoverable, and reusable. To fulfill this mission SHARE is building a free, open, data set about research and scholarly
activities across their life cycle.

SHARE harvests metadata nightly from 100+ repositories, normalizes that metadata into one format, and makes it accessable via a web API.

The technical side of SHARE has many pieces that you can interact with:

- API Endpoints for accessing the raw and normalized metadata
    + https://staging-share.osf.io/api
- A search endpoint powered by elasticsearch that indexes the normalized data allowing:
   - Thorough search of creative works:
        + Creative works: https://staging-share.osf.io/api/search/abstractcreativework/_search
        + more info on the elasticsearch docs page: http://share-research.readthedocs.io/en/latest/elasticsearch.html
   - Data aggregations across fields
- A python library called ``sharepa`` for SHARE Parsing and Analysis
- An Ember application using the SHARE API for:
   - Discovering new Projects
   - Curation
   - Corrections and Updates
        + https://staging-share.osf.io/discover

Guide
=====

.. toctree::
    :maxdepth: 2

    quickstart
    harvesters_and_normalizers
    share_models
    elasticsearch
    ember_app
    troubleshooting

Contribute
==========

- Source Code: https://github.com/CenterForOpenScience/SHARE
- Issue Tracker: https://github.com/CenterForOpenScience/SHARE/issues

Get In Touch
============

::

   Association of Research Libraries
   21 Dupont Circle NW #800
   Washington, DC 20036
   202-296-2296
   info@share-research.org
