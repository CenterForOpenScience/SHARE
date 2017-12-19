# SHARE v2

SHARE is creating a free, open dataset of research (meta)data.

[![Coverage Status](https://coveralls.io/repos/github/CenterForOpenScience/SHARE/badge.svg?branch=develop)](https://coveralls.io/github/CenterForOpenScience/SHARE?branch=develop)
[![Gitter](https://badges.gitter.im/CenterForOpenScience/SHARE.svg)](https://gitter.im/CenterForOpenScience/SHARE)

## Technical Documentation

http://share-research.readthedocs.io/en/latest/index.html


## On the OSF

https://osf.io/sdxvj/


## Get involved

We'll be expanding this section in the near future, but, beyond using our API for your own purposes, harvesters are a great way to get started. You can find a few that we have in our list [here](https://github.com/CenterForOpenScience/SHARE/issues/510).

## Setup for testing
It is useful to set up a [virtual environment](http://virtualenvwrapper.readthedocs.io/en/latest/install.html) to ensure [python3](https://www.python.org/downloads/) is your designated version of python and make the python requirements specific to this project.

    mkvirtualenv share -p `which python3.5`
    workon share

Once in the `share` virtual environment, install the necessary requirements, then setup SHARE.

    pip install -Ur requirements.txt
    python setup.py develop
    pyenv rehash  # Only necessary when using pyenv to manage virtual environments

`docker-compose` assumes [Docker](https://www.docker.com/) is installed and running. Running `./bootstrap.sh` will create and provision the database. If there are any SHARE containers running, make sure to stop them before bootstrapping using `docker-compose stop`.

    docker-compose build web
    docker-compose run --rm web ./bootstrap.sh

## Run
Run the API server

    # In docker
    docker-compose up -d web

    # Locally
    sharectl server

Setup Elasticsearch

    sharectl search setup

Run Celery

    # In docker
    docker-compose up -d worker

    # Locally
    sharectl worker -B

## Populate with data
This is particularly applicable to running [ember-share](https://github.com/CenterForOpenScience/ember-share), an interface for SHARE.

Harvest data from providers, for example

    sharectl harvest com.nature
    sharectl harvest com.peerj.preprints

    # Harvests may be scheduled to run asynchronously using the schedule command
    sharectl schedule org.biorxiv.html

    # Some sources provide thousands of records per day
    # --limit can be used to set a maximum number of records to gather
    sharectl harvest org.crossref --limit 250

If the Celery worker is running, new data will automatically be indexed every couple minutes.

Alternatively, data may be explicitly indexed using `sharectl`

    sharectl search
    # Forcefully re-index all data
    sharectl search --all

## Building docs

    cd docs/
    pip install -r requirements.txt
    make watch

## Running Tests

### Unit test suite

  py.test

### BDD Suite

  behave

