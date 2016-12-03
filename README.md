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

Once in the `share` virtual environment, install the necessary requirements.

    pip install -r requirements.txt

`docker-compose` assumes [Docker](https://www.docker.com/) is installed and running. `docker-compose up -d web` creates and starts containers for elasticsearch, rabbitmq, and postgres. Finally, `./up.sh` ensures everything has been installed properly.

    docker-compose up -d web
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

## Run
Run the API server

    python manage.py runserver

Run Celery

    python manage.py celery worker -l DEBUG

## Populate with data
This is particularly applicable to running [ember-share](https://github.com/CenterForOpenScience/ember-share), an interface for SHARE.

Harvest data from providers, for example

    ./manage.py harvest com.nature --async
    ./manage.py harvest io.osf --async

Pass data to elasticsearch with `runbot`. Rerunning this command will get the most recently harvested data. This can take a minute or two to finish.

    ./manage.py runbot elasticsearch

## Build docs

    cd docs/
    pip install -r requirements.txt
    make watch
