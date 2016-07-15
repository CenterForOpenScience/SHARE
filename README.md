# SHAREv2

[![Gitter](https://badges.gitter.im/CenterForOpenScience/SHARE.svg)](https://gitter.im/CenterForOpenScience/SHARE?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

## Technical Documentation

http://share-research.readthedocs.io/en/latest/index.html


## On the OSF

https://osf.io/sdxvj/

                              
## Setup for testing
It is useful to set up a [virtual environment](http://virtualenvwrapper.readthedocs.io/en/latest/install.html) to ensure [python3](https://www.python.org/downloads/) is your designated version of python and make the python requirements specific to this project.

    mkvirtualenv share -p `which python3.5`
    workon share

Once in the `share` virtual environment, install the necessary requirements.

    pip install -r requirements.txt

`docker-compose` assumes [Docker](https://www.docker.com/) is installed and running. Finally, `./up.sh` ensures everything has been installed properly.

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
