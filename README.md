# SHARE v2

SHARE is creating a free, open dataset of research (meta)data.

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

    pip install -r requirements.txt
    python setup.py develop

`docker-compose` assumes [Docker](https://www.docker.com/) is installed and running. Running `./bootstrap.sh` will create and provision the database. If there are any SHARE containers running, make sure to stop them before bootstrapping using `docker-compose stop`.

    docker-compose build web
    docker-compose run --rm web ./bootstrap.sh

## Run
Run the API server

    docker-compose up -d web

Run Celery

    python manage.py celery worker -l DEBUG

## Populate with data
This is particularly applicable to running [ember-share](https://github.com/CenterForOpenScience/ember-share), an interface for SHARE. 

In a separate terminal, navigate to SHARE directory and activate the same virtual environment. 

Harvest data from providers, for example

    ./manage.py harvest com.nature --async
    ./manage.py harvest com.peerj.preprints --async
    
Insure all requirements.txt needed for this project are properly installed, this may take some time.

    pip install -r dev-requirements.txt 
    ./manage.py elasticsearch

## Building docs

    cd docs/
    pip install -r requirements.txt
    make watch

## Running Tests

### Unit test suite

  py.test

### BDD Suite

  behave
  
## Problems with Postgress

If you run into problems with Postgress, restart Docker. If that doesn't work proceed to reset Docker by going to Docker -> preferences -> reset (bomb icon)
