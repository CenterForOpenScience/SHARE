# SHAREv2

## On OSF

https://osf.io/sdxvj/

## Pipeline
    Harvester/Push/Curators -> Raw -> Normalization -> HoldingMaster -> Process -> Master (Versioned) -> Views (e.g., JamDB, ES, Neo4J)
                                                                                `-> Provenance
                              
## Setup for testing
    pip install -r requirements.txt
    pg
    createuser share
    psql
        CREATE DATABASE share;
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver