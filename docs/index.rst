*****
SHARE
*****

SHARE is building a free, open, dataset about research and scholarly activities across the lifecycle.

SHARE is a higher education initiative whose mission is to maximize research impact by making research widely accessible,
discoverable, and reusable. To fulfill this mission SHARE is building a free, open, data set about research and scholarly
activities across their life cycle.

SHARE harvests metadata nightly from 100+ repositories, normalizes that metadata into one format, and makes it accessable via a web API.

The technical side of SHARE has many pieces that you can interact with:

- API Endpoints for accessing the raw and normalized metadata
- A search endpoint powered by elasticsearch that indexes the normalized data allowing:
   - Thorough search
   - Data aggregations across fields
- A python library called ``sharepa`` for SHARE Parsing and Analysis
- An Ember application using the SHARE API for:
   - Discovering new Projects
   - Curation
   - Corrections and Updates


Features
========

SHARE has a processing pipeline that allows the data to be used in many formats::

    Harvester/Push/Curators -> Raw -> Normalization -> HoldingMaster ->
    Process -> Master (Versioned) ->
    Views (e.g., JamDB, ES, Neo4J) -> Provenance

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
