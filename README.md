# SHAREv2

## Technical Documentation

http://share-research.readthedocs.io/en/latest/index.html


## On the OSF

https://osf.io/sdxvj/

## Pipeline
    Harvester/Push/Curators -> Raw -> Normalization -> HoldingMaster -> Process -> Master (Versioned) -> Views (e.g., JamDB, ES, Neo4J)
                                                                                `-> Provenance
                              
## Setup for testing
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

## Run
    python manage.py runserver
    python manage.py monitor
    python manage.py celery worker -l DEBUG


## Build docs
     
    cd docs/
    pip install -r requirements.txt
    make watch
